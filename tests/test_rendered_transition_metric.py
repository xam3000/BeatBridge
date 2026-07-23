import math

import numpy as np

from src.ranking import RenderedTransitionInput, rank_rendered_transitions


def _rendered_input(candidate_id, bridge_envelope):
    sample_rate = 8_000
    seconds_per_region = 2
    region_samples = sample_rate * seconds_per_region
    time = np.arange(region_samples, dtype=np.float64) / sample_rate
    tone = np.sin(2.0 * np.pi * 440.0 * time)
    pre = 0.5 * tone
    transition = bridge_envelope * tone
    post = 0.5 * tone
    return RenderedTransitionInput(
        candidate_id=candidate_id,
        renderer="equal_power",
        audio=np.concatenate([pre, transition, post]).astype(np.float32),
        sample_rate=sample_rate,
        transition_start_sample=region_samples,
        transition_end_sample=region_samples * 2,
        transition_length_beats=4,
        bpm=120.0,
    )


def test_rendered_transition_metric_prefers_a_low_energy_smooth_bridge():
    samples = 16_000
    half = samples // 2
    smooth_bridge = np.concatenate(
        [
            np.linspace(0.5, 0.02, half, endpoint=False),
            np.linspace(0.02, 0.5, samples - half),
        ]
    )
    flat_bridge = np.full(samples, 0.5)

    result = rank_rendered_transitions(
        (
            _rendered_input("flat", flat_bridge),
            _rendered_input("shaped", smooth_bridge),
        )
    )

    assert not result.failures
    assert result.metric == "rendered_transition_baseline_v1"
    assert [score.candidate_id for score in result.scores] == ["shaped", "flat"]
    assert result.scores[0].component_scores["energy_shape"] > result.scores[1].component_scores[
        "energy_shape"
    ]
    assert all(math.isfinite(score.total_score) for score in result.scores)
    assert all(0.0 <= score.total_score <= 1.0 for score in result.scores)


def test_rendered_transition_metric_records_one_bad_variant_without_blocking_others():
    samples = 16_000
    valid = _rendered_input("valid", np.full(samples, 0.2))
    invalid = RenderedTransitionInput(
        candidate_id="invalid",
        renderer="fade",
        audio=np.zeros(100, dtype=np.float32),
        sample_rate=8_000,
        transition_start_sample=100,
        transition_end_sample=100,
        transition_length_beats=4,
        bpm=120.0,
    )

    result = rank_rendered_transitions((invalid, valid))

    assert [score.candidate_id for score in result.scores] == ["valid"]
    assert len(result.failures) == 1
    assert result.failures[0].candidate_id == "invalid"
    assert result.failures[0].error_type == "ValueError"
