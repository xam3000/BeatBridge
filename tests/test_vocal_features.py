import json

import numpy as np
import soundfile as sf
import torch

from src.features import feature_index
from src.features.extract_track import extract_or_load_track_features
from src.features.vocal import VocalStemArtifact, extract_or_load_vocal_stem


class _Analysis:
    def __init__(self, sample_rate=8_000, bpm=120.0, beat_count=25):
        self.sample_rate = sample_rate
        self.bpm = bpm
        self.beat_count = beat_count

    def __call__(self, _):
        beat_samples = int(round(self.sample_rate * 60.0 / self.bpm))
        return self.bpm, [
            (index * beat_samples, index % 4 + 1, 4)
            for index in range(self.beat_count)
        ]


def _write_test_song(path, *, sample_rate=8_000):
    time = np.arange(13 * sample_rate, dtype=np.float32) / sample_rate
    audio = 0.2 * np.sin(2 * np.pi * 220.0 * time)
    sf.write(path, audio, sample_rate, subtype="FLOAT")
    return audio


def test_demucs_vocal_stem_is_cached_with_model_provenance(tmp_path):
    song = tmp_path / "song.wav"
    audio = _write_test_song(song)
    calls = []

    class _FakeSeparator:
        samplerate = 8_000

        def __init__(self, **kwargs):
            calls.append(kwargs)

        def separate_audio_file(self, _):
            stereo = torch.from_numpy(np.stack((audio, audio)))
            stems = {
                "vocals": 0.25 * stereo,
                "other": 0.75 * stereo,
            }
            return stereo, stems

    first = extract_or_load_vocal_stem(
        song,
        cache_root=tmp_path / "cache",
        model_name="test-model",
        device="cpu",
        separator_factory=_FakeSeparator,
    )
    second = extract_or_load_vocal_stem(
        song,
        cache_root=tmp_path / "cache",
        model_name="test-model",
        device="cpu",
        separator_factory=lambda **_: (_ for _ in ()).throw(
            AssertionError("A stem cache hit must not load a model")
        ),
    )

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert len(calls) == 1
    assert calls[0]["device"] == "cpu"
    assert np.array_equal(first.audio, second.audio)
    assert first.manifest["paper"]["citation_key"] == "rouard2023hybrid"
    assert first.manifest["artifact_sha256"] == second.manifest["artifact_sha256"]


def test_track_features_populate_vocal_channels_from_cached_stem(tmp_path):
    song = tmp_path / "song.wav"
    audio = _write_test_song(song)
    cache_directory = tmp_path / "fake-vocal"
    cache_directory.mkdir()

    def _fake_vocal_loader(*_, **__):
        vocal = np.zeros_like(audio)
        vocal[audio.size // 3 : 2 * audio.size // 3] = (
            0.8 * audio[audio.size // 3 : 2 * audio.size // 3]
        )
        return VocalStemArtifact(
            cache_directory=cache_directory,
            manifest={
                "artifact_sha256": "fake-stem-sha256",
                "model_name": "htdemucs",
                "demucs_version": "4.1.0",
                "weights": {"revision": "test"},
                "paper": {"citation_key": "rouard2023hybrid"},
            },
            audio=vocal,
            sample_rate=8_000,
            cache_hit=True,
        )

    artifact = extract_or_load_track_features(
        song,
        cache_root=tmp_path / "cache",
        analysis=_Analysis(),
        sample_rate=8_000,
        vocal_backend="demucs",
        vocal_stem_loader=_fake_vocal_loader,
    )

    valid = artifact.base_features[:, feature_index("vocal_valid")]
    activity = artifact.base_features[:, feature_index("vocal_activity")]
    progress = artifact.base_features[:, feature_index("vocal_phrase_progress")]
    assert np.all(valid == 1.0)
    assert np.max(activity) > np.min(activity)
    assert np.max(progress) > 0.0
    manifest = json.loads(
        (artifact.cache_directory / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["extractor_components"]["vocal"] == "demucs_energy_activity_v1"
    assert manifest["vocal_artifact"]["paper"]["citation_key"] == (
        "rouard2023hybrid"
    )
