import json
from dataclasses import replace

import numpy as np
import pytest
import soundfile as sf

from src.analysis.models import AnalysisResult, BeatGridMetadata
from src.batch_render import build_argument_parser, render_candidate_batch
from src.candidates import CandidateGenerationConfig, CandidateGenerationResult
from src.pipeline import generate_transition_candidates
from src.tempo.simple_tempo_adjust import SimpleTempoAdjust


class StubAnalysis:
    def __call__(self, song_path):
        info = sf.info(song_path)
        beat_step = info.samplerate // 2  # 120 BPM
        beats = [
            (sample, index % 4 + 1, 4)
            for index, sample in enumerate(range(0, info.frames, beat_step))
        ]
        return AnalysisResult(
            120.0,
            tuple(beats),
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
    analysis = StubAnalysis()
    candidates = generate_transition_candidates(
        song1,
        song2,
        analysis=analysis,
        config=CandidateGenerationConfig(
            transition_lengths_bars=(1,),
            source_boundary_count=1,
            target_boundary_count=1,
        ),
    )
    return candidates, analysis, tmp_path / "batch"


def test_batch_render_exports_wavs_and_a_traceable_manifest(batch_inputs):
    candidates, analysis, output_directory = batch_inputs

    result = render_candidate_batch(
        candidates,
        output_directory,
        renderers=("simple", "fade"),
        analysis=analysis,
    )

    assert not result.failures
    assert len(result.rendered_variants) == 2
    assert result.manifest_path.is_file()
    for variant in result.rendered_variants:
        output_path = output_directory / variant.output_file
        assert output_path.is_file()
        assert sf.info(output_path).samplerate == 44_100
        assert variant.candidate_id == candidates.candidates[0].candidate_id

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["format_version"] == 1
    assert manifest["render_protocol_version"] == 5
    assert manifest["candidate_generation"]["candidates"][0]["candidate_id"] == candidates.candidates[0].candidate_id
    assert manifest["candidate_ranking"]["ranker"] == "feature_baseline_v3"
    assert manifest["candidate_ranking"]["scores"][0]["rank"] == 1
    assert manifest["rendered_transition_ranking"]["metric"] == "rendered_transition_baseline_v1"
    assert len(manifest["rendered_transition_ranking"]["scores"]) == 2
    assert not manifest["rendered_transition_ranking"]["failures"]
    assert manifest["render_selection"]["top_k"] == 5
    assert [item["renderer"] for item in manifest["rendered_variants"]] == ["simple", "fade"]
    assert all(item["candidate_rank"] == 1 for item in manifest["rendered_variants"])
    assert all(item["transition_rank"] is not None for item in manifest["rendered_variants"])
    assert all(0.0 <= item["transition_score"] <= 1.0 for item in manifest["rendered_variants"])
    assert all(
        item["transition_end_sample"] >= item["transition_start_sample"]
        for item in manifest["rendered_variants"]
    )
    assert all(
        item["tempo_backend"] == "not_needed"
        for item in manifest["rendered_variants"]
    )
    assert manifest["render_preview"] == {
        "seconds_before_source_cutpoint": 5.0,
        "seconds_after_source_cutpoint": 12.0,
    }
    assert all(variant.sample_count <= 17 * 44_100 for variant in result.rendered_variants)


def test_batch_render_refuses_to_replace_existing_artifacts_without_opt_in(batch_inputs):
    candidates, analysis, output_directory = batch_inputs
    render_candidate_batch(candidates, output_directory, renderers=("simple",), analysis=analysis)

    with pytest.raises(FileExistsError, match="overwrite=True"):
        render_candidate_batch(candidates, output_directory, renderers=("simple",), analysis=analysis)


def test_batch_passes_candidate_bpms_to_every_renderer(batch_inputs, monkeypatch):
    candidates, analysis, output_directory = batch_inputs
    candidate = candidates.candidates[0]
    candidate = replace(candidate, source_bpm=120.0, target_bpm=100.0)
    generation = CandidateGenerationResult((candidate,), candidates.rejections)
    from src import batch_render

    recorded_bpms = []
    original_render_transition = batch_render.render_transition

    def record_render_transition(*args, **kwargs):
        recorded_bpms.append((kwargs["source_bpm"], kwargs["target_bpm"]))
        kwargs["tempo_adjuster"] = SimpleTempoAdjust()
        return original_render_transition(*args, **kwargs)

    monkeypatch.setattr(batch_render, "render_transition", record_render_transition)

    result = render_candidate_batch(
        generation,
        output_directory,
        renderers=("simple", "fade", "equal_power", "tempo_fade"),
        analysis=analysis,
    )

    assert not result.failures
    assert recorded_bpms == [(120.0, 100.0)] * 4


def test_batch_cli_accepts_all_variable_transition_lengths():
    args = build_argument_parser().parse_args(
        [
            "source.wav",
            "target.wav",
            "--output-dir",
            "output/variable-test",
            "--transition-bars",
            "2",
            "4",
            "6",
            "8",
        ]
    )

    assert tuple(args.transition_bars) == (2, 4, 6, 8)


def test_mert_batch_contract_and_filtered_selection(batch_inputs, monkeypatch):
    from src import batch_render
    from src.candidates import BaselineCandidateGenerationConfig
    from src.ranking import continuation
    from src.ranking.feature_baseline import RankingFailure

    original, analysis, out = batch_inputs
    method = continuation.METHOD
    with pytest.raises(ValueError, match="four 4/4"):
        render_candidate_batch(original, out, ranking_method=method)
    first = original.candidates[0]
    generate = batch_render.generate_transition_candidates

    def capture(*args, config, **kwargs):
        assert isinstance(config, BaselineCandidateGenerationConfig)
        assert config.transition_lengths_bars == (4,)
        return generate(*args, config=config, **kwargs)

    monkeypatch.setattr(batch_render, "generate_transition_candidates", capture)
    def stub(candidates, analysis, rate):
        assert len(candidates) > 1
        return continuation.ContinuationRanking(
            (continuation.ContinuationScore(candidates[-1].candidate_id, 1, .75),),
            {"fixture": "stub"},
            tuple(RankingFailure(c.candidate_id, "incomplete_bar_window", "fixture") for c in candidates[:-1]))

    monkeypatch.setattr(continuation, "rank_continuations", stub)
    batch = batch_render.generate_and_render_batch(first.source_track.path, first.target_track.path, out,
              analysis=analysis, ranking_method=method, top_k=3, renderers=("equal_power",))
    result = json.loads(batch.manifest_path.read_text(encoding="utf-8"))
    winner = batch.candidate_generation.candidates[-1].candidate_id
    assert result["cue_ranking"]["provenance"] == {"fixture": "stub"}
    assert result["cue_ranking"]["scores"] == [dict(candidate_id=winner, rank=1, total_score=.75)]
    assert [r["candidate_id"] for r in result["candidate_ranking"]["scores"]] == [winner]
    assert result["render_selection"]["candidate_ids"] == [winner]
    assert len(result["rendered_variants"]) == 1
    assert result["rendered_variants"][0]["selection_score"] == .75
    assert result["cue_ranking"]["failures"] and not result["failures"]
