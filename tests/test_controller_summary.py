import numpy as np

from src.evaluation.controller_summary import component_interval, recording_components


def test_recording_components_join_both_roles_and_keep_edge_multiplicity():
    pairs = [("a", "b"), ("c", "d"), ("other_b", "e"), ("e", "a"),
             ("f", "g"), ("h", "i"), ("j", "k")]
    groups = {track: track for pair in pairs for track in pair}
    groups["other_b"] = "b"
    components = recording_components(pairs, groups)
    assert components == [[0, 2, 3], [1], [4], [5], [6]]

    differences = np.array([0.1, 0.2, -0.4, 0.7, 0.5, 0.6, 1.5])
    draws = np.random.default_rng(20261121).integers(5, size=(10000, 5))
    means = [differences[[i for k in draw for i in components[k]]].mean() for draw in draws]
    np.testing.assert_allclose(component_interval(differences, components), np.quantile(means, [.025, .975]))
