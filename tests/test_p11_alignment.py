import numpy as np
import pytest

from src.evaluation.p11_alignment import LocalGridFailure, align_target, check_timing


def test_real_warp_moves_clicks_without_transposing_sustained_tone():
    rate = 44100
    a = np.arange(17)*16000
    b = 13000 + np.r_[0, np.cumsum([16200, 15500]*8)]
    n = np.arange(b[-1] + rate)
    tone = (.05*np.sin(2*np.pi*440*n/rate)).astype(np.float32)
    stereo = np.stack([tone, tone.copy()])
    stereo[1, b] = 1
    corrected, receipt = align_target(stereo, a, b, rate)
    assert receipt["output_beats"] == a.tolist()
    np.testing.assert_array_equal(np.flatnonzero(corrected[1] > .9), a[:-1])
    excerpt = corrected[0, 2000:14000]
    peak = np.argmax(abs(np.fft.rfft(excerpt * np.hanning(len(excerpt))))) * rate / len(excerpt)
    assert abs(peak - 440) < 5
    assert corrected.shape == (2, a[-1])


def test_gate_limits_are_inclusive_and_both_failures_are_rejected():
    a = np.arange(17)*10000
    check_timing(a, np.arange(17)*10100, a[-1]-882, 44100)
    with pytest.raises(LocalGridFailure):
        check_timing(a, np.arange(17)*10101, a[-1], 44100)
    with pytest.raises(LocalGridFailure):
        check_timing(a, a, a[-1]-883, 44100)
