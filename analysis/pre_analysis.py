from pathlib import Path
import hashlib
import logging
import numpy as np
import subprocess

import librosa

tmp_folder = Path("tmp/")
MAX_BEAT_MATCH_DISTANCE_SECONDS = 0.2
logger = logging.getLogger(__name__)


class PreAnalysis:
    def __init__(self,analysis_location):
        self.analysis_location = analysis_location
        self.missing_beats = {"librosa": [], "auftakt": []}

    def __call__(self,song_path):
        self.song_path = Path(song_path)
        self.previous_analysis = self.find_previous_analysis()
        if self.previous_analysis and self.load_previous_analysis():
            return self.bpm, self.beat_frames
        self.load_song()
        self.find_bpm()

        self.auftakt_analysis_comparison()

        self.save_previous_analysis()
        
        return self.bpm, self.beat_frames

    def find_previous_analysis(self):
        song_name = self.song_path.stem
        song_extension = self.song_path.suffix
        analysis_folder = Path(f"{self.analysis_location}{song_name}")

        if not analysis_folder.is_dir():
            return None

        matching_file = analysis_folder / "00_pre_analysis.txt"
        if matching_file.is_file():
            return matching_file

        return None

    def load_previous_analysis(self):
        # first line is the hash, second line is the BPM, and each following line stores one beat entry
        analysis_path = Path(self.previous_analysis)
        song_path = self.song_path

        if not analysis_path.is_file() or not song_path.is_file():
            return False

        try:
            analysis_lines = analysis_path.read_text().splitlines()
            stored_hash = analysis_lines[0]
            bpm_line = analysis_lines[1]
            current_hash = hashlib.sha256(song_path.read_bytes()).hexdigest()
            if stored_hash != current_hash:
                return False

            self.bpm = float(bpm_line)
            self.beat_frames = [self._parse_saved_beat_line(line) for line in analysis_lines[2:] if line.strip()]
        except (IndexError, ValueError):
            return False

        # output False for devolempent purposes to force re-analysis, can be removed later
        return False

    def save_previous_analysis(self):
        song_name = self.song_path.stem
        analysis_folder = Path(f"{self.analysis_location}{song_name}")
        analysis_folder.mkdir(parents=True, exist_ok=True)

        analysis_path = analysis_folder / "00_pre_analysis.txt"
        song_hash = hashlib.sha256(self.song_path.read_bytes()).hexdigest()
        beat_frame_lines = "\n".join(self._format_saved_beat_line(frame) for frame in self.beat_frames)
        analysis_contents = f"{song_hash}\n{self.bpm}\n{beat_frame_lines}\n"
        analysis_path.write_text(analysis_contents)
        self.previous_analysis = analysis_path
        self.save_missing_beats()

    def save_missing_beats(self):
        song_name = self.song_path.stem
        analysis_folder = Path(f"{self.analysis_location}{song_name}")
        analysis_folder.mkdir(parents=True, exist_ok=True)

        missing_beats_path = analysis_folder / "01_missing_beats.txt"
        missing_lines = ["librosa_without_auftakt"]
        missing_lines.extend(
            f"{beat['sample']},{beat['time_seconds']:.6f},{beat['distance_seconds']:.6f}"
            for beat in self.missing_beats["librosa"]
        )
        missing_lines.append("")
        missing_lines.append("auftakt_without_librosa")
        missing_lines.extend(
            f"{beat['time_seconds']:.6f},{beat['count_in_bar']},{beat['beats_in_bar']},{beat['distance_seconds']:.6f}"
            for beat in self.missing_beats["auftakt"]
        )
        missing_beats_path.write_text("\n".join(missing_lines) + "\n")

    def load_song(self):
        self.song, self.sr = librosa.load(self.song_path, sr=None, mono=True)

    def find_bpm(self):
        onset_env = librosa.onset.onset_strength(y=self.song, sr=self.sr,
                                         aggregate=np.median)
        self.bpm, self.beat_frames = librosa.beat.beat_track(y=self.song, sr=self.sr, units="samples",onset_envelope=onset_env)
        self.bpm = self.bpm[0] if isinstance(self.bpm, (list, np.ndarray)) else self.bpm

    def auftakt_analysis_comparison(self):
        # run auftakt
        if self.song_path.suffix.lower() != ".wav":
            temp_wav_path = tmp_folder / f"{self.song_path.stem}.wav"
            subprocess.run(["ffmpeg", "-i", str(self.song_path), str(temp_wav_path)], check=True)
            song_to_analyze = temp_wav_path
        else:
            song_to_analyze = self.song_path

        command = ["aufTAKTCl.exe", "-i", str(song_to_analyze), "-r", str(tmp_folder)+"/aufTAKT_output"]

        print("Running command:")
        print(" ".join(command))
        
        subprocess.run(command, check=True)

        auftakt_output_path = tmp_folder / "aufTAKT_output"
        auftakt_lines = auftakt_output_path.read_text().splitlines()[1:]
        auftakt_beats = []
        for line in auftakt_lines:
            if not line.strip():
                continue

            time_seconds, count_in_bar, beats_in_bar = [part.strip() for part in line.split(",")]
            auftakt_beats.append((float(time_seconds), int(count_in_bar), int(beats_in_bar)))

        if auftakt_beats:
            auftakt_times = np.array([beat[0] for beat in auftakt_beats], dtype=float)
            librosa_times = librosa.samples_to_time(np.asarray(self.beat_frames), sr=self.sr)
            combined_beats = []
            matched_auftakt_indices = set()
            self.missing_beats = {"librosa": [], "auftakt": []}

            for sample, beat_time in zip(self.beat_frames, librosa_times):
                closest_index, distance = self._find_closest_beat_index(auftakt_times, beat_time)
                if distance > MAX_BEAT_MATCH_DISTANCE_SECONDS:
                    logger.warning(
                        "No matching aufTAKT beat for librosa beat at %.3fs (distance %.3fs)",
                        beat_time,
                        distance,
                    )
                    self.missing_beats["librosa"].append(
                        {
                            "sample": int(sample),
                            "time_seconds": float(beat_time),
                            "distance_seconds": float(distance),
                        }
                    )
                    combined_beats.append(int(sample))
                    continue

                matched_auftakt_indices.add(closest_index)
                _, count_in_bar, beats_in_bar = auftakt_beats[closest_index]
                combined_beats.append((int(sample), count_in_bar, beats_in_bar))

            for idx, auftakt_time in enumerate(auftakt_times):
                closest_index, distance = self._find_closest_beat_index(librosa_times, auftakt_time)
                if distance > MAX_BEAT_MATCH_DISTANCE_SECONDS or idx not in matched_auftakt_indices:
                    logger.warning(
                        "No matching librosa beat for aufTAKT beat at %.3fs (distance %.3fs, bar beat %s/%s)",
                        auftakt_time,
                        distance,
                        auftakt_beats[idx][1],
                        auftakt_beats[idx][2],
                    )
                    self.missing_beats["auftakt"].append(
                        {
                            "time_seconds": float(auftakt_time),
                            "count_in_bar": int(auftakt_beats[idx][1]),
                            "beats_in_bar": int(auftakt_beats[idx][2]),
                            "distance_seconds": float(distance),
                        }
                    )

            self.beat_frames = combined_beats

        # clear out tmp folder
        for file in tmp_folder.iterdir():
            if file.is_file():
                file.unlink()

    @staticmethod
    def _parse_saved_beat_line(line):
        parts = [part.strip() for part in line.split(",")]
        if len(parts) == 1:
            return int(parts[0])
        if len(parts) == 3:
            sample, count_in_bar, beats_in_bar = parts
            return int(sample), int(count_in_bar), int(beats_in_bar)
        raise ValueError(f"Invalid beat line: {line}")

    @staticmethod
    def _format_saved_beat_line(frame):
        if isinstance(frame, tuple):
            sample, count_in_bar, beats_in_bar = frame
            return f"{int(sample)},{int(count_in_bar)},{int(beats_in_bar)}"
        return str(int(frame))

    @staticmethod
    def _find_closest_beat_index(beat_times, target_time):
        insert_index = np.searchsorted(beat_times, target_time)
        candidate_indices = []
        if insert_index > 0:
            candidate_indices.append(insert_index - 1)
        if insert_index < len(beat_times):
            candidate_indices.append(insert_index)

        closest_index = min(
            candidate_indices,
            key=lambda idx: abs(float(beat_times[idx]) - target_time),
        )
        distance = abs(float(beat_times[closest_index]) - target_time)
        return closest_index, distance
