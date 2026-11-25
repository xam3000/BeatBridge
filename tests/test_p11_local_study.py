import json
from http.cookiejar import CookieJar
from pathlib import Path
import re
import sqlite3
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen
from wsgiref.simple_server import make_server

import numpy as np
import pytest
import soundfile as sf
from hoertest.app import StudyApp

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


def test_rating_scale_and_existing_session(study):
    session = Session(study, "current")
    begin(session)
    rating = dict(kind="rating", page=0, code="00-A")
    for value in range(1, 8):
        session.event(dict(rating, value=value))
    for value in (0, 8, 100, 1.5, True, "4", None):
        with pytest.raises(ValueError, match="1 bis 7"):
            session.event(dict(rating, value=value))
    resumed = Session(study, "current").state()
    assert resumed["ratings"] == {"00-A": 7, "00-B": None}
    assert not resumed["heard"]

    # Recreate an in-progress session as stored by the original player.
    old = Session(study, "legacy")
    begin(old)
    with sqlite3.connect(study / "responses.sqlite") as db:
        raw, = db.execute("SELECT state FROM sessions WHERE sid=?", (old.sid,)).fetchone()
        state = json.loads(raw)
        del state["rating_scale"]
        del state["rating_protocol_sha256"]
        state["ratings"]["00-A"] = 53
        db.execute("UPDATE sessions SET state=? WHERE sid=?", (json.dumps(state), old.sid))
    old = Session(study, "legacy")
    assert old.state()["rating_scale"] == (0, 100)
    assert old.state()["ratings"]["00-A"] == 53
    old.event(dict(rating, value=100))
    assert old.state()["ratings"]["00-A"] == 100


def complete_page(s, person_offset, *, ssl_offset=0):
    state = s.state()
    p = state["page"]
    for code in state["codes"]:
        a = s.mapping[code]
        value = 1
        if p and a["condition"] != "anchor":
            value += {"ssl":2 + ssl_offset, "rule":1, "random":0}[a["selector"]]
            value += int(a["condition"] == "D")
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
    assert result["analysis_scale"] == [1, 7]
    assert all(row["mean"] == 1 for row in result["anchors"].values())
    assert all(pair["cells"]["ssl_D"] == 5 for pair in result["pairs"])
    expected = dict(ssl_minus_rule=1, top_minus_random=1.5,
                    direct_minus_equal=1, absolute_where_minus_how=.5)
    assert result["sessions_by_rating_scale"] == {"1-7": 3}
    assert result["pair_weighted_effects"] == pytest.approx(expected)
    assert result["h3_reference_points"] == -.3
    assert result["h3_distance_points"] == pytest.approx(1.3)
    assert all(effects == pytest.approx(expected) for effects in result["leave_one_person_out"].values())
    for name, value in expected.items():
        assert result["descriptive_95"][name] == pytest.approx([value, value])
    records, _ = read_neutral(out)
    assert neutral_check(records)["anomalies"] == []
    key = read(study / "study_key.json")
    mapping = layout(key, records[0]["ordinal"])
    old = json.loads(json.dumps(records[0]))
    old_state = old["state"]
    # Recorded by the first seven-point player, before the change in reporting units.
    old_state["rating_protocol_sha256"] = "e71c79e5f7dd37bc74c16ffcd8ef1006b0d8b329e8a253c04c45c1dc6cf82402"
    old_state["ratings"] = dict.fromkeys(old_state["ratings"], 7)
    old_cells, old_anchors, excluded = decode([old], key)
    assert not excluded and all(row == [7] * 6 for row in old_cells.values())
    assert all(anchor["score"] == 7 for anchor in old_anchors)
    old_state["rating_protocol_sha256"] = "incorrect"
    with pytest.raises(ValueError, match="Rating procedure"):
        decode([old], key)
    del old_state["rating_scale"], old_state["rating_protocol_sha256"]
    old_state["ratings"] = dict.fromkeys(old_state["ratings"], 53)
    assert not neutral_check([old])["anomalies"]
    legacy_cells, legacy_anchors, excluded = decode([old], key)
    assert not excluded and all(row == pytest.approx([4.18] * 6) for row in legacy_cells.values())
    assert all(anchor["score"] == pytest.approx(4.18) for anchor in legacy_anchors)
    anchor = next(k for k,v in mapping.items() if k.startswith("01-") and v["condition"]=="anchor")
    cell = next(k for k,v in mapping.items() if k.startswith("02-") and v["condition"]!="anchor")
    del records[0]["state"]["ratings"][anchor]
    records[0]["state"]["ratings"][cell] = 8
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


