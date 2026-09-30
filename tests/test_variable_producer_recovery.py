import hashlib
import json
from pathlib import Path

from src.features.variable_split import authority_from_mapping, write_variable_split_authority
from src.features.variable_dataset_export import _discover_pair_manifests
from src.variable_producer_recovery import recover_variable_producer_root


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_recovery_aggregates_verified_pair_manifests_without_mutating_partial_root(tmp_path):
    songs = []
    for name in ("a.wav", "b.wav", "c.wav"):
        path = tmp_path / name
        path.write_bytes(name.encode("ascii"))
        songs.append(path)
    hashes = {path: _sha(path) for path in songs}
    assignments = {hashes[path]: "validation" for path in songs}

    corpus_manifest = tmp_path / "corpus.json"
    _write_json(
        corpus_manifest,
        {
            "tracks": [
                {"path": str(path), "sha256": hashes[path]}
                for path in songs
            ]
        },
    )
    split_map = tmp_path / "split.json"
    write_variable_split_authority(
        split_map,
        authority_from_mapping(assignments, assignments),
    )

    partial_root = tmp_path / "partial" / "manifest.json"
    pair_refs = []
    for index, (source, target) in enumerate(((songs[0], songs[1]), (songs[1], songs[0])), start=1):
        pair_path = partial_root.parent / "pairs" / f"{index:04d}" / "manifest.json"
        _write_json(
            pair_path,
            {
                "format_version": 1,
                "source_audio_sha256": hashes[source],
                "target_audio_sha256": hashes[target],
                "split": "validation",
                "producer_request_config_sha256": "a" * 64,
                "candidate_generation": {
                    "candidates": [{"candidate_id": f"candidate-{index}"}],
                    "generated_candidate_counts_by_length": {"2": 1, "4": 0, "6": 0, "8": 0},
                },
                "candidate_ranking": {"failures": []},
                "failures": [],
            },
        )
        if index == 1:
            pair_refs.append(
                {
                    "status": "completed",
                    "manifest_path": str(pair_path.relative_to(partial_root.parent)),
                    "pair_manifest_sha256": _sha(pair_path),
                }
            )

    _write_json(
        partial_root,
        {
            "producer_request_config_sha256": "a" * 64,
            "sources": [
                {
                    "source_path": str(songs[0]),
                    "source_audio_sha256": hashes[songs[0]],
                    "split": "validation",
                    "status": "completed",
                    "song_ranking": {"scores": []},
                    "pairs": pair_refs,
                },
                {
                    "source_path": str(songs[1]),
                    "source_audio_sha256": hashes[songs[1]],
                    "split": "validation",
                    "status": "running",
                    "pairs": [],
                },
            ],
        },
    )
    supplemental_root = tmp_path / "supplemental" / "manifest.json"
    supplemental_pair = supplemental_root.parent / "pairs" / "extra" / "manifest.json"
    _write_json(
        supplemental_pair,
        {
            "format_version": 1,
            "source_audio_sha256": hashes[songs[0]],
            "target_audio_sha256": hashes[songs[2]],
            "split": "validation",
            "producer_request_config_sha256": "b" * 64,
            "candidate_generation": {
                "candidates": [{"candidate_id": "supplemental-candidate"}],
                "generated_candidate_counts_by_length": {"2": 1, "4": 0, "6": 0, "8": 0},
            },
            "candidate_ranking": {"failures": []},
            "failures": [],
        },
    )
    _write_json(
        supplemental_root,
        {
            "producer_request_config_sha256": "b" * 64,
            "sources": [
                {
                    "source_audio_sha256": hashes[songs[0]],
                    "pairs": [
                        {
                            "status": "completed",
                            "split": "validation",
                            "manifest_path": str(supplemental_pair.relative_to(supplemental_root.parent)),
                            "pair_manifest_sha256": _sha(supplemental_pair),
                        }
                    ],
                }
            ],
        },
    )
    original_partial_sha = _sha(partial_root)

    recovered_path = recover_variable_producer_root(
        partial_root,
        corpus_manifest,
        split_map,
        tmp_path / "recovered",
        supplemental_roots=(supplemental_root,),
    )
    recovered = json.loads(recovered_path.read_text(encoding="utf-8"))

    assert recovered["status"] == "completed_recovered_from_pair_manifests"
    assert [source["status"] for source in recovered["sources"]] == ["completed", "completed"]
    assert [len(source["pairs"]) for source in recovered["sources"]] == [2, 1]
    assert recovered["sources"][0]["song_ranking"] == {"scores": []}
    assert recovered["sources"][1]["song_ranking"] is None
    assert recovered["recovery"]["pair_manifest_count"] == 2
    assert recovered["recovery"]["supplemental_validation_pair_count"] == 1
    assert recovered["recovery"]["source_ranking_count_recovered"] == 1
    assert len(_discover_pair_manifests(recovered_path.parent / "manifest.json")) == 3
    assert _sha(partial_root) == original_partial_sha
