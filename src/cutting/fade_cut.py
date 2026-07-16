import numpy as np

from .simple_cut import SimpleCut


class FadeCut(SimpleCut):
    def __init__(
        self,
        align_bar=True,
        snap_to_down_beat=True,
        fade_beats=8,
        fade_beats_before=None,
        fade_beats_after=0,
    ):
        super().__init__(align_bar=align_bar, snap_to_down_beat=snap_to_down_beat)
        self.fade_beats_before = int(fade_beats if fade_beats_before is None else fade_beats_before)
        self.fade_beats_after = int(fade_beats_after)

        if self.fade_beats_before < 0 or self.fade_beats_after < 0:
            raise ValueError("fade beat counts must be greater than or equal to 0")
        if self.fade_beats_before == 0 and self.fade_beats_after == 0:
            raise ValueError("FadeCut needs at least one beat of transition")

    def cut(self, song1, song2, song1_sample, song2_sample, beat_frames1, beat_frames2):
        audio1 = self._get_audio(song1)
        audio2 = self._get_audio(song2)

        cut_sample1 = self._clamp_sample(song1_sample, audio1)
        cut_sample2 = self._clamp_sample(song2_sample, audio2)

        if beat_frames1 is None or beat_frames2 is None:
            raise ValueError("beat_frames are required for FadeCut")

        cut_sample1, cut_sample2 = self._resolve_cut_samples(
            cut_sample1,
            cut_sample2,
            beat_frames1,
            beat_frames2,
        )

        transition_start1, transition_end1 = self._find_transition_bounds(
            beat_frames1,
            cut_sample1,
            audio1.shape[-1],
        )
        transition_start2, transition_end2 = self._find_transition_bounds(
            beat_frames2,
            cut_sample2,
            audio2.shape[-1],
        )

        before_length = min(cut_sample1 - transition_start1, cut_sample2 - transition_start2)
        after_length = min(transition_end1 - cut_sample1, transition_end2 - cut_sample2)

        if before_length < 0 or after_length < 0:
            raise ValueError("Invalid transition bounds for FadeCut")

        transition_start1 = cut_sample1 - before_length
        transition_start2 = cut_sample2 - before_length
        transition_end1 = cut_sample1 + after_length
        transition_end2 = cut_sample2 + after_length

        prefix = audio1[..., :transition_start1]
        transition_segment1 = audio1[..., transition_start1:transition_end1].astype(np.float32, copy=False)
        transition_segment2 = audio2[..., transition_start2:transition_end2].astype(np.float32, copy=False)
        suffix = audio2[..., transition_end2:]

        transition_length = transition_segment1.shape[-1]
        if transition_length == 0:
            raise ValueError("Transition length must be greater than 0")

        fade_out = np.linspace(1.0, 0.0, transition_length, endpoint=True, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, transition_length, endpoint=True, dtype=np.float32)

        mixed_transition = (
            transition_segment1 * fade_out.reshape(self._envelope_shape(transition_segment1))
            + transition_segment2 * fade_in.reshape(self._envelope_shape(transition_segment2))
        )

        return np.concatenate([prefix, mixed_transition, suffix], axis=-1)

    def _resolve_cut_samples(self, cut_sample1, cut_sample2, beat_frames1, beat_frames2):
        if self.snap_to_down_beat or self.align_bar:
            beat1 = self._find_nearest_beat(
                beat_frames1,
                cut_sample1,
                downbeat_only=self.snap_to_down_beat,
            )
            cut_sample1 = beat1["sample"]

            if self.align_bar and beat1["count_in_bar"] is not None:
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
            return cut_sample1, cut_sample2

        beat1 = self._find_nearest_beat(beat_frames1, cut_sample1, downbeat_only=False)
        beat2 = self._find_nearest_beat(beat_frames2, cut_sample2, downbeat_only=False)
        return beat1["sample"], beat2["sample"]

    def _find_transition_bounds(self, beat_frames, cut_sample, max_sample):
        parsed_beats = [self._parse_beat_frame(frame) for frame in beat_frames]
        beat_index = min(
            range(len(parsed_beats)),
            key=lambda idx: abs(parsed_beats[idx]["sample"] - int(cut_sample)),
        )

        start_index = max(0, beat_index - self.fade_beats_before)
        end_index = min(len(parsed_beats) - 1, beat_index + self.fade_beats_after)

        transition_start = parsed_beats[start_index]["sample"]
        if self.fade_beats_after > 0:
            transition_end = parsed_beats[end_index]["sample"]
        else:
            transition_end = cut_sample

        transition_end = min(int(max_sample), int(transition_end))
        transition_start = max(0, int(transition_start))
        return transition_start, transition_end

    @staticmethod
    def _envelope_shape(audio):
        if audio.ndim == 1:
            return (audio.shape[-1],)
        return (1, audio.shape[-1])
