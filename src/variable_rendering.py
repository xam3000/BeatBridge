"""Additive exact-duration rendering for variable-length candidates."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from src.analysis.pre_analysis import PreAnalysis
from src.pipeline import (
    BeatBridgePipeline,
    DEFAULT_SAMPLE_RATE,
    RenderResult,
    _limit_to_preview,
    build_cutter,
)
from src.features.variable_contract import geometry_for_length
from src.tempo.time_stretch import TimeStretch


VARIABLE_RENDER_RESULT_FORMAT_VERSION = 6


def render_variable_transition(
    candidate,
    renderer="fade",
    *,
    target_sample_rate=DEFAULT_SAMPLE_RATE,
    analysis=None,
    analysis_location=None,
    tempo_adjuster=None,
    preview_seconds_before=5.0,
    preview_seconds_after=12.0,
):
    """Render one v2 candidate with an exact bridge duration.

    The legacy renderer remains responsible for v1 candidates. This path uses
    the candidate's beat window and rejects unequal source/target durations
    instead of shortening the bridge to the smaller side.
    """
    if int(getattr(candidate, "format_version", 1)) != 2:
        raise ValueError("render_variable_transition requires a variable candidate")
    geometry_for_length(
        candidate.transition_length_bars,
        transition_length_beats=candidate.transition_length_beats,
    )
    if analysis is None:
        cache_path = (
            Path("output") / "pre_analysis"
            if analysis_location is None
            else Path(analysis_location)
        )
        analysis = PreAnalysis(str(cache_path) + os.sep)
    if renderer == "simple":
        from src.pipeline import render_transition

        result = render_transition(
            candidate.source_track.path,
            candidate.target_track.path,
            candidate.source_cutpoint.sample,
            candidate.target_cutpoint.sample,
            renderer=renderer,
            fade_beats=candidate.transition_length_beats,
            target_sample_rate=target_sample_rate,
            analysis=analysis,
            analysis_location=analysis_location,
            source_bpm=candidate.source_bpm,
            target_bpm=candidate.target_bpm,
            preview_seconds_before=preview_seconds_before,
            preview_seconds_after=preview_seconds_after,
        )
        return RenderResult(
            audio=result.audio,
            sample_rate=result.sample_rate,
            renderer=result.renderer,
            tempo_backend=result.tempo_backend,
            transition_start_sample=result.transition_start_sample,
            transition_end_sample=result.transition_end_sample,
            format_version=VARIABLE_RENDER_RESULT_FORMAT_VERSION,
            source_grid=result.source_grid,
            target_grid=result.target_grid,
            transition_length_bars=candidate.transition_length_bars,
            transition_length_beats=candidate.transition_length_beats,
        )

    if renderer not in {"fade", "equal_power", "tempo_fade"}:
        raise ValueError(f"Unknown variable renderer: {renderer}")
    if int(candidate.transition_length_beats) <= 0:
        raise ValueError("Variable candidate transition_length_beats must be positive")

    target_sample_rate = int(target_sample_rate)
    if target_sample_rate <= 0:
        raise ValueError("target_sample_rate must be greater than 0")
    tempo_adjuster = tempo_adjuster or TimeStretch()
    cutter = build_cutter(renderer, fade_beats=int(candidate.transition_length_beats))
    pipeline = BeatBridgePipeline(
        candidate.source_track.path,
        candidate.target_track.path,
        analysis,
        tempo_adjuster,
        cutter,
        target_sample_rate=target_sample_rate,
        bpm1=candidate.source_bpm,
        bpm2=candidate.target_bpm,
    )
    source_audio, target_audio = pipeline.adjust_tempo()
    source_cut = int(
        round(
            int(candidate.source_cutpoint.sample)
            * target_sample_rate
            / DEFAULT_SAMPLE_RATE
        )
    )
    target_cut = int(
        round(
            int(candidate.target_cutpoint.sample)
            * target_sample_rate
            / DEFAULT_SAMPLE_RATE
            * pipeline.adjusted_sample_scale2
        )
    )
    source_cut, target_cut = cutter.resolve_cut_samples(
        source_audio,
        target_audio,
        source_cut,
        target_cut,
        pipeline.beat_frames1,
        pipeline.adjusted_beat_frames2,
    )
    transition_beats = int(candidate.transition_length_beats)
    source_end = cutter._find_beat_offset_sample(
        pipeline.beat_frames1,
        source_cut,
        transition_beats,
        source_audio.shape[-1],
    )
    target_start = cutter._find_beat_offset_sample(
        pipeline.adjusted_beat_frames2,
        target_cut,
        -transition_beats,
        target_audio.shape[-1],
    )
    source_length = int(source_end - source_cut)
    target_length = int(target_cut - target_start)
    if source_length <= 0 or target_length <= 0:
        raise ValueError("Variable candidate has no complete transition window")
    if source_length != target_length:
        raise ValueError(
            "Variable candidate transition windows have different sample lengths: "
            f"source={source_length}, target={target_length}"
        )

    fade_out, fade_in = cutter._build_envelopes(source_length)
    source_transition = source_audio[..., source_cut:source_end].astype(
        np.float32, copy=False
    )
    target_transition = target_audio[..., target_start:target_cut].astype(
        np.float32, copy=False
    )
    mixed_transition = (
        source_transition * fade_out.reshape(cutter._envelope_shape(source_transition))
        + target_transition * fade_in.reshape(cutter._envelope_shape(target_transition))
    )
    audio = np.concatenate(
        [source_audio[..., :source_cut], mixed_transition, target_audio[..., target_cut:]],
        axis=-1,
    ).astype(np.float32, copy=False)
    audio, preview_start = _limit_to_preview(
        audio,
        source_cut,
        target_sample_rate,
        preview_seconds_before,
        preview_seconds_after,
    )
    return RenderResult(
        audio=audio,
        sample_rate=target_sample_rate,
        renderer=renderer,
        tempo_backend=pipeline.tempo_backend,
        transition_start_sample=source_cut - preview_start,
        transition_end_sample=source_cut + source_length - preview_start,
        format_version=VARIABLE_RENDER_RESULT_FORMAT_VERSION,
        source_grid=pipeline.grid_metadata1,
        target_grid=pipeline.grid_metadata2,
        transition_length_bars=int(candidate.transition_length_bars),
        transition_length_beats=transition_beats,
    )
