import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
import pytest
import soundfile as sf

from src.evaluation.p11_session import (
    CELLS, REVISION, SELECTORS, Session, digest, layout, neutral_check, prepare, read, seal,
)
from src.evaluation.p11_web import server_for
from src.evaluation.p12_descriptive import analyse, decode, read_neutral
from src.features.p07_mert import file_sha256


def write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


@pytest.fixture
def study(tmp_path):
    package = tmp_path / "practice"
    (package / "player").mkdir(parents=True)
    mapping = {}
    for code in ("01-A", "01-B"):
        wav = package / "player" / (code + ".wav")
        sf.write(wav, np.zeros((200, 2)), 44100, subtype="PCM_24")
        mapping[code] = dict(sha256=file_sha256(wav))
    write(package / "zuordnung.json", mapping)
    (package / "player/index.html").write_text(
        "const session = " + json.dumps(dict(split="development", session_id=digest(mapping))) + ";\n")
    panels = []
    for index in range(7):
        panel = tmp_path / f"dev{index}"
        panel.mkdir()
        selectors = {s:s for s in SELECTORS}
        write(panel / "protocol.json", dict(panel=dict(pair_id=panel.name, selectors=selectors,
                                                       split="development", revision=REVISION)))
        rows = []
        for s, c in sorted(CELLS):
            wav = panel / f"{s}-{c}.wav"
            sf.write(wav, np.ones((200, 2)) * (len(rows) / 20), 44100, subtype="PCM_24")
            rows.append(dict(selector=s, condition=c, candidate_id=s, wav=wav.name, wav_sha256=file_sha256(wav),
                             split="development", pair=[f"a{index}", f"b{index}"],
                             protocol_sha256=file_sha256(panel / "protocol.json")))
        write(panel / "results.json", rows)
        panels.append(panel)
    root = tmp_path / "private"
    prepare(root, panels, package, "development")
    return root


def test_balanced_positions_and_anchors(study):
    key = read(study / "study_key.json")
    orders, anchor_by_pair = [], {}
    for i in range(7):
        mapping = layout(key, i)
        order = []
        for page in range(1, 8):
            assets = [asset for code,asset in mapping.items() if code.startswith(f"{page:02}-")]
            assert len(assets) == 7
            assert len([a for a in assets if a["condition"] != "anchor"]) == 6
            anchor, = [a for a in assets if a["condition"] == "anchor"]
            order.append(anchor["pair"])
            anchor_by_pair.setdefault(anchor["pair"], []).append(anchor["selector"])
        orders.append(order)
    assert all(len(set(position)) == 7 for position in zip(*orders))
    assert all(set(anchors[:3]) == set(SELECTORS) == set(anchors[3:6]) for anchors in anchor_by_pair.values())


def test_revised_render_requires_released_isolated_head(tmp_path, monkeypatch):
    from src.evaluation import p11_stimuli
    from src.ranking import continuation

    selection = tmp_path / "selection.json"
    monkeypatch.setattr(continuation, "ISOLATED_SELECTION", selection)
    for decision in (None, {"status":"pending"}, {"status":"selected", "ranking_method":continuation.METHOD}):
        if decision:
            write(selection, decision)
        with pytest.raises(ValueError, match="isolated-window"):
            p11_stimuli.run(tmp_path / "new-run", rotated=True)
    assert not (tmp_path / "new-run").exists()


def test_final_gate_replays_assignments_and_rejects_bad_timing(tmp_path, monkeypatch):
    from src.evaluation import comparison_study
    from src.evaluation.p11_session import check_final_panel
    from src.ranking import continuation

    head = tmp_path / "head.json"
    write(head, dict(status="selected", ranking_method=continuation.ISOLATED_METHOD))
    monkeypatch.setattr(continuation, "ISOLATED_SELECTION", head)
    monkeypatch.setattr(comparison_study, "measure_clip", lambda pcm:(-23., -10.))
    masters = tmp_path / "stimuli"
    masters.mkdir()
    sf.write(masters / "tone.wav", np.zeros((200, 2)), 44100, subtype="PCM_24")
    (tmp_path / "pool.csv").write_text("id,ssl,rule\none,1,1\n")
    pair = dict(pair_id="test")
    provenance = dict(selection_sha256=file_sha256(head), encoder_runtime=dict(device="cuda:0",gpu="test",
                                                                              autocast="bfloat16"))
    ranking = dict(ranker=continuation.ISOLATED_METHOD, scores=[dict(rank=1,candidate_id="one")],
                   provenance=provenance)
    winners = dict.fromkeys(SELECTORS, "one")
    write(tmp_path / "selection.json", dict(pair=pair, common=1, selectors=winners, cue_ranking=ranking,
          ranking_method=continuation.ISOLATED_METHOD,pool_sha256=file_sha256(tmp_path / "pool.csv")))
    panel = dict(pair_id="test", selectors=winners, pair_manifest_sha256=file_sha256(tmp_path / "selection.json"))
    write(tmp_path / "panel.json", panel)
    contract = dict(panel=panel, panel_sha256=file_sha256(tmp_path / "panel.json"), updates=80,
                    ssl_provenance=provenance)
    timing = dict(contract=REVISION,max_error_ms=20.,source_residual_ms=3.,target_residual_ms=4.,
                  beat_offset_ms=7.,span_error_ms=2.)
    row = dict(wav="tone.wav",geometry=dict(tempo_alignment=timing),
               loudness=dict(pair_target_lufs=-23., final_lufs=-23., final_dbtp=-10.))
    check_final_panel(masters, contract, [row], pair)
    timing["beat_offset_ms"] = 21.
    with pytest.raises(ValueError,match="timing"):
        check_final_panel(masters, contract, [row], pair)


