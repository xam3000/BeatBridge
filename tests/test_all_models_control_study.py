import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from src.evaluation.all_models_control_study import (
    _empty_ratings,
    build_listening_page,
    discover_representative_runs,
)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_player_contains_every_pair_and_has_no_answer_mapping():
    manifest = {
        "dataset_id": "dataset-1",
        "created_at_utc": "2026-09-04T00:00:00+00:00",
        "criteria": ["cleanliness"],
        "pairs": [
            {
                "index": 1,
                "directory": "01__a__to__b",
                "source_track": "musik/a.flac",
                "target_track": "musik/b.flac",
                "transition_length_bars": 4,
                "tempo_adjustment_fraction": 0.001,
                "labels": ["A", "B", "C"],
            }
        ],
    }
    page = build_listening_page(manifest)
    assert "01__a__to__b" in page
    assert "label+'.wav'" in page
    assert "Bewertungen herunterladen" in page
    assert "baseline_equal_power" not in page
    ratings = _empty_ratings(manifest)
    assert ratings["ratings"][0]["scores"]["C"]["artifact_freedom"] is None


def test_discovery_keeps_best_compatible_run_per_family(tmp_path):
    dataset = tmp_path / "dataset"
    dataset_manifest = {"dataset_id": "shared"}
    _write_json(dataset / "manifest.json", dataset_manifest)
    import hashlib

    dataset_sha = hashlib.sha256((dataset / "manifest.json").read_bytes()).hexdigest()
    runs = tmp_path / "runs"

    def add(name, family, loss, *, dataset_id="shared", renderer=None):
        run = runs / name
        checkpoint = run / "checkpoints" / "best.pt"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_bytes(b"checkpoint")
        _write_json(
            run / "manifest.json",
            {
                "status": "completed",
                "best_validation_loss": loss,
                "contract": {
                    "model": {"name": family},
                    "dataset": {
                        "dataset_id": dataset_id,
                        "manifest_sha256": dataset_sha,
                    },
                    "renderer": {"name": renderer},
                },
                "files": {"best_checkpoint": {"path": "checkpoints/best.pt"}},
            },
        )

    add("mlp_worse", "time_shared_mlp_v1", 0.4)
    add("mlp_best", "time_shared_mlp_v1", 0.3)
    add("vocal", "vocal_time_shared_mlp_v2", 0.5)
    add(
        "tcn_wrong_renderer",
        "tcn_bilstm_transition_control_v1",
        0.1,
        renderer="other",
    )
    add(
        "tcn",
        "tcn_bilstm_transition_control_v1",
        0.6,
        renderer="differentiable_full_band_transition_v1",
    )
    add("foreign", "time_shared_mlp_v1", 0.01, dataset_id="foreign")

    selected = {path.name for path in discover_representative_runs(runs, dataset)}
    assert selected == {"mlp_best", "vocal", "tcn"}


@pytest.mark.parametrize("label_count", [3, 5])
def test_candidate_places_preserve_ties_notes_and_legacy_ratings(label_count):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to execute the local player's JavaScript")
    labels = list("ABCDE"[:label_count])
    manifest = {
        "dataset_id": "synthetic",
        "created_at_utc": "synthetic",
        "pairs": [{
            "index": 1, "directory": "synthetic", "source_track": "a.wav",
            "target_track": "b.wav", "labels": labels,
            "transition_length_bars": 4, "tempo_adjustment_fraction": 0,
        }],
    }
    page = build_listening_page(manifest)
    script = re.search(r"</script><script>(.*?)</script>", page, re.S).group(1)
    # Execute the generated script with a small DOM adapter; no browser/focus needed.
    harness = r"""
const vm=require('node:vm'), assert=require('node:assert/strict');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const labels=input.manifest.pairs[0].labels;
const key='beatbridge:synthetic:synthetic';
const storage=new Map([[key,JSON.stringify({1:{ranking:[...labels].reverse(),notes:'alt',scores:{kept:true}}})]]);
function open(){
 const elements={manifest:{textContent:JSON.stringify(input.manifest)},
  pairs:{children:[],appendChild(child){this.children.push(child);}}, save:{},clear:{},state:{}};
 let download;
 const context=vm.createContext({
  document:{getElementById:id=>elements[id],createElement(tag){
   if(tag==='a')return {click(){}};
   return {className:'',set innerHTML(value){
    this.html=value;
    this.selects=[...value.matchAll(/data-label="([^"]+)"/g)].map(m=>({
     dataset:{label:m[1]},addEventListener(_,fn){this.change=fn;}}));
    this.notes={addEventListener(_,fn){this.input=fn;}};
   },querySelectorAll(){return this.selects;},querySelector(){return this.notes;}};
  }},
  localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
  URL:{createObjectURL(blob){download=blob.parts.join('');return 'blob:test';},revokeObjectURL(){}},
  Blob:class{constructor(parts){this.parts=parts;}},
 });
 vm.runInContext(input.script,context);
 const section=elements.pairs.children[0];
 return {section,change(label,value){
  const select=section.selects.find(s=>s.dataset.label===label);
  select.change({target:{dataset:select.dataset,value}});
 },save(){elements.save.onclick();return JSON.parse(download);}};
}
let ui=open();
assert.equal(ui.section.selects.length,labels.length);
let out=ui.save().ratings[0];
assert.deepEqual(out.ranking,[...labels].reverse());
assert.equal(out.ranks.A,labels.length);
assert.equal(out.notes,'alt');
ui.section.notes.input({target:{value:'neue Notiz'}});
ui.change('A','1');ui.change('B','1');
out=ui.save().ratings[0];
assert.equal(out.ranks.A,1);assert.equal(out.ranks.B,1);
assert.deepEqual(out.ranking,[]);assert.equal(out.notes,'neue Notiz');
assert.deepEqual(out.scores,{kept:true});
ui=open();out=ui.save().ratings[0];
assert.equal(out.ranks.A,1);assert.equal(out.ranks.B,1);
assert.equal(out.notes,'neue Notiz');
ui.change('A','');out=ui.save().ratings[0];
assert.equal(out.ranks.A,null);assert.equal(out.ranks.B,1);
assert.deepEqual(out.ranking,[]);
storage.clear();ui=open();out=ui.save().ratings[0];
assert.deepEqual(out.ranks,Object.fromEntries(labels.map(l=>[l,null])));
for(const label of labels)ui.change(label,'1');
out=ui.save().ratings[0];assert.ok(Object.values(out.ranks).every(r=>r===1));
assert.deepEqual(out.ranking,[]);
console.log('candidate places: migration, ties, persistence, clearing and download passed');
"""
    result = subprocess.run(
        [node, "-e", harness],
        input=json.dumps({"manifest": manifest, "script": script}),
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
