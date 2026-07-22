from pathlib import Path

import numpy as np
import soundfile as sf

from src.ranking.song_compatibility import rank_song_targets


class StubAnalysis:
    def __init__(self, bpms):
        self.bpms = {str(Path(path)): bpm for path, bpm in bpms.items()}

    def __call__(self, song_path):
        return self.bpms[str(Path(song_path))], []


def test_song_compatibility_prefers_a_harmonically_and_temporally_closer_target(tmp_path):
    sample_rate = 44_100
    time = np.arange(sample_rate * 3, dtype=np.float32) / sample_rate
    source = tmp_path / "source.wav"
    compatible = tmp_path / "compatible.wav"
    incompatible = tmp_path / "incompatible.wav"
    sf.write(source, 0.2 * np.sin(2 * np.pi * 440.0 * time), sample_rate)
    sf.write(compatible, 0.2 * np.sin(2 * np.pi * 440.0 * time), sample_rate)
    sf.write(incompatible, 0.05 * np.sin(2 * np.pi * 659.25 * time), sample_rate)

    result = rank_song_targets(
        source,
        (incompatible, compatible),
        analysis=StubAnalysis({source: 120.0, compatible: 120.0, incompatible: 100.0}),
    )

    assert not result.failures
    assert [Path(score.target_path).name for score in result.scores] == [
        "compatible.wav",
        "incompatible.wav",
    ]
    assert result.scores[0].component_scores["tempo"] > result.scores[1].component_scores["tempo"]
    assert result.scores[0].component_scores["harmonic"] > result.scores[1].component_scores["harmonic"]
