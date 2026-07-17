from .fade_cut import FadeCut


class EqualPowerFadeCut(FadeCut):
    """Crossfade whose squared gains sum to one across the transition."""

    def __init__(
        self,
        align_bar=True,
        snap_to_down_beat=True,
        fade_beats=8,
        fade_beats_before=None,
        fade_beats_after=0,
    ):
        super().__init__(
            align_bar=align_bar,
            snap_to_down_beat=snap_to_down_beat,
            fade_beats=fade_beats,
            fade_beats_before=fade_beats_before,
            fade_beats_after=fade_beats_after,
            fade_curve="equal_power",
        )
