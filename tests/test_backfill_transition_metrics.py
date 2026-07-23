import json

import numpy as np
import soundfile as sf

from src.evaluation.backfill_transition_metrics import (
    _ReadOnlyBeatGridCache,
    score_existing_pair_batch,
)


def test_existing_pair_batch_is_scored_without_changing_its_manifest(tmp_path):
    sample_rate = 8_000
    source_path = tmp_path / "source.wav"
    target_path = tmp_path / "target.wav"
    sf.write(source_path, np.zeros(sample_rate * 10, dtype=np.float32), sample_rate)
    sf.write(target_path, np.zeros(sample_rate * 10, dtype=np.float32), sample_rate)

    analysis_location = tmp_path / "analysis"
    beats = "\n".join(
        f"{sample},{index % 4 + 1},4"
        for index, sample in enumerate(range(0, sample_rate * 10, sample_rate // 2))
    )
    for path, digest in ((source_path, "source-hash"), (target_path, "target-hash")):
        cache_directory = analysis_location / path.stem
        cache_directory.mkdir(parents=True)
        (cache_directory / "00_pre_analysis.txt").write_text(
            f"{digest}\n120.0\n{beats}\n",
            encoding="utf-8",
        )

    pair_directory = tmp_path / "pair"
    rendered_directory = pair_directory / "rendered"
    rendered_directory.mkdir(parents=True)
    region_samples = sample_rate * 2
    time = np.arange(region_samples) / sample_rate
    tone = np.sin(2 * np.pi * 440.0 * time)
    envelope = np.concatenate(
        [
            np.linspace(0.5, 0.05, region_samples // 2, endpoint=False),
            np.linspace(0.05, 0.5, region_samples // 2),
        ]
    )
    rendered = np.concatenate([0.5 * tone, envelope * tone, 0.5 * tone])
    rendered_path = rendered_directory / "variant.wav"
    sf.write(rendered_path, rendered, sample_rate)

    candidate = {
        "candidate_id": "candidate-test",
        "source_track": {"path": str(source_path), "sha256": "source-hash"},
        "target_track": {"path": str(target_path), "sha256": "target-hash"},
        "source_cutpoint": {"sample": 32_000, "beat_index": 8},
        "target_cutpoint": {"sample": 32_000, "beat_index": 8},
        "transition_length_beats": 4,
        "source_bpm": 120.0,
        "target_bpm": 120.0,
    }
    manifest = {
        "format_version": 1,
        "candidate_generation": {"candidates": [candidate]},
        "render_preview": {
            "seconds_before_source_cutpoint": 2.0,
            "seconds_after_source_cutpoint": 4.0,
        },
        "rendered_variants": [
            {
                "candidate_id": "candidate-test",
                "renderer": "equal_power",
                "output_file": "rendered/variant.wav",
                "sample_rate": sample_rate,
            }
        ],
    }
    manifest_path = pair_directory / "manifest.json"
    manifest_text = json.dumps(manifest, sort_keys=True)
    manifest_path.write_text(manifest_text, encoding="utf-8")

    payload = score_existing_pair_batch(
        pair_directory,
        analysis_cache=_ReadOnlyBeatGridCache(analysis_location),
    )

    assert payload["scored_variant_count"] == 1
    assert payload["failure_count"] == 0
    assert payload["variants"][0]["transition_start_sample"] == region_samples
    assert payload["variants"][0]["transition_end_sample"] == region_samples * 2
    assert 0.0 <= payload["variants"][0]["transition_score"] <= 1.0
    assert manifest_path.read_text(encoding="utf-8") == manifest_text
