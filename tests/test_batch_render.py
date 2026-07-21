import json

import numpy as np
import pytest
import soundfile as sf

from src.batch_render import render_candidate_batch
from src.candidates import CandidateGenerationConfig
from src.pipeline import generate_transition_candidates


class StubAnalysis:
    def __call__(self, song_path):
        info = sf.info(song_path)
        beat_step = info.samplerate // 2  # 120 BPM
        beats = [
            (sample, index % 4 + 1, 4)
            for index, sample in enumerate(range(0, info.frames, beat_step))
        ]
        return 120.0, beats


@pytest.fixture
def batch_inputs(tmp_path):
    song1 = tmp_path / "song1.wav"
    song2 = tmp_path / "song2.wav"
    sf.write(song1, np.zeros(44_100 * 20, dtype=np.float32), 44_100)
    sf.write(song2, np.zeros(48_000 * 20, dtype=np.float32), 48_000)
    analysis = StubAnalysis()
    candidates = generate_transition_candidates(
        song1,
        song2,
        analysis=analysis,
        config=CandidateGenerationConfig(
            transition_lengths_bars=(1,),
            source_boundary_count=1,
            target_boundary_count=1,
        ),
    )
    return candidates, analysis, tmp_path / "batch"


def test_batch_render_exports_wavs_and_a_traceable_manifest(batch_inputs):
    candidates, analysis, output_directory = batch_inputs

    result = render_candidate_batch(
        candidates,
        output_directory,
        renderers=("simple", "fade"),
        analysis=analysis,
    )

    assert not result.failures
    assert len(result.rendered_variants) == 2
    assert result.manifest_path.is_file()
    for variant in result.rendered_variants:
        output_path = output_directory / variant.output_file
        assert output_path.is_file()
        assert sf.info(output_path).samplerate == 44_100
        assert variant.candidate_id == candidates.candidates[0].candidate_id

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["format_version"] == 1
    assert manifest["candidate_generation"]["candidates"][0]["candidate_id"] == candidates.candidates[0].candidate_id
    assert [item["renderer"] for item in manifest["rendered_variants"]] == ["simple", "fade"]


def test_batch_render_refuses_to_replace_existing_artifacts_without_opt_in(batch_inputs):
    candidates, analysis, output_directory = batch_inputs
    render_candidate_batch(candidates, output_directory, renderers=("simple",), analysis=analysis)

    with pytest.raises(FileExistsError, match="overwrite=True"):
        render_candidate_batch(candidates, output_directory, renderers=("simple",), analysis=analysis)
