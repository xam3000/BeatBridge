import json
from pathlib import Path

from src import artifact_paths


def test_copied_windows_run_keeps_checksum_bound_paths_on_resume(tmp_path, monkeypatch):
    project = tmp_path / "renamed checkout"
    run = project / "output" / "runs" / "model"
    data = project / "output" / "datasets" / "d1"
    cache = project / "output" / "cache" / "manifest.json"
    for path in (run, data, cache.parent):
        path.mkdir(parents=True)
    monkeypatch.setattr(artifact_paths, "PROJECT", project)
    historical = r"Z:\former-machine\BeatBridge\output"
    def identity(dataset, waveforms):
        return {"path": str(dataset), "vocal_waveform_cache_manifests": {
            "train": [{"example_id": "example", "path": str(waveforms), "sha256": "kept"}]}}

    previous = identity(historical + r"\datasets\d1", historical + r"\cache\manifest.json")
    (run / "manifest.json").write_text(json.dumps({"contract": {"dataset": previous}}))
    for resume in (False, True):
        result = artifact_paths.portable_dataset_identity(identity(data, cache), run, resume)
        record = result["vocal_waveform_cache_manifests"]["train"][0]
        assert artifact_paths.artifact_path(record["path"]) == cache
        assert artifact_paths.artifact_path(result["path"]) == data
        if resume:
            assert result == previous
        else:
            assert result == identity("output/datasets/d1", "output/cache/manifest.json")
    assert artifact_paths.artifact_path(r"checkpoints\best.pt", run) == run / "checkpoints" / "best.pt"