@pytest.fixture
def institute(study, tmp_path):
    root = tmp_path / "transport"
    prepare(root, sorted(tmp_path.glob("dev*")), tmp_path / "practice", "development", institute=True)
    deployed = tmp_path / "server-copy"
    root.rename(deployed)
    return deployed


def test_institute_assignment_and_sealed_results(institute, tmp_path):
    key = read(institute / "study_key.json")
    orders, anchors = [], {pair: [] for pair in key["panels"]}
    for seat in range(21):
        mapping = layout(key, seat, f"saved-session-{seat}")
        assert mapping == layout(key, seat, f"saved-session-{seat}")
        order = []
        for page in range(1, 8):
            assigned = [a for code, a in mapping.items() if code.startswith(f"{page:02}-")]
            anchor, = [a for a in assigned if a["condition"] == "anchor"]
            order.append(anchor["pair"])
            anchors[anchor["pair"]].append(anchor["selector"])
        orders.append(order)
    for first in range(0, 21, 7):
        assert all(set(position) == key["panels"].keys() for position in zip(*orders[first:first + 7]))
    for selectors in anchors.values():
        assert all(set(selectors[first:first + 3]) == set(SELECTORS) for first in range(0, 21, 3))
    assert layout(key, 0, "other-session") != layout(key, 0, "saved-session-0")
    assert len(list((institute / "media").glob("*.wav"))) == 9  # Identical fixture clips are copied once.
    assert all(Path(a["path"]).parent == Path("media") for a in mapping.values())

    Session(institute, "unterbrochen")
    unfinished = tmp_path / "nur-unterbrochen"
    seal(institute, unfinished)
    counts = analyse(unfinished, institute / "study_key.json", "development")
    assert counts["started_sessions"] == 1 and counts["completed_sessions"] == 0
    assert counts["analysis_scale"] == [1, 7]
    assert counts["pair_weighted_effects"] is None
    assert all(group["pair_weighted_effects"] is None and group["completed_sessions"] == 0
               for group in counts["by_listening_setting"].values())
    completed = Session(institute, "test-session")
    completed.event(dict(kind="begin", page=-1, profile=dict(music="mittel", dj="wenig", dance="viel",
                         hearing="keine Angabe", setting="anderer Hörplatz")))
    while not completed.state()["done"]:
        complete_page(completed, 0)
    on_site = Session(institute, "test-on-site")
    on_site.event(dict(kind="begin", page=-1, profile=dict(music="mittel", dj="wenig", dance="viel",
                       hearing="keine Angabe", setting="Institut")))
    while not on_site.state()["done"]:
        complete_page(on_site, 0, ssl_offset=-1)
    originals = tmp_path / "originale-institut"
    seal(institute, originals)
    report = analyse(originals, institute / "study_key.json", "development")
    assert report["started_sessions"] == 3 and report["completed_sessions"] == 2
    assert len(report["incomplete_sessions"]) == 1 and report["valid_panels"] == 14
    assert all(sum(pos) == 2 for pos in report["completed_pair_positions"].values())
    assert report["pair_weighted_effects"]["ssl_minus_rule"] == .5
    assert report["pair_weighted_effects"]["direct_minus_equal"] == 1
    assert report["profiles"]["test-session"]["setting"] == "anderer Hörplatz"
    for setting, expected in (("Institut", 0), ("anderer Hörplatz", 1)):
        group = report["by_listening_setting"][setting]
        assert group["completed_sessions"] == group["sessions_with_valid_panels"] == 1
        assert group["valid_panels"] == group["independent_pairs"] == 7
        assert group["pair_weighted_effects"]["ssl_minus_rule"] == pytest.approx(expected)
        assert all(pair["effects"]["ssl_minus_rule"] == pytest.approx(expected) for pair in group["pairs"])

    records, _ = read_neutral(originals)
    deadline = min(row["state"]["finished"] for row in records)
    on_time = tmp_path / "sealed-with-deadline"
    seal(institute, on_time, deadline=deadline)
    report = analyse(on_time, institute / "study_key.json", "development")
    assert len(read_neutral(on_time)[0]) == 2
    assert report["started_sessions"] == 3 and report["all_submitted_sessions"] == 2
    assert report["completed_sessions"] == 1 and len(report["late_submissions"]) == 1
    assert report["valid_panels"] == 7 and report["pair_weighted_effects"]["ssl_minus_rule"] == 1
    with pytest.raises(ValueError, match="UTC offset"):
        seal(institute, tmp_path / "ambiguous-deadline", deadline="2026-11-25T12:00:00")


