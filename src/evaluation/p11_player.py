"""Package local, participant-specific blind players and a separate experimenter key."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from src.features.p07_mert import file_sha256
from src.features.p08_pairs import publish_dataset, rng_for


def package(panels, destination, person, split):
    order = sorted(panels)
    rng_for("panels", person, seed=20261120).shuffle(order)
    with publish_dataset(destination) as stage:
        public = stage / "player"
        public.mkdir()
        mapping, pages = {}, []
        for i, pair in enumerate(order, 1):
            directory = panels[pair]
            rows = json.loads((directory / "results.json").read_bytes())
            cells = {(r["selector"], r["condition"]) for r in rows}
            if (cells != {(s, c) for s in ("ssl", "rule", "random") for c in ("E", "D")} | {("rule", "anchor")}
                    or len(rows) != 7 or any(r["split"] != split for r in rows)):
                raise ValueError(f"Incomplete or foreign panel {pair}")
            rng_for("clips", person, pair, seed=20261120).shuffle(rows)
            page = []
            for j, row in enumerate(rows):
                code = f"{i:02d}-{chr(65+j)}"
                source = directory / row["wav"]
                if file_sha256(source) != row["wav_sha256"]:
                    raise ValueError(f"Stimulus SHA mismatch for {pair}")
                shutil.copyfile(source, public / (code + ".wav"))
                mapping[code] = dict(pair=pair, selector=row["selector"], condition=row["condition"],
                                     cue=row["candidate_id"], sha256=row["wav_sha256"])
                page.append(code)
            pages.append(page)
        template = Path(__file__).with_name("p11_player.html").read_text(encoding="utf-8")
        session_id = hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()
        public_data = json.dumps(dict(person=person, split=split, session_id=session_id,
                                      pages=pages)).replace("<", "\\u003c")
        (public / "index.html").write_text(template.replace("/*SESSION*/null", public_data), encoding="utf-8")
        (stage / "zuordnung.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("panel", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    package({"Entwicklung": args.panel}, args.output, "Demo", "development")
