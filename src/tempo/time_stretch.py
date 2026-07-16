import numpy as np
import librosa


class TimeStretch:
    def __init__(self):
        pass
    
    def adjust_tempo_by_factor(self, audio, sample_rate, tempo_factor, res_type="soxr_hq"):
        """Change tempo with time stretching while keeping pitch unchanged.

        Parameters
        ----------
        audio:
            Audio samples as a numpy array. Supports mono ``(samples,)`` and
            multi-channel ``(channels, samples)`` arrays.
        sample_rate:
            Kept for API compatibility with ``SimpleTempoAdjust``.
        tempo_factor:
            Tempo multiplier to apply. Values above 1.0 make the audio faster,
            values below 1.0 make it slower.
        res_type:
            Kept for API compatibility with ``SimpleTempoAdjust``.
        """
        if tempo_factor <= 0:
            raise ValueError("tempo_factor must be greater than 0")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than 0")

        audio = np.asarray(audio)
        return librosa.effects.time_stretch(audio, rate=float(tempo_factor))

    def adjust_tempo_to_bpm(self, audio, sample_rate, original_bpm, res_type="soxr_hq"):
        """Adjust audio from ``original_bpm`` to ``target_bpm``."""
        if original_bpm <= 0:
            raise ValueError("original_bpm must be greater than 0")
        if self.target_bpm <= 0:
            raise ValueError("target_bpm must be greater than 0")

        tempo_factor = float(self.target_bpm) / float(original_bpm)
        return self.adjust_tempo_by_factor(audio, sample_rate, tempo_factor, res_type=res_type)


# Alias for drop-in compatibility with the class name used by simple_tempo_adjust.py.
SimpleTempoAdjust = TimeStretch
