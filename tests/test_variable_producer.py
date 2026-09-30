import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.analysis.models import BeatGridMetadata
from src.candidates.models import TrackReference
from src.candidates.variable import generate_variable_candidates_from_grids
from src.features.variable_split import authority_from_mapping, write_variable_split_authority
from src.ranking.feature_baseline import CandidateRankingResult, CandidateScore, FeatureRankingConfig
from src.variable_producer import generate_variable_candidate_producer


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_candidate_only_producer_is_split_aware_and_compact(tmp_path, monkeypatch):
    songs = []
    for name in ("a.wav", "b.wav"):
        path = tmp_path / name
        path.write_bytes(name.encode("ascii"))
        songs.append(path)
    assignments = {_sha(path): "train" for path in songs}
    split_map = tmp_path / "split.json"
    write_variable_split_authority(
        split_map,
        authority_from_mapping(assignments, assignments),
    )

    class FakeAnalysis:
        def __init__(self, _root):
            pass

        def __call__(self, _path):
            return 150.0, []

    def fake_song_ranking(source, targets, **_kwargs):
        scores = tuple(
            SimpleNamespace(target_path=target, rank=index, total_score=1.0)
            for index, target in enumerate(targets, start=1)
        )
        return SimpleNamespace(scores=scores, to_dict=lambda: {"scores": [vars(item) for item in scores]})

    metadata = BeatGridMetadata("partial_merge_v2", False, "test", 1.0)
    grid = [(index * 100, index % 4 + 1, 4) for index in range(128)]

    def fake_generation(source, target, *, config, **_kwargs):
        return generate_variable_candidates_from_grids(
            TrackReference(str(source), _sha(source)),
            150.0,
            grid,
            TrackReference(str(target), _sha(target)),
            150.0,
            grid,
            source_grid_metadata=metadata,
            target_grid_metadata=metadata,
            config=config,
        )

    def fake_ranking(candidates, **_kwargs):
        candidate = candidates[0]
        return CandidateRankingResult(
            scores=(CandidateScore(candidate.candidate_id, 1, 1.0, {}, {}),),
            failures=(),
            config=FeatureRankingConfig(),
        )

    monkeypatch.setattr("src.variable_producer.PartialPreAnalysis", FakeAnalysis)
    monkeypatch.setattr("src.variable_producer.rank_song_targets", fake_song_ranking)
    monkeypatch.setattr("src.variable_producer.generate_transition_candidates", fake_generation)
    monkeypatch.setattr("src.variable_producer.rank_candidates", fake_ranking)

    root_path = generate_variable_candidate_producer(
        [str(path) for path in songs],
        tmp_path / "producer",
        split_map=split_map,
        analysis_location=tmp_path / "analysis",
        top_targets=1,
        top_candidates_per_length=1,
        transition_lengths_bars=(2, 4, 6, 8),
        source_workers=2,
    )
    root = json.loads(root_path.read_text(encoding="utf-8"))
    assert root["renderers"] == []
    assert root["status"] == "completed"
    assert root["audio_materialized"] is False
    assert len(root["producer_request_config_sha256"]) == 64
    assert not list((tmp_path / "producer").rglob("*.wav"))
    assert len(root["sources"]) == 2
    for source in root["sources"]:
        pair = source["pairs"][0]
        assert pair["split"] == source["split"] == "train"
        assert pair["selected_candidate_count"] == 4
        payload = json.loads((root_path.parent / pair["manifest_path"]).read_text(encoding="utf-8"))
        assert {item["transition_length_bars"] for item in payload["candidate_generation"]["candidates"]} == {2, 4, 6, 8}
        assert payload["rendered_variants"] == []


def test_candidate_producer_excludes_closed_test_before_opening_audio(tmp_path, monkeypatch):
    paths = []
    for name in ("train.wav", "validation.wav", "test.wav"):
        path = tmp_path / name
        path.write_bytes(name.encode("ascii"))
        paths.append(path)
    train, validation, test = paths
    hashes = {path: _sha(path) for path in paths}
    assignments = {
        hashes[train]: "train",
        hashes[validation]: "validation",
        hashes[test]: "test",
    }
    split_map = tmp_path / "split.json"
    write_variable_split_authority(
        split_map,
        authority_from_mapping(assignments, assignments),
    )
    corpus_manifest = tmp_path / "corpus.json"
    corpus_manifest.write_text(
        json.dumps(
            {
                "tracks": [
                    {"path": str(path), "sha256": hashes[path]}
                    for path in paths
                ]
            }
        ),
        encoding="utf-8",
    )
    analysed = []

    class FakeAnalysis:
        def __init__(self, _root):
            pass

        def __call__(self, path):
            analysed.append(Path(path).resolve())
            return 150.0, []

    original_file_sha256 = __import__("src.variable_producer", fromlist=["_file_sha256"])._file_sha256

    def guarded_file_sha256(path):
        assert Path(path).resolve() != test.resolve()
        return original_file_sha256(path)

    monkeypatch.setattr("src.variable_producer.PartialPreAnalysis", FakeAnalysis)
    monkeypatch.setattr("src.variable_producer._file_sha256", guarded_file_sha256)

    root_path = generate_variable_candidate_producer(
        [str(path) for path in paths],
        tmp_path / "producer",
        split_map=split_map,
        analysis_location=tmp_path / "analysis",
        corpus_manifest_path=corpus_manifest,
    )
    root = json.loads(root_path.read_text(encoding="utf-8"))

    assert {Path(row["source_path"]).resolve() for row in root["sources"]} == {
        train.resolve(),
        validation.resolve(),
    }
    assert {path for path in analysed} == {train.resolve(), validation.resolve()}
    assert root["closed_split_exclusions"] == [
        {
            "path": str(test),
            "sha256": hashes[test],
            "split": "test",
            "reason": "closed_split",
        }
    ]
    assert root["producer_request_config"]["closed_split_names"] == ["test"]


def test_candidate_producer_requires_manifest_when_test_split_exists(tmp_path, monkeypatch):
    paths = []
    for name in ("train.wav", "test.wav"):
        path = tmp_path / name
        path.write_bytes(name.encode("ascii"))
        paths.append(path)
    assignments = {_sha(paths[0]): "train", _sha(paths[1]): "test"}
    split_map = tmp_path / "split.json"
    write_variable_split_authority(
        split_map,
        authority_from_mapping(assignments, assignments),
    )
    hashed_audio = []

    def guarded_deduplicate(audio_paths):
        hashed_audio.extend(audio_paths)
        raise AssertionError("audio must not be inspected before the closed-test gate")

    monkeypatch.setattr("src.variable_producer._deduplicate", guarded_deduplicate)
    with pytest.raises(ValueError, match="corpus manifest is required"):
        generate_variable_candidate_producer(
            [str(path) for path in paths],
            tmp_path / "producer",
            split_map=split_map,
            analysis_location=tmp_path / "analysis",
        )
    assert hashed_audio == []
