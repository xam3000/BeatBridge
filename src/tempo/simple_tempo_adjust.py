import numpy as np
import librosa

class SimpleTempoAdjust:

    def __init__(self):
        pass

    def adjust_tempo_by_factor(self,audio, sample_rate, tempo_factor, res_type="soxr_hq"):
        """Change tempo by changing the effective sample rate and resampling back.

        A ``tempo_factor`` above 1.0 makes the audio faster/shorter.
        A ``tempo_factor`` below 1.0 makes the audio slower/longer.

        Parameters
        ----------
        audio:
            Audio samples as a numpy array. Supports mono ``(samples,)`` and
            multi-channel ``(channels, samples)`` arrays.
        sample_rate:
            Original sample rate of ``audio``.
        tempo_factor:
            Tempo multiplier to apply.
        res_type:
            Resampling mode forwarded to ``librosa.resample``.
        """
        if tempo_factor <= 0:
            raise ValueError("tempo_factor must be greater than 0")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than 0")

        audio = np.asarray(audio)
        effective_sample_rate = float(sample_rate) * float(tempo_factor)

        # Resample along the time axis so the output keeps the original sample rate.
        adjusted_audio = librosa.resample(
            audio,
            orig_sr=effective_sample_rate,
            target_sr=sample_rate,
            axis=-1,
            res_type=res_type,
        )
        return adjusted_audio


    def adjust_tempo_to_bpm(self, audio, sample_rate, original_bpm, target_bpm, res_type="soxr_hq"):
        """Adjust audio from ``original_bpm`` to ``target_bpm``."""
        if original_bpm <= 0:
            raise ValueError("original_bpm must be greater than 0")
        if target_bpm <= 0:
            raise ValueError("target_bpm must be greater than 0")

        tempo_factor = float(target_bpm) / float(original_bpm)
        return self.adjust_tempo_by_factor(audio, sample_rate, tempo_factor, res_type=res_type)
