from pathlib import Path
import subprocess
import tempfile

import numpy as np
import soundfile as sf


class TimeStretchBackendError(RuntimeError):
    """A Rubber Band backend could not produce valid stretched audio."""


class TimeStretch:
    """Pitch-preserving tempo adjustment backed by Rubber Band.

    FFmpeg's ``rubberband`` filter is preferred because FFmpeg is already part
    of the BeatBridge toolchain. The standalone ``rubberband`` command is used
    as a fallback. Intermediate WAV files use 32-bit floating-point samples so
    the backend boundary does not add a PCM16 quantisation step.
    """

    def __init__(
        self,
        *,
        ffmpeg_executable="ffmpeg",
        rubberband_executable="rubberband",
    ):
        self.ffmpeg_executable = str(ffmpeg_executable)
        self.rubberband_executable = str(rubberband_executable)
        self.last_backend = None

    def adjust_tempo_by_factor(
        self,
        audio,
        sample_rate,
        tempo_factor,
        res_type="soxr_hq",
    ):
        """Change tempo while keeping pitch unchanged.

        Parameters
        ----------
        audio:
            Audio samples as a NumPy array. Supports mono ``(samples,)`` and
            channel-first multi-channel ``(channels, samples)`` arrays.
        sample_rate:
            Sample rate used for the temporary and returned audio.
        tempo_factor:
            Tempo multiplier. Values above 1.0 make the audio faster and
            shorter; values below 1.0 make it slower and longer.
        res_type:
            Kept for API compatibility with ``SimpleTempoAdjust``. Rubber Band
            controls the time-stretch resynthesis and does not use this value.
        """
        tempo_factor = float(tempo_factor)
        sample_rate = int(sample_rate)
        if not np.isfinite(tempo_factor) or tempo_factor <= 0:
            raise ValueError("tempo_factor must be a finite value greater than 0")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be greater than 0")

        audio = np.asarray(audio)
        if audio.ndim not in {1, 2}:
            raise ValueError("audio must have shape (samples,) or (channels, samples)")
        if audio.shape[-1] == 0:
            raise ValueError("audio must contain at least one sample")
        if not np.isfinite(audio).all():
            raise ValueError("audio must contain only finite samples")

        expected_samples = int(round(audio.shape[-1] / tempo_factor))
        if abs(tempo_factor - 1.0) < 1e-12:
            self.last_backend = "not_needed"
            return audio.astype(np.float32, copy=True)

        channels = 1 if audio.ndim == 1 else int(audio.shape[0])
        failures = []
        with tempfile.TemporaryDirectory(prefix="beatbridge_timestretch_") as temp_dir:
            temp_dir = Path(temp_dir)
            input_path = temp_dir / "input.wav"
            ffmpeg_output_path = temp_dir / "ffmpeg_output.wav"
            cli_output_path = temp_dir / "rubberband_output.wav"
            sf.write(
                str(input_path),
                audio.T,
                sample_rate,
                format="WAV",
                subtype="FLOAT",
            )

            try:
                self._run_ffmpeg(
                    input_path,
                    ffmpeg_output_path,
                    sample_rate=sample_rate,
                    channels=channels,
                    tempo_factor=tempo_factor,
                )
                adjusted = self._read_backend_output(
                    ffmpeg_output_path,
                    sample_rate=sample_rate,
                    channels=channels,
                    mono=audio.ndim == 1,
                )
                self.last_backend = "ffmpeg_librubberband"
                return self._match_length(adjusted, expected_samples)
            except TimeStretchBackendError as error:
                failures.append(f"FFmpeg/librubberband: {error}")

            try:
                self._run_rubberband_cli(
                    input_path,
                    cli_output_path,
                    tempo_factor=tempo_factor,
                )
                adjusted = self._read_backend_output(
                    cli_output_path,
                    sample_rate=sample_rate,
                    channels=channels,
                    mono=audio.ndim == 1,
                )
                self.last_backend = "rubberband_cli_r3"
                return self._match_length(adjusted, expected_samples)
            except TimeStretchBackendError as error:
                failures.append(f"Rubber Band CLI: {error}")

        self.last_backend = None
        details = " | ".join(failures)
        raise TimeStretchBackendError(
            "[Time stretch] No Rubber Band backend succeeded. "
            "Install FFmpeg with --enable-librubberband or the standalone "
            f"rubberband CLI. {details}"
        )

    def adjust_tempo_to_bpm(
        self,
        audio,
        sample_rate,
        original_bpm,
        target_bpm,
        res_type="soxr_hq",
    ):
        """Adjust audio from ``original_bpm`` to ``target_bpm``."""
        original_bpm = float(original_bpm)
        target_bpm = float(target_bpm)
        if not np.isfinite(original_bpm) or original_bpm <= 0:
            raise ValueError("original_bpm must be a finite value greater than 0")
        if not np.isfinite(target_bpm) or target_bpm <= 0:
            raise ValueError("target_bpm must be a finite value greater than 0")

        tempo_factor = target_bpm / original_bpm
        return self.adjust_tempo_by_factor(
            audio,
            sample_rate,
            tempo_factor,
            res_type=res_type,
        )

    def _run_ffmpeg(
        self,
        input_path,
        output_path,
        *,
        sample_rate,
        channels,
        tempo_factor,
    ):
        filter_spec = (
            f"rubberband=tempo={tempo_factor:.17g}:pitch=1:channels=together"
        )
        command = [
            self.ffmpeg_executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-af",
            filter_spec,
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-c:a",
            "pcm_f32le",
            str(output_path),
        ]
        self._run_command(command, backend_name="FFmpeg/librubberband")

    def _run_rubberband_cli(
        self,
        input_path,
        output_path,
        *,
        tempo_factor,
    ):
        time_ratio = 1.0 / float(tempo_factor)
        command = [
            self.rubberband_executable,
            "-3",
            "-t",
            f"{time_ratio:.17g}",
            str(input_path),
            str(output_path),
        ]
        self._run_command(command, backend_name="Rubber Band CLI")

    @staticmethod
    def _run_command(command, *, backend_name):
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as error:
            raise TimeStretchBackendError(
                f"executable not found: {command[0]}"
            ) from error
        except OSError as error:
            raise TimeStretchBackendError(
                f"could not start {command[0]}: {error}"
            ) from error

        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "unknown error").strip()
            raise TimeStretchBackendError(
                f"{backend_name} exited with code {completed.returncode}: {message}"
            )

    @staticmethod
    def _read_backend_output(path, *, sample_rate, channels, mono):
        path = Path(path)
        if not path.is_file():
            raise TimeStretchBackendError("backend produced no output WAV")
        try:
            info = sf.info(str(path))
            output, output_sample_rate = sf.read(
                str(path),
                dtype="float32",
                always_2d=True,
            )
        except (OSError, RuntimeError) as error:
            raise TimeStretchBackendError(
                f"backend output could not be read: {error}"
            ) from error

        if int(output_sample_rate) != int(sample_rate):
            raise TimeStretchBackendError(
                f"backend changed sample rate from {sample_rate} to {output_sample_rate}"
            )
        if int(info.channels) != int(channels):
            raise TimeStretchBackendError(
                f"backend changed channel count from {channels} to {info.channels}"
            )
        if not np.isfinite(output).all():
            raise TimeStretchBackendError("backend output contains non-finite samples")

        channel_first = output.T.astype(np.float32, copy=False)
        return channel_first[0] if mono else channel_first

    @staticmethod
    def _match_length(audio, expected_samples):
        current_samples = int(audio.shape[-1])
        if current_samples == expected_samples:
            return audio.astype(np.float32, copy=False)
        if current_samples > expected_samples:
            return audio[..., :expected_samples].astype(np.float32, copy=False)

        padding = [(0, 0)] * audio.ndim
        padding[-1] = (0, expected_samples - current_samples)
        return np.pad(audio, padding, mode="constant").astype(np.float32, copy=False)