def begin(s):
    s.event(dict(kind="begin", page=-1, profile=dict(music="viel", dj="wenig", dance="mittel", hearing="nein")))


def complete_page(s, person_offset):
    state = s.state()
    p = state["page"]
    for code in state["codes"]:
        a = s.mapping[code]
        value = 50
        if p and a["condition"] != "anchor":
            value += {"ssl":12, "rule":4, "random":0}[a["selector"]]
            value += 3 if a["condition"] == "D" else 0
            value += person_offset
        for kind in ("play", "ended", "rating"):
            s.event(dict(kind=kind, page=p, code=code, value=value))
    s.event(dict(kind="next", page=p))


def test_known_effects_on_sealed_originals(study, tmp_path, monkeypatch):
    # Hundreds of simulated clicks are committed here; the fixture only tests logical persistence.
    connect = Session.connect

    def fixture_db(session):
        db = connect(session)
        db.execute("PRAGMA synchronous=OFF")
        return db

    monkeypatch.setattr(Session, "connect", fixture_db)
    for i in range(3):
        s = Session(study, f"VP{i}")
        begin(s)
        with pytest.raises(ValueError):
            s.event(dict(kind="next", page=0))
        complete_page(s, i)
        complete_page(s, i)
        s.event(dict(kind="back", page=2))
        assert s.state()["page"] == 1
        s.event(dict(kind="next", page=1))
        resumed = Session(study, f"VP{i}")
        assert resumed.sid == s.sid and resumed.state()["page"] == 2
        while not resumed.state()["done"]:
            complete_page(resumed, i)
        with pytest.raises(ValueError, match="abgeschlossen"):
            s.event(dict(kind="back", page=7))
    Session(study, "unterbrochen")
    out = tmp_path / "sealed"
    seal(study, out)
    result = analyse(out, study / "study_key.json", "development")
    assert result["available_panels"] == result["valid_panels"] == 21
    assert result["independent_pairs"] == 7
    assert result["incomplete_sessions"][0]["person"] == "unterbrochen"
    expected = dict(ssl_minus_rule=8., top_minus_random=8., direct_minus_equal=3., absolute_where_minus_how=5.)
    assert result["pair_weighted_effects"] == expected
    assert result["h3_distance_points"] == 8
    assert all(effects == expected for effects in result["leave_one_person_out"].values())
    assert result["descriptive_95"] == {k:[v,v] for k,v in expected.items()}
    records, _ = read_neutral(out)
    assert neutral_check(records)["anomalies"] == []
    key = read(study / "study_key.json")
    mapping = layout(key, records[0]["ordinal"])
    anchor = next(k for k,v in mapping.items() if k.startswith("01-") and v["condition"]=="anchor")
    cell = next(k for k,v in mapping.items() if k.startswith("02-") and v["condition"]!="anchor")
    del records[0]["state"]["ratings"][anchor]
    records[0]["state"]["ratings"][cell] = 101
    anomalies = neutral_check(records)["anomalies"]
    assert [a["missing_or_invalid_rating"] for a in anomalies] == [[anchor], [cell]]
    assert not any("selector" in a or "condition" in a for a in anomalies)
    data, anchors, exclusions = decode(records, key)
    assert len(data) == 20 and len(anchors) == 20
    assert {e["reason"] for e in exclusions} == {"missing anchor", "incomplete factorial panel"}
    raw_path = out / next(iter(read(out / "receipt.json")["files"]))
    raw_path.write_bytes(raw_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum"):
        analyse(out, study / "study_key.json", "development")


def test_loopback_serves_only_neutral_current_page(study):
    session = Session(study, "Pilot")
    server, url = server_for(session, 0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(url) as response:
            assert response.status == 200
        with urlopen(url + "state") as response:
            state = json.load(response)
        assert state["page"] == -1 and "mapping" not in state and "split" not in state
        with pytest.raises(HTTPError, match="404"):
            urlopen(url + "study_key.json")
        with pytest.raises(HTTPError, match="404"):
            urlopen(url + "audio/01-A")
        payload = dict(kind="begin", page=-1, profile=dict(music="viel", dj="wenig", dance="mittel", hearing="nein"))
        headers = {"Origin":f"http://127.0.0.1:{server.server_port}", "Content-Type":"application/json"}
        with urlopen(Request(url+"event", data=json.dumps(payload).encode(), headers=headers)) as response:
            state = json.load(response)
        assert state["codes"] == ["00-A", "00-B"] and all(v is None for v in state["ratings"].values())
        with urlopen(url + "audio/00-A") as response:
            assert response.read(4) == b"RIFF"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
