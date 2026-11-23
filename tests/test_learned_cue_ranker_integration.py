import json
from dataclasses import replace
import hashlib
from types import SimpleNamespace

import pytest
import numpy as np
import soundfile as sf

from src.analysis.models import AnalysisResult, BeatGridMetadata
from src.batch_render import build_argument_parser as build_batch_parser
from src.batch_render import render_candidate_batch
from src.candidates import CandidateGenerationConfig, VariableCandidateGenerationConfig
from src.pipeline import generate_transition_candidates
from src.multi_batch_render import build_argument_parser as build_multi_parser
from src.multi_batch_render import generate_multi_song_batch
from src.multi_batch_render import main as multi_main
from src.ranking.feature_baseline import CandidateScore, RankingFailure
from src.ranking.learned_cue_ranker import (
    LearnedCueRankingResult,
    load_learned_cue_ranker,
    _load_normalizer,
    _validate_hard_filter_contract,
)
from src.ml.cue_ranker_model import CueRankerTemporalConfig, CUE_RANKER_MODEL_NAME
from src.ml.cue_ranker_runner import CUE_RANKER_RUN_FORMAT_VERSION, CUE_RANKER_RUNNER_NAME


class _StubAnalysis:
    def __call__(self, song_path):
        info = sf.info(song_path)
        beat_step = info.samplerate // 2
        beats = tuple(
            (sample, index % 4 + 1, 4)
            for index, sample in enumerate(range(0, info.frames, beat_step))
        )
        return AnalysisResult(
            120.0,
            beats,
            BeatGridMetadata(
                grid_source="test_detector",
                fallback_used=False,
                backend_version="test_detector=1",
                confidence=0.9,
            ),
        )


@pytest.fixture
def batch_inputs(tmp_path):
    song1 = tmp_path / "song1.wav"
    song2 = tmp_path / "song2.wav"
    sf.write(song1, np.zeros(44_100 * 20, dtype=np.float32), 44_100)
    sf.write(song2, np.zeros(48_000 * 20, dtype=np.float32), 48_000)
    analysis = _StubAnalysis()
    candidates = generate_transition_candidates(
        song1,
        song2,
        analysis=analysis,
        config=CandidateGenerationConfig(
            transition_lengths_bars=(2,),
            source_boundary_count=1,
            target_boundary_count=1,
        ),
    )
    return candidates, analysis, tmp_path / "batch"


def test_cli_keeps_feature_baseline_default_and_accepts_learned_opt_in():
    batch_default = build_batch_parser().parse_args(["a.wav", "b.wav", "--output-dir", "out"])
    batch_learned = build_batch_parser().parse_args(
        ["a.wav", "b.wav", "--output-dir", "out", "--ranking-method", "learned_cue_ranker_v1"]
    )
    multi_default = build_multi_parser().parse_args(["a.wav", "b.wav", "--output-dir", "out"])
    multi_learned = build_multi_parser().parse_args(
        ["a.wav", "b.wav", "--output-dir", "out", "--ranking-method", "learned_cue_ranker_v1"]
    )

    assert batch_default.ranking_method == "feature_baseline_v3"
    assert multi_default.ranking_method == "feature_baseline_v3"
    assert batch_learned.ranking_method == "learned_cue_ranker_v1"
    assert multi_learned.ranking_method == "learned_cue_ranker_v1"


def test_multi_batch_rejects_missing_learned_run_before_writing_output(tmp_path):
    source = tmp_path / "source.wav"
    target = tmp_path / "target.wav"
    source.write_bytes(b"synthetic")
    target.write_bytes(b"synthetic-target")
    run = tmp_path / "missing-run"
    run.mkdir()

    with pytest.raises(FileNotFoundError, match="run manifest is missing"):
        generate_multi_song_batch(
            [source, target],
            tmp_path / "output",
            ranking_method="learned_cue_ranker_v1",
            cue_ranker_run=run,
        )
    assert not (tmp_path / "output").exists()


def test_multi_cli_reports_missing_learned_checkpoint_clearly(tmp_path, capsys):
    source = tmp_path / "source.wav"
    target = tmp_path / "target.wav"
    source.write_bytes(b"synthetic")
    target.write_bytes(b"synthetic-target")
    run = tmp_path / "missing-run"
    run.mkdir()

    exit_code = multi_main(
        [
            str(source),
            str(target),
            "--output-dir",
            str(tmp_path / "output"),
            "--ranking-method",
            "learned_cue_ranker_v1",
            "--cue-ranker-run",
            str(run),
        ]
    )

    assert exit_code == 1
    assert "learned_cue_ranker_v1 preflight failed" in capsys.readouterr().err


