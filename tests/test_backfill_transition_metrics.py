import json
import hashlib

import numpy as np
import soundfile as sf

from src.analysis.pre_analysis import (
    ANALYSIS_CACHE_FILENAME,
    ANALYSIS_CACHE_FORMAT_VERSION,
    ANALYSIS_CACHE_NAMESPACE,
)
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


def test_read_only_cache_loads_exact_current_analysis_id(tmp_path):
    sample_rate = 8_000
    track = tmp_path / "track.wav"
    sf.write(track, np.zeros(sample_rate, dtype=np.float32), sample_rate)
    digest = hashlib.sha256(track.read_bytes()).hexdigest()
    analysis_id = "analysis-test"
    beats = [[index * 1000, index % 4 + 1, 4] for index in range(8)]
    grid_hash = hashlib.sha256(
        json.dumps(beats, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    cache_path = (
        tmp_path
        / "analysis"
        / ANALYSIS_CACHE_NAMESPACE
        / digest
        / analysis_id
        / ANALYSIS_CACHE_FILENAME
    )
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text(
        json.dumps(
            {
                "format_version": ANALYSIS_CACHE_FORMAT_VERSION,
                "analysis_id": analysis_id,
                "source_audio": {"sha256": digest},
                "result": {
                    "beat_frames": beats,
                    "grid_metadata": {
                        "analysis_id": analysis_id,
                        "beat_grid_sha256": grid_hash,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    legacy_path = tmp_path / "analysis" / track.stem / "00_pre_analysis.txt"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        f"{digest}\n120.0\n999,1,4\n",
        encoding="utf-8",
    )

    loaded = _ReadOnlyBeatGridCache(tmp_path / "analysis").normalised_beats(
        track,
        digest,
        sample_rate,
        expected_grid_metadata={
            "analysis_id": analysis_id,
            "beat_grid_sha256": grid_hash,
        },
    )

    assert loaded == tuple(tuple(beat) for beat in beats)
