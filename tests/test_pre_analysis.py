import hashlib
import json
import os

import numpy as np
import soundfile as sf

from src.analysis.pre_analysis import GRID_METADATA_FILENAME, PreAnalysis


def test_legacy_cache_is_marked_unknown_in_additive_sidecar(tmp_path):
    song = tmp_path / "legacy.wav"
    sf.write(song, np.zeros(8_000, dtype=np.float32), 8_000)
    cache_root = tmp_path / "analysis"
    cache_directory = cache_root / song.stem
    cache_directory.mkdir(parents=True)
    digest = hashlib.sha256(song.read_bytes()).hexdigest()
    beat_lines = "\n".join(
        f"{index * 1000},{index % 4 + 1},4" for index in range(8)
    )
    (cache_directory / "00_pre_analysis.txt").write_text(
        f"{digest}\n120.0\n{beat_lines}\n",
        encoding="utf-8",
    )

    result = PreAnalysis(str(cache_root) + os.sep)(song)

    assert result.grid_metadata.grid_source == "legacy_cache_unknown"
    assert result.grid_metadata.fallback_used is None
    sidecar = json.loads(
        (cache_directory / GRID_METADATA_FILENAME).read_text(encoding="utf-8")
    )
    assert sidecar["grid_source"] == "legacy_cache_unknown"
    assert sidecar["fallback_used"] is None
