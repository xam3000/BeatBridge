"""Synthetic audit smoke for the sealed Cue-Ranker train/serve chain."""

import json

import numpy as np
from torch.utils.data import DataLoader

from src.analysis.models import BeatGridMetadata
from src.candidates.models import CutPoint, TrackReference, TransitionCandidate
from src.features.cue_ranker_dataset import export_cue_ranker_dataset
from src.features.cue_ranker_universe import build_cue_ranker_universe, write_cue_ranker_pair_index
from src.features.extract_track import TrackFeatureArtifact
from src.ml.cue_ranker_data import CueRankerGroupedDataset, collate_cue_ranker_groups
from src.ml.cue_ranker_runner import CueRankerTrainingConfig, train_cue_ranker
from src.ml.cue_ranker_teacher import TeacherEvaluation, label_cue_ranker_teacher
from src.ml.wandb_logging import WandbConfig
from src.ranking.learned_cue_ranker import load_learned_cue_ranker, rank_candidates_learned

from test_cue_ranker_feature_loader import _feature_cache, _sha_bytes
from test_cue_ranker_teacher import _release
from test_cue_ranker_universe import _candidate, _pair_manifest, _record, _sha


def _candidate_with_tempo(source, target, identifier, bars):
    candidate = _candidate(
        source, target, identifier, bars, source_sample=2_000, target_sample=8_000,
    )
    candidate["source_bpm"] = 128.0
    candidate["target_bpm"] = 128.0
    return candidate


