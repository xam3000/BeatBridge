import numpy as np
import pytest
import soundfile as sf

from src.tempo.cue_alignment import CueAlignmentError, measure_cue_alignment
from src.pipeline import BeatBridgePipeline
from src.cutting.equal_power_fade_cut import EqualPowerFadeCut
from src.tempo.simple_tempo_adjust import SimpleTempoAdjust


def test_regression_recovers_tempo_despite_quantized_equal_bpm_fields():
    # A 512-sample analysis hop need not divide the physical beat period.
    beats = np.arange(161)
    a = np.rint(beats * 17813. / 512) * 512
    b = np.rint(beats * 18191. / 512) * 512
    fit = measure_cue_alignment(a, b, 61, 93, 16, 48000)
    fit.require_valid()
    assert fit.tempo_factor == pytest.approx(18191 / 17813, rel=.0004)
    assert fit.source_fit_beats == fit.target_fit_beats == 64


def test_interior_displaced_beat_rejects_equal_spans():
    a = np.arange(129) * 18000
    b = a.copy()
    b[64 - 8] += 3500
    fit = measure_cue_alignment(a, b, 40, 64, 16, 48000)
    assert fit.span_error_ms < 20
    assert fit.beat_offset_ms > 60
    with pytest.raises(CueAlignmentError, match="cross-track offset"):
        fit.require_valid()


def test_missing_beat_at_boundary_rejects_cue():
    with pytest.raises(CueAlignmentError, match="Incomplete"):
        measure_cue_alignment(np.arange(40), np.arange(40), 35, 24, 16, 48000)


def test_bpm_only_fallback_has_no_observations():
    from src.tempo.cue_alignment import require_observed_grid
    with pytest.raises(CueAlignmentError, match="no observed"):
        require_observed_grid({"grid_source": "fallback_from_bpm"})


def test_equal_bpm_fields_still_stretch_at_the_cue(tmp_path):
    rate = 8000
    files, grids = [], {}
    for role, period in (("a", 3000), ("b", 3090)):
        path = tmp_path / f"{role}.wav"
        files.append(path)
        samples = np.arange(81) * period
        grids[str(path)] = [(int(s), i % 4 + 1, 4) for i, s in enumerate(samples)]
        audio = np.zeros(samples[-1] + 10, dtype=np.float32)
        audio[samples] = .5
        sf.write(path, audio, rate, subtype="FLOAT")

    def analysis(path):
        return 160., grids[str(path)]

    cutter = EqualPowerFadeCut(fade_beats=16)
    pipeline = BeatBridgePipeline(*files, analysis, SimpleTempoAdjust(), cutter, target_sample_rate=rate)
    pipeline.cut(3000*32, 3090*48)
    assert pipeline.cue_alignment.tempo_factor == pytest.approx(1.03)
    assert pipeline.effective_target_cutpoint == 3000*48
    assert cutter.effective_transition_samples == 3000*16


def test_direct_batch_filters_a_stale_cue_before_top_k(tmp_path):
    from dataclasses import replace
    from src.analysis.models import AnalysisResult, BeatGridMetadata
    from src.batch_render import render_candidate_batch
    from src.candidates import CandidateGenerationConfig
    from src.pipeline import generate_transition_candidates

    rate = 8000
    paths = [tmp_path / f"{role}.wav" for role in ("a", "b")]
    for path in paths:
        sf.write(path, np.zeros(rate * 16, dtype=np.float32), rate)
    frames = tuple((i * 4000, i % 4 + 1, 4) for i in range(32))

    def analysis(_):
        return AnalysisResult(120., frames, BeatGridMetadata("detector", False, "v1", .9))

    generation = generate_transition_candidates(
        *paths, target_sample_rate=rate, analysis=analysis,
        config=CandidateGenerationConfig(transition_lengths_bars=(1,)),
    )
    good = generation.candidates[0]
    bad = replace(good, candidate_id="stale", source_cutpoint=replace(good.source_cutpoint, sample=1000))
    result = render_candidate_batch(replace(generation, candidates=(bad, good)), tmp_path / "batch",
                                    target_sample_rate=rate, analysis=analysis, top_k=1, renderers=("simple",))
    assert [v.candidate_id for v in result.rendered_variants] == [good.candidate_id]
    assert result.candidate_generation.rejections[-1].code == "cue_grid_regression_v3"
