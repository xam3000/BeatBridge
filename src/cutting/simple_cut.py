import numpy as np


class SimpleCut:
    def __init__(self, align_bar=True, snap_to_down_beat=True):
        self.align_bar = align_bar
        self.snap_to_down_beat = snap_to_down_beat

    def cut(self, song1, song2, song1_sample, song2_sample, beat_frames1, beat_frames2):
        audio1 = self._get_audio(song1)
        audio2 = self._get_audio(song2)

        cut_sample1 = self._clamp_sample(song1_sample, audio1)
        cut_sample2 = self._clamp_sample(song2_sample, audio2)

        beat_frames1 = beat_frames1
        beat_frames2 = beat_frames2
        if self.snap_to_down_beat or self.align_bar:
            if beat_frames1 is None or beat_frames2 is None:
                raise ValueError(
                    "beat_frames are required when snap_to_down_beat or align_bar is enabled"
                )

        beat1 = None
        if beat_frames1 is not None and (self.snap_to_down_beat or self.align_bar):
            beat1 = self._find_nearest_beat(
                beat_frames1,
                cut_sample1,
                downbeat_only=self.snap_to_down_beat,
            )
            if self.align_bar and beat1["count_in_bar"] is None:
                raise ValueError(
                    "Bar alignment requires beat frames with count_in_bar metadata"
                )
            cut_sample1 = beat1["sample"]

        if beat_frames2 is not None and (self.snap_to_down_beat or self.align_bar):
            if self.align_bar and beat1 is not None and beat1["count_in_bar"] is not None:
                beat2 = self._find_nearest_beat(
                    beat_frames2,
                    cut_sample2,
                    downbeat_only=self.snap_to_down_beat,
                    count_in_bar=beat1["count_in_bar"],
                    beats_in_bar=beat1["beats_in_bar"],
                )
            else:
                beat2 = self._find_nearest_beat(
                    beat_frames2,
                    cut_sample2,
                    downbeat_only=self.snap_to_down_beat,
                )
            cut_sample2 = beat2["sample"]

        return np.concatenate(
            [audio1[..., :cut_sample1], audio2[..., cut_sample2:]],
            axis=-1,
        )

    @staticmethod
    def _get_audio(song):
        if isinstance(song, np.ndarray):
            return song
        if isinstance(song, dict):
            if "audio" in song:
                return song["audio"]
            if "song" in song:
                return song["song"]
        for attr in ("audio", "song", "samples"):
            if hasattr(song, attr):
                return getattr(song, attr)
        raise ValueError("Could not extract audio data from song")

    @staticmethod
    def _get_beat_frames(song):
        if isinstance(song, dict):
            return song.get("beat_frames")
        return getattr(song, "beat_frames", None)

    @staticmethod
    def _clamp_sample(sample, audio):
        sample = int(sample)
        max_sample = audio.shape[-1]
        return max(0, min(sample, max_sample))

    @staticmethod
    def _parse_beat_frame(frame):
        if isinstance(frame, tuple):
            sample = int(frame[0])
            count_in_bar = int(frame[1]) if len(frame) > 1 else None
            beats_in_bar = int(frame[2]) if len(frame) > 2 else None
            return {
                "sample": sample,
                "count_in_bar": count_in_bar,
                "beats_in_bar": beats_in_bar,
                "is_downbeat": count_in_bar == 1 if count_in_bar is not None else False,
            }

        sample = int(frame)
        return {
            "sample": sample,
            "count_in_bar": None,
            "beats_in_bar": None,
            "is_downbeat": False,
        }

    def _find_nearest_beat(
        self,
        beat_frames,
        target_sample,
        downbeat_only=False,
        count_in_bar=None,
        beats_in_bar=None,
    ):
        parsed_beats = [self._parse_beat_frame(frame) for frame in beat_frames]

        candidates = parsed_beats
        if downbeat_only:
            downbeats = [beat for beat in candidates if beat["is_downbeat"]]
            if not downbeats:
                raise ValueError(
                    "Downbeat snapping requires beat frames with count_in_bar metadata"
                )
            candidates = downbeats

        if count_in_bar is not None:
            aligned_beats = [
                beat
                for beat in candidates
                if beat["count_in_bar"] == count_in_bar
                and (
                    beats_in_bar is None
                    or beat["beats_in_bar"] is None
                    or beat["beats_in_bar"] == beats_in_bar
                )
            ]
            if not aligned_beats:
                raise ValueError("No beat position matches the requested bar alignment")
            candidates = aligned_beats

        if not candidates:
            raise ValueError("No valid beat positions available for the requested cut")

        return min(candidates, key=lambda beat: abs(beat["sample"] - int(target_sample)))