def _artifact(cache_root, audio_sha):
    manifest_path = next(
        (cache_root / "feature_protocol_v2" / audio_sha[:16]).glob("*/manifest.json")
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    with np.load(manifest_path.parent / manifest["data_file"], allow_pickle=False) as data:
        arrays = {
            name: np.asarray(data[name])
            for name in (
                "base_features", "bin_boundaries", "spectral_flux_raw", "onset_strength_raw",
            )
        }
    return TrackFeatureArtifact(
        cache_directory=manifest_path.parent,
        manifest=manifest,
        cache_hit=True,
        **arrays,
    )


def _inference_candidate(payload):
    source_grid = BeatGridMetadata.from_dict(payload["source_grid"])
    target_grid = BeatGridMetadata.from_dict(payload["target_grid"])
    return TransitionCandidate(
        candidate_id=payload["candidate_id"],
        source_track=TrackReference(**payload["source_track"]),
        target_track=TrackReference(**payload["target_track"]),
        source_cutpoint=CutPoint(**payload["source_cutpoint"]),
        target_cutpoint=CutPoint(**payload["target_cutpoint"]),
        transition_length_bars=payload["transition_length_bars"],
        transition_length_beats=payload["transition_length_beats"],
        source_bpm=payload["source_bpm"],
        target_bpm=payload["target_bpm"],
        tempo_relative_difference=0.0,
        generator=payload["generator"],
        filter_status=payload["filter_status"],
        format_version=payload["format_version"],
        source_grid=source_grid,
        target_grid=target_grid,
    )


def test_pair_index_to_offline_resume_and_learned_inference_smoke(tmp_path, monkeypatch):
    """Exercise every auditable boundary with synthetic train/validation only."""

    source_train, target_train, source_valid, target_valid = (
        _sha(value)
        for value in ("e2e-source-train", "e2e-target-train", "e2e-source-valid", "e2e-target-valid")
    )
    cache_root = tmp_path / "feature-cache"
    cache_hashes = {
        sha: _feature_cache(cache_root, sha, 128.0)
        for sha in (source_train, target_train, source_valid, target_valid)
    }
    train_manifest, validation_manifest = tmp_path / "train-pair.json", tmp_path / "validation-pair.json"
    train_candidates = [
        _candidate_with_tempo(source_train, target_train, f"train-{bars}", bars)
        for bars in (2, 4, 6, 8)
    ]
    validation_candidates = [
        _candidate_with_tempo(source_valid, target_valid, f"validation-{bars}", bars)
        for bars in (2, 4, 6, 8)
    ]
    _pair_manifest(train_manifest, train_candidates)
    _pair_manifest(validation_manifest, validation_candidates)
    split_map = {
        source_train: "train", target_train: "train",
        source_valid: "validation", target_valid: "validation",
    }
    index = write_cue_ranker_pair_index(
        [
            _record(train_manifest, source_train, target_train, "train"),
            _record(validation_manifest, source_valid, target_valid, "validation"),
        ],
        tmp_path / "pair-index.json",
        split_map=split_map,
    )
    universe = build_cue_ranker_universe(index, tmp_path / "universe", split_map=split_map).output_directory
    assert json.loads((universe / "manifest.json").read_text(encoding="utf-8"))["test"] == {
        "state": "sealed_not_materialized"
    }

    normalizer_source = tmp_path / "normalizer-source.json"
    normalizer_source.write_text(
        json.dumps({
            "fit_scope": "training_tracks_only", "stats_id": "e2e-synthetic",
            "spectral_flux_log1p_p99": 1.0, "onset_strength_log1p_p99": 1.0,
            "training_audio_sha256": [source_train, target_train],
            "input_universe_manifest_sha256": _sha_bytes(universe / "manifest.json"),
        }),
        encoding="utf-8",
    )
    release = _release(tmp_path)

    def evaluator(row, _release_payload):
        candidate = row["candidate"]
        source = candidate["source_track"]["sha256"]
        target = candidate["target_track"]["sha256"]
        provenance = {
            "alignment_contract": "local_grid_target_to_source_v1",
            "normalizer_sha256": _sha_bytes(normalizer_source),
            "source_feature_payload_sha256": cache_hashes[source][0],
            "source_feature_manifest_sha256": cache_hashes[source][1],
            "target_feature_payload_sha256": cache_hashes[target][0],
            "target_feature_manifest_sha256": cache_hashes[target][1],
        }
        guard_score = 0.1 if candidate["transition_length_bars"] == 8 else 0.9
        return TeacherEvaluation(-float(candidate["transition_length_bars"]), guard_score, provenance)

    labels = label_cue_ranker_teacher(universe, release, tmp_path / "labels", evaluator=evaluator).output_directory
    teacher_manifest = json.loads((labels / "manifest.json").read_text(encoding="utf-8"))
    assert teacher_manifest["test"] == {"state": "sealed_not_materialized"}
    assert teacher_manifest["counts"]["train"]["guard_rejected"] == 1

    dataset = export_cue_ranker_dataset(
        universe, labels, tmp_path / "dataset", train_only_normalizer=normalizer_source,
    ).output_directory
    dataset_manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    assert dataset_manifest["test"] == {"state": "sealed_not_materialized"}
    assert not (dataset / "test").exists()
    train = CueRankerGroupedDataset(dataset, "train", feature_cache_root=cache_root)
    validation = CueRankerGroupedDataset(dataset, "validation", feature_cache_root=cache_root)
    train_loader = DataLoader(train, batch_size=1, collate_fn=collate_cue_ranker_groups)
    validation_loader = DataLoader(validation, batch_size=1, collate_fn=collate_cue_ranker_groups)
    run = tmp_path / "ranker-run"
    run_kwargs = {
        "dataset_manifest_sha256": _sha_bytes(dataset / "manifest.json"),
        "wandb_config": WandbConfig(mode="offline", project="beatbridge-cue-ranker-audit"),
        "progress": lambda _message: None,
    }
    first = train_cue_ranker(
        train_loader,
        validation_loader,
        run,
        config=CueRankerTrainingConfig(max_epochs=1, patience=3, device="cpu"),
        **run_kwargs,
    )
    second = train_cue_ranker(
        train_loader,
        validation_loader,
        run,
        resume=True,
        config=CueRankerTrainingConfig(max_epochs=2, patience=3, device="cpu"),
        **run_kwargs,
    )
    assert (first.last_epoch, second.last_epoch) == (1, 2)
    run_manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert (run / "manifest.sha256").read_text(encoding="utf-8").split()[0] == _sha_bytes(run / "manifest.json")
    assert all(_sha_bytes(run / record["path"]) == record["sha256"] for record in run_manifest["files"].values() if record)
    assert len(json.loads((run / "history.json").read_text(encoding="utf-8"))["epochs"]) == 2
    assert (run / "wandb").is_dir()

    loaded = load_learned_cue_ranker(run, dataset_manifest_path=dataset / "manifest.json")
    artifacts = {
        "source.wav": _artifact(cache_root, source_train),
        "target.wav": _artifact(cache_root, target_train),
    }
    monkeypatch.setattr(
        "src.ranking.learned_cue_ranker.extract_or_load_track_features",
        lambda song_path, **_kwargs: artifacts[song_path],
    )
    candidates = tuple(_inference_candidate(candidate) for candidate in train_candidates)
    first_ranking = rank_candidates_learned(candidates, loaded_ranker=loaded)
    second_ranking = rank_candidates_learned(candidates, loaded_ranker=loaded)
    assert not first_ranking.failures
    assert [item.to_dict() for item in first_ranking.scores] == [item.to_dict() for item in second_ranking.scores]
    assert {score.candidate_id for score in first_ranking.scores} == {candidate.candidate_id for candidate in candidates}