@pytest.mark.parametrize("material", ["run02", "cue_grid_regression_v3_fixed_rule"])
def test_institute_fixed_anchors_keep_all_49_clips_on_every_seat(institute, material):
    key = read(institute / "study_key.json")
    key["material"] = material
    for pair, assets in key["panels"].items():
        key["panels"][pair] = [a for a in assets if a["condition"] != "anchor" or a["selector"] == "rule"]
    expected = {(pair, a["selector"], a["condition"], a["sha256"])
                for pair, assets in key["panels"].items() for a in assets}
    orders = set()
    for seat in range(21):
        mapping = layout(key, seat, f"saved-{seat}")
        clips = [asset for code, asset in mapping.items() if not code.startswith("00-")]
        identity = [(a["pair"], a["selector"], a["condition"], a["sha256"]) for a in clips]
        assert len(identity) == 49 and set(identity) == expected
        orders.add(tuple(identity))
    assert len(orders) == 21


def test_institute_common_link_shuffles_and_resumes(institute):
    with make_server("127.0.0.1", 0, None) as server:
        origin = f"http://127.0.0.1:{server.server_port}"
        url = origin + "/institut/hoertest/"
        server.set_app(StudyApp(institute, url))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def seats():
            with sqlite3.connect(institute / "responses.sqlite") as db:
                return db.execute("SELECT count(*) FROM sessions").fetchone()[0]

        def visit(browser):
            with browser.open(url) as response:
                html = response.read().decode()
                return html, re.search(r'name="form" value="([^"]+)"', html)[1]

        def start(browser, nonce):
            form = urlencode(dict(form=nonce, participate="yes")).encode()
            with browser.open(Request(url + "start", data=form, headers={"Origin": origin})) as response:
                assert response.status == 200
                return response.geturl()

        def state(browser, location):
            with browser.open(location + "state") as response:
                return json.load(response)

        try:
            first = build_opener(HTTPCookieProcessor(CookieJar()))
            second = build_opener(HTTPCookieProcessor(CookieJar()))
            html, nonce = visit(first)
            assert "7 Entwicklungspaare" in html and "Begonnene Sitzung fortsetzen" not in html and seats() == 0
            saved = start(first, nonce)
            assert start(first, nonce) == saved and seats() == 1
            other = start(second, visit(second)[1])
            assert other != saved and seats() == 2
            assert "Begonnene Sitzung fortsetzen" in visit(first)[0]
            assert state(first, saved)["session_code"] == urlsplit(saved).path.split("/")[-2]
            with pytest.raises(HTTPError, match="403"):
                state(second, saved)
            with pytest.raises(HTTPError, match="404"):
                first.open(url + "study_key.json")
            event = dict(kind="begin", page=-1, profile=dict(music="viel", dj="wenig", dance="mittel",
                         hearing="keine Angabe", setting="Institut"))
            with first.open(Request(saved + "event", data=json.dumps(event).encode(),
                            headers={"Origin": origin, "Content-Type": "application/json"})) as response:
                assert json.load(response)["codes"] == ["00-A", "00-B"]
            with first.open(Request(saved + "audio/00-A", headers={"Range": "bytes=0-3"})) as response:
                assert response.status == 206 and response.read() == b"RIFF"
            with first.open(Request(saved + "audio/00-A", method="HEAD")) as response:
                assert int(response.headers["Content-Length"]) > 4 and response.read() == b""
            with pytest.raises(HTTPError, match="404"):
                first.open(saved + "audio/01-A")
            assert state(second, other)["page"] == -1
            assert state(first, saved)["page"] == 0
            fresh = start(first, visit(first)[1])
            assert fresh not in (saved, other) and state(first, fresh)["page"] == -1 and seats() == 3
        finally:
            server.shutdown()
            thread.join()