def test_invalid_learned_checkpoint_is_rejected_after_hash_preflight(tmp_path):
    dataset_root = tmp_path / "dataset"
    normalizer = dataset_root / "normalization" / "train_only_stats.json"
    normalizer.parent.mkdir(parents=True)
    normalizer.write_text(
        json.dumps(
            {
                "fit_scope": "training_tracks_only",
                "spectral_flux_log1p_p99": 1.0,
                "onset_strength_log1p_p99": 1.0,
                "stats_id": "synthetic",
                "input_universe_manifest_sha256": "d" * 64,
                "source_sha256": "e" * 64,
                "training_audio_sha256": ["a" * 64],
            }
        ),
        encoding="utf-8",
    )

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    dataset_manifest = dataset_root / "manifest.json"
    dataset_manifest.write_text(
        json.dumps(
            {
                "format_version": 3,
                "test": {"state": "sealed_not_materialized"},
                "universe_manifest_sha256": "d" * 64,
                "teacher_manifest_sha256": "t" * 64,
                "teacher_release_sha256": "r" * 64,
                "teacher_contract_sha256": "c" * 64,
                "teacher_alignment_contract": "local_grid_target_to_source_v1",
                "normalization": {
                    "fit_scope": "training_tracks_only",
                    "sha256": sha(normalizer),
                    "source_sha256": "e" * 64,
                },
                "files": {
                    "train_only_normalizer": {
                        "path": "normalization/train_only_stats.json",
                        "sha256": sha(normalizer),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    config = CueRankerTemporalConfig().to_dict()
    contract = {
        "format_version": 1,
        "runner_name": CUE_RANKER_RUNNER_NAME,
        "model_name": CUE_RANKER_MODEL_NAME,
        "model_format_version": 1,
        "dataset_manifest_sha256": sha(dataset_manifest),
        "model": {"name": CUE_RANKER_MODEL_NAME, "config": config},
    }
    run_root = tmp_path / "run"
    run_root.mkdir()
    checkpoint = run_root / "best.pt"
    checkpoint.write_bytes(b"not-a-torch-checkpoint")
    run_manifest = run_root / "manifest.json"
    run_manifest.write_text(
        json.dumps(
            {
                "format_version": CUE_RANKER_RUN_FORMAT_VERSION,
                "runner_name": CUE_RANKER_RUNNER_NAME,
                "status": "completed",
                "run_id": "synthetic-run",
                "contract": contract,
                "files": {"best": {"path": "best.pt", "sha256": sha(checkpoint)}},
            }
        ),
        encoding="utf-8",
    )
    (run_root / "manifest.sha256").write_text(
        f"{sha(run_manifest)}  manifest.json\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="cannot be loaded"):
        load_learned_cue_ranker(run_root, dataset_manifest_path=dataset_manifest)


def test_inference_normalizer_rejects_payload_scope_mismatch(tmp_path):
    normalizer = tmp_path / "normalizer.json"
    normalizer.write_text(
        json.dumps(
            {
                "fit_scope": "all_splits",
                "stats_id": "synthetic",
                "spectral_flux_log1p_p99": 1.0,
                "onset_strength_log1p_p99": 1.0,
                "input_universe_manifest_sha256": "d" * 64,
                "source_sha256": "e" * 64,
                "training_audio_sha256": ["a" * 64],
            }
        ),
        encoding="utf-8",
    )
    digest = hashlib.sha256(normalizer.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="invalid fit scope"):
        _load_normalizer(
            tmp_path / "manifest.json",
            {
                "universe_manifest_sha256": "d" * 64,
                "normalization": {
                    "fit_scope": "training_tracks_only",
                    "sha256": digest,
                    "source_sha256": "e" * 64,
                },
                "files": {"train_only_normalizer": {"path": "normalizer.json", "sha256": digest}},
            },
        )


def test_learned_ranker_cannot_accept_legacy_or_unverified_candidates(batch_inputs):
    candidates, _analysis, _output = batch_inputs
    with pytest.raises(ValueError, match="Candidate-v2"):
        _validate_hard_filter_contract(candidates.candidates)


def test_learned_selection_is_additive_and_renderer_manifest_compatible(batch_inputs, monkeypatch):
    candidates, analysis, output_directory = batch_inputs
    first = candidates.candidates[0]
    first = replace(
        first,
        generator="bar_grid_v2_length_specific",
        format_version=2,
        transition_length_bars=2,
        transition_length_beats=8,
        source_grid=replace(first.source_grid, beat_grid_sha256="a" * 64),
        target_grid=replace(first.target_grid, beat_grid_sha256="b" * 64),
    )
    second = replace(first, candidate_id="candidate-second")
    generation = replace(candidates, candidates=(first, second), format_version=2)

    ranking = LearnedCueRankingResult(
        scores=(
            CandidateScore("candidate-second", 1, 0.9, {"model_score": 0.9}, {}),
            CandidateScore(first.candidate_id, 2, 0.1, {"model_score": 0.1}, {}),
        ),
        failures=(),
        provenance={
            "checkpoint": {"sha256": "c" * 64},
            "run_manifest": {"sha256": "r" * 64},
            "dataset": {"sha256": "d" * 64, "format_version": 3},
            "teacher": {"release_sha256": "t" * 64, "contract_sha256": "u" * 64},
        },
    )
    monkeypatch.setattr("src.batch_render.load_learned_cue_ranker", lambda *args, **kwargs: object())
    monkeypatch.setattr("src.batch_render.rank_candidates_learned", lambda *args, **kwargs: ranking)

    result = render_candidate_batch(
        generation,
        output_directory,
        renderers=("simple",),
        analysis=analysis,
        ranking_method="learned_cue_ranker_v1",
        cue_ranker_run="synthetic-run",
        cue_ranker_dataset="synthetic-dataset",
        top_k=1,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert result.candidate_ranking.ranker == "feature_baseline_v3"
    assert manifest["ranking_method"] == "learned_cue_ranker_v1"
    assert manifest["candidate_ranking"]["ranker"] == "feature_baseline_v3"
    assert manifest["cue_ranking"]["ranker"] == "learned_cue_ranker_v1"
    assert manifest["cue_ranking"]["model_name"] == "learned_cue_ranker_v1"
    assert manifest["cue_ranking"]["checkpoint_sha256"] == "c" * 64
    assert manifest["cue_ranking"]["dataset_manifest_sha256"] == "d" * 64
    assert manifest["cue_ranking"]["teacher_contract"]["contract_sha256"] == "u" * 64
    assert manifest["cue_ranking"]["scores"][0]["candidate_id"] == "candidate-second"
    assert manifest["cue_ranking"]["selection_candidate_ids"] == ["candidate-second"]
    assert manifest["rendered_variants"][0]["selection_method"] == "learned_cue_ranker_v1"
    assert manifest["rendered_variants"][0]["selection_score"] == 0.9
    assert manifest["render_selection"]["candidate_ids"] == ["candidate-second"]


def test_learned_render_failure_backfills_next_ranked_candidate(batch_inputs, monkeypatch):
    candidates, analysis, output_directory = batch_inputs
    first = replace(
        candidates.candidates[0],
        generator="bar_grid_v2_length_specific",
        format_version=2,
        transition_length_bars=2,
        transition_length_beats=8,
        source_grid=replace(candidates.candidates[0].source_grid, beat_grid_sha256="a" * 64),
        target_grid=replace(candidates.candidates[0].target_grid, beat_grid_sha256="b" * 64),
    )
    rejected = replace(first, candidate_id="candidate-rejected")
    fallback = replace(first, candidate_id="candidate-fallback")
    generation = replace(candidates, candidates=(first, rejected, fallback), format_version=2)
    ranking = LearnedCueRankingResult(
        scores=(
            CandidateScore(rejected.candidate_id, 1, 0.9, {"model_score": 0.9}, {}),
            CandidateScore(fallback.candidate_id, 2, 0.8, {"model_score": 0.8}, {}),
            CandidateScore(first.candidate_id, 3, 0.1, {"model_score": 0.1}, {}),
        ),
        failures=(),
        provenance={},
    )
    from src.variable_rendering import render_variable_transition as real_render

    def render_with_one_failure(candidate, *args, **kwargs):
        if candidate.candidate_id == rejected.candidate_id:
            raise RuntimeError("synthetic render failure")
        return real_render(candidate, *args, **kwargs)

    monkeypatch.setattr("src.batch_render.load_learned_cue_ranker", lambda *args, **kwargs: object())
    monkeypatch.setattr("src.batch_render.rank_candidates_learned", lambda *args, **kwargs: ranking)
    monkeypatch.setattr("src.batch_render.render_variable_transition", render_with_one_failure)

    result = render_candidate_batch(
        generation,
        output_directory,
        renderers=("simple",),
        analysis=analysis,
        ranking_method="learned_cue_ranker_v1",
        cue_ranker_run="synthetic-run",
        cue_ranker_dataset="synthetic-dataset",
        top_k=1,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert [variant.candidate_id for variant in result.rendered_variants] == [fallback.candidate_id]
    assert [failure.candidate_id for failure in result.failures] == [rejected.candidate_id]
    assert manifest["cue_ranking"]["selection_candidate_ids"] == [fallback.candidate_id]
    assert manifest["cue_ranking"]["backfill"]["skipped_candidate_ids"] == [rejected.candidate_id]
    assert manifest["cue_ranking"]["backfill"]["partial"] is False


def test_multi_cli_uses_variable_candidate_contract_for_learned_method():
    from src.multi_batch_render import _candidate_generation_config

    config = _candidate_generation_config(
        (2, 4),
        approximate_grid_policy="reject",
        ranking_method="learned_cue_ranker_v1",
    )
    assert isinstance(config, VariableCandidateGenerationConfig)
    assert config.transition_lengths_bars == (2, 4)
