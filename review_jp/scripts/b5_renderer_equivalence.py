"""B5-Zusatz: Ist der differenzierbare Renderer bei Equal-Power-Controls
numerisch identisch zum nicht-differenzierbaren Equal-Power-Crossfade?

Im Repo gibt es dafür keinen Test. Hier wird es gemessen:
  (1) Zwei-Band-Renderer mit linearer Rampe (= Epoche 0 des MLP) gegen
      EqualPowerFadeCut (src/cutting/equal_power_fade_cut.py; Hüllkurven aus fade_cut.py:152-166).
  (2) Full-Band-Renderer mit den Controls eines frisch initialisierten
      TCN/BiLSTM (= dessen "Epoche 0") gegen denselben Equal-Power-Crossfade.

Start: review_jp/.venv/bin/python review_jp/scripts/b5_renderer_equivalence.py
"""

from __future__ import annotations

import numpy as np
import torch

from common import TOP3, CACHE_V1, dump_json, load_split, load_waveforms
from src.control import DifferentiableTwoBandRenderer
from src.control.differentiable import DifferentiableFullBandTransitionRenderer
from src.cutting.equal_power_fade_cut import EqualPowerFadeCut
from src.ml.model import TCNBiLSTMTransitionControl


def db(value: float) -> float:
    return float(20 * np.log10(max(value, 1e-12)))


def rms(array) -> float:
    return float(np.sqrt(np.mean(np.square(array))))


def main():
    validation = load_split(TOP3, "validation")
    cutter = EqualPowerFadeCut(fade_beats=16, align_bar=True, snap_to_down_beat=True)
    two_band = DifferentiableTwoBandRenderer(11025, 180.0, 127)
    full_band = DifferentiableFullBandTransitionRenderer(11025, 180.0, 3500.0, 127)
    torch.manual_seed(0)
    tcn = TCNBiLSTMTransitionControl().eval()
    ramp = torch.linspace(0.0, 1.0, 32)
    rows = []
    for index, example_id in enumerate(validation["example_ids"]):
        wave = load_waveforms(CACHE_V1, example_id)
        source, target = wave["source_audio"], wave["target_audio"]
        fade_out, fade_in = cutter._build_envelopes(source.shape[-1])
        reference = source.numpy() * fade_out[None, :] + target.numpy() * fade_in[None, :]
        with torch.no_grad():
            rendered_two = two_band(source, target, ramp, ramp).audio.numpy()
            controls = tcn(
                torch.from_numpy(validation["features_a"][index]),
                torch.from_numpy(validation["features_b"][index]),
                torch.from_numpy(validation["global_features"][index]),
            )
            rendered_full = full_band(
                source, target, controls.gain_a, controls.gain_b,
                controls["eq_low_A"], controls["eq_low_B"],
                controls["eq_mid_A"], controls["eq_mid_B"],
                controls["eq_high_A"], controls["eq_high_B"],
                controls.low_end_ownership, controls.vocal_ducking,
            ).audio.numpy()
        rows.append({
            "example_id": example_id,
            "two_band_max_abs_error": float(np.abs(rendered_two - reference).max()),
            "two_band_error_rms_db_re_reference": db(rms(rendered_two - reference) / rms(reference)),
            "full_band_init_level_db_re_equal_power": db(rms(rendered_full) / rms(reference)),
            "full_band_init_error_rms_db_re_reference":
                db(rms(rendered_full - reference) / rms(reference)),
            "tcn_init_eq_value": float(controls["eq_mid_A"].mean()),
            "tcn_init_vocal_ducking": float(controls.vocal_ducking.mean()),
            "tcn_init_gain_a_first_mid_last": [float(controls.gain_a[i]) for i in (0, 15, 31)],
        })
    summary = {
        "n": len(rows),
        "two_band_max_abs_error_max": max(r["two_band_max_abs_error"] for r in rows),
        "two_band_error_rms_db_worst": max(r["two_band_error_rms_db_re_reference"] for r in rows),
        "full_band_init_level_db_mean":
            float(np.mean([r["full_band_init_level_db_re_equal_power"] for r in rows])),
        "full_band_init_error_rms_db_mean":
            float(np.mean([r["full_band_init_error_rms_db_re_reference"] for r in rows])),
        "tcn_init_eq_value": rows[0]["tcn_init_eq_value"],
        "tcn_init_vocal_ducking": rows[0]["tcn_init_vocal_ducking"],
        "rows": rows,
    }
    dump_json("b5_renderer_equivalence.json", summary)
    print({k: v for k, v in summary.items() if k != "rows"})


if __name__ == "__main__":
    main()
