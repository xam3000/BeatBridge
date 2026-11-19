"""Build the P01 metadata-only exposure register from local BeatBridge artefacts."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from src.variable_corpus_inventory import AUDIO_EXTENSIONS, _recording_group_key


CORPUS = Path("output/corpora/prive_scantraxx_extension_v2_20260923_run01")
BASE_BATCH = Path("output/batches/all_music_recursive_bpm145_165_top1_20260805/manifest.json")
PRIVE_BATCH = Path("output/batches/prive/_top1000/_baseline/_20260921_fixed/manifest.json")
PUBLIC = Path("docs/masterarbeit/review_jp_20261118/p01")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory_file(item):
    path, label = item
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_type:stream_tags=artist,title,isrc:format=duration:format_tags=artist,title,isrc",
         "-of", "json", str(path)], capture_output=True, check=True, encoding="utf-8",
    )
    metadata = json.loads(result.stdout)
    header = metadata["format"]
    stream = metadata["streams"][0]
    tags = {k.lower(): v.strip() for source in (stream, header)
            for k, v in source.get("tags", {}).items()}
    duration = float(header["duration"])
    if not math.isfinite(duration) or duration <= 0 or stream["codec_type"] != "audio":
        raise ValueError(f"Invalid audio header: {label}")
    isrc = re.sub(r"[-\s]", "", tags.get("isrc", "")).upper()
    return dict(path=label, sha256=sha(path), artist=tags.get("artist", ""),
                title=tags.get("title", ""), isrc=isrc, duration_seconds=duration)


class History:
    def __init__(self, tracks):
        self.by_path = {t["path"].casefold(): t["sha256"] for t in tracks}
        self.digests = set(self.by_path.values())
        self.evidence = defaultdict(set)
        self.sources = {}
        self.group_ids = defaultdict(set)
        self.previously_exposed = set()

    def register(self, path, role):
        sid = f"S{len(self.sources) + 1:03}"
        self.sources[sid] = {"path": path.as_posix(), "sha256": sha(path), "role": role}
        return sid

    def mark(self, sid, reason, path=None, digest=None):
        if path:
            parts = path.replace("\\", "/").casefold().split("/")
            if "musik" not in parts:
                raise ValueError(f"{sid}: unrecognised source path {path}")
            key = "/".join(parts[parts.index("musik"):])
            actual = self.by_path[key]
            if digest and actual != digest:
                raise ValueError(f"{sid}: historical SHA mismatch at {path}")
            digest = actual
        if digest not in self.digests:
            raise ValueError(f"{sid}: historical recording missing locally {digest}")
        self.evidence[digest].add(f"{sid}/{reason}")


def load(path):
    return json.loads(path.read_bytes())


def historical_sources(tracks):
    h = History(tracks)
    for name in ("corpus_manifest.json", "recording_groups.json", "split_authority.json"):
        path = CORPUS / name
        data = load(path)
        sid = h.register(path, "historical corpus")
        if name == "split_authority.json":
            for row in data["track_assignments"]:
                h.mark(sid, row["split"], digest=row["sha256"])
        else:
            for row in data["tracks"] + data.get("recording_conflict_exclusions", []):
                h.mark(sid, row.get("reason", "inventory"), row.get("path"), row["sha256"])
                h.group_ids[row["sha256"]].add(row["recording_group_id"])

    datasets = {}
    for path in sorted(Path("output/datasets").glob("*/manifest.json")):
        sid = h.register(path, "dataset assignment")
        data = load(path)
        datasets[h.sources[sid]["sha256"]] = sid
        for row in data["track_assignments"]:
            h.mark(sid, row["split"], row.get("path"), row["sha256"])
    for path in sorted(Path("output/training_runs").glob("prive*20260926_run01/manifest.json")):
        sid = h.register(path, "September training contract")
        contract = load(path)["contract"]
        dataset = (contract["dataset"]["manifest_sha256"] if "dataset" in contract
                   else contract["dataset_manifest_sha256"])
        h.sources[sid]["dataset_source"] = datasets[dataset]

    batches = {BASE_BATCH, PRIVE_BATCH, Path("output/batches/prive_top1000_variable_top3_20260922/manifest.json")}
    batches.update(Path("output/batches").glob("all_*/*manifest.json"))
    batches.update(Path("output").glob("batch_variable*/manifest.json"))
    batches.update(Path("output/producers").glob("*/manifest.json"))
    for path in sorted(batches):
        data = load(path)
        sid = h.register(path, "batch / producer")
        for track_path in data.get("songs", []):
            h.mark(sid, "input", track_path)
        for role in ("duplicate_tracks", "excluded_tracks", "closed_split_exclusions"):
            for row in data.get(role, []):
                h.mark(sid, role, row["path"], row.get("sha256"))
        for role in ("analysis_failures", "excluded_tracks"):
            for row in data.get("bpm_filter", {}).get(role, []):
                h.mark(sid, "bpm_" + role, row["path"])
        for row in data["sources"]:
            h.mark(sid, "source", row["source_path"], row.get("source_audio_sha256"))
            for target in row.get("selected_target_paths", []):
                h.mark(sid, "selected_target", target)

    studies = sorted({*Path("output/control_studies").glob("*/manifest.json"),
                      *Path("output").glob("four_models*/manifest.json"),
                      *Path("output/control_comparisons").glob("*/manifest.json")})
    for path in studies:
        data = load(path)
        sid = h.register(path, "study / control comparison")
        if "pairs" not in data and "main_study" not in data:
            raise ValueError(f"Unrecognised study manifest: {path}")
        for pair in data.get("pairs", []):
            original = pair if "source_track" in pair else pair.get("dataset_example", pair.get("candidate"))
            for role in ("source_track", "target_track"):
                track = original[role]
                if isinstance(track, str):
                    h.mark(sid, role, track)
                else:
                    h.mark(sid, role, track["path"], track.get("sha256"))

    for path in sorted(Path("output/gui_transitions").glob("*.json")):
        sid = h.register(path, "manual GUI render")
        data = load(path)
        for role in ("source", "target"):
            h.mark(sid, role, data[role]["path"], data[role]["sha256"])

    policy = Path("config/track_exclusions.json")
    sid = h.register(policy, "documented exclusion")
    for row in load(policy)["tracks"]:
        h.mark(sid, "policy", row["path"], row["sha256"])
    for name in ("RESULTS_EVIDENCE_LEDGER.md", "CONTROL_STUDY_PROTOCOL.md",
                 "LISTENING_STUDY_ANALYSE_20261106.md"):
        h.register(Path("docs") / name, "historical interpretation / listening exposure")
    return h


def resolve_groups(tracks, history, reviews):
    # Union of identities. A link can join two previously separate components.
    parent = {}

    def root(token):
        parent.setdefault(token, token)
        while token != parent[token]:
            parent[token] = parent[parent[token]]
            token = parent[token]
        return token

    for track in tracks:
        digest = track["sha256"]
        root(digest)
        review = reviews.get(digest, {})
        artist = track["artist"] or review.get("artist", "")
        title = track["title"] or review.get("title", "")
        track.update(artist=artist, title=title)
        tokens = set(history.group_ids[digest])
        if artist and title:
            key = _recording_group_key(artist, title)
            if "unknown" not in key.split("|"):
                tokens.add("recording-" + hashlib.sha256(key.encode()).hexdigest()[:20])
        if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}", track["isrc"]):
            tokens.add("isrc-" + track["isrc"])
        alias = review.get("alias_sha256", "")
        if alias:
            if alias not in history.digests:
                raise ValueError(f"Alias refers to absent file: {alias}")
            tokens.add(alias)
        for token in sorted(tokens):
            parent[root(token)] = root(digest)

    components = defaultdict(set)
    for token in parent:
        components[root(token)].add(token)
    for track in tracks:
        digest = track["sha256"]
        component = components[root(digest)]
        historical = {g for member in component for g in history.group_ids.get(member, ())}
        ids = sorted(historical or {t for t in component if t.startswith("recording-")})
        track["recording_group_id"] = ids[0] if ids else "unresolved-" + root(digest)
        track["direct_evidence"] = " ".join(sorted(history.evidence[digest]))
        track["clearance_source"] = reviews.get(digest, {}).get("source", "")
        track["clearance_decision"] = reviews.get(digest, {}).get("decision", "")
        track["alias_sha256"] = reviews.get(digest, {}).get("alias_sha256", "")

    blocked = {track["recording_group_id"] for track in tracks
               if track["direct_evidence"] or track["sha256"] in history.previously_exposed
               or track["clearance_decision"] == "used"}
    # An unresolved submission may be another edition of a putatively fresh one.
    pending = {track["recording_group_id"] for track in tracks
               if reviews.get(track["sha256"], {}).get("decision") != "unused"
               or not track["clearance_source"] or not track["artist"] or not track["title"]
               or track["recording_group_id"].startswith("unresolved-")}
    for track in tracks:
        group = track["recording_group_id"]
        track["status"] = "exposed" if group in blocked else "pending" if group in pending else "eligible"


def population(tracks):
    representatives = {}
    for track in sorted(tracks, key=lambda t: t["sha256"]):
        if track["status"] == "eligible":
            representatives.setdefault(track["recording_group_id"], track["sha256"])
    def order(group):
        return hashlib.sha256(f"P01-v1|{group}".encode()).digest(), group
    ordered = [{"recording_group_id": g, "sha256": representatives[g]}
               for g in sorted(representatives, key=order)]
    count = min(12, len(ordered) // 2)
    pairs = []
    if count >= 10:
        for i in range(count):
            pairs.append(dict(pair_id=f"P{i + 1:02}", source=ordered[2*i], target=ordered[2*i+1]))
    return dict(format_version=1, protocol="P01-v1", status="awaiting_user_commit" if pairs else "insufficient_material",
                eligible_groups=ordered, pairs=pairs, possible_disjoint_pairs=count,
                missing_groups_for_10=max(0, 20-len(ordered)), missing_groups_for_12=max(0, 24-len(ordered)))


def run(destination, extra=None, clearance=None):
    if destination.exists():
        raise FileExistsError(f"Output must be a new directory: {destination}")
    files = [(p, p.as_posix()) for p in sorted(Path("musik").rglob("*")) if p.suffix.lower() in AUDIO_EXTENSIONS]
    if extra:
        if not extra.is_dir() or extra.resolve().is_relative_to(Path("musik").resolve()):
            raise ValueError("Additional source must be a separate existing directory")
        files.extend((p, "intake/" + p.relative_to(extra).as_posix()) for p in sorted(extra.rglob("*"))
                     if p.suffix.lower() in AUDIO_EXTENSIONS)
    with ThreadPoolExecutor(max_workers=4) as workers:
        tracks = list(workers.map(inventory_file, files))
    history = historical_sources(tracks)
    # Later use can add evidence. The historical local artefacts remain immutable.
    reference = PUBLIC / "exposure_sources.json"
    if reference.exists():
        previous = load(reference)
        present = {s["path"]: s["sha256"] for s in history.sources.values()}
        for source in previous["sources"].values():
            path = source["path"]
            if path not in present or (path.startswith("output/") and present[path] != source["sha256"]):
                raise ValueError(f"Missing or changed historical source: {path}")
        catalog = reference.with_name("exposure_tracks.csv")
        if sha(catalog) != previous["exposure_tracks_sha256"]:
            raise ValueError("Historical exposure catalog checksum mismatch")
        with catalog.open(encoding="utf-8", newline="") as stream:
            for old in csv.DictReader(stream):
                if old["status"] == "exposed":
                    if history.by_path.get(old["path"].casefold()) != old["sha256"]:
                        raise ValueError(f"Missing or replaced historical recording: {old['path']}")
                    history.group_ids[old["sha256"]].add(old["recording_group_id"])
                    history.previously_exposed.add(old["sha256"])
    reviews = {}
    if clearance:
        with clearance.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                digest = row["sha256"]
                if (digest in reviews or digest not in history.digests or not row["source"].strip()
                        or row["decision"] not in {"used", "unused", "unclear"}):
                    raise ValueError(f"Invalid clearance row: {digest}")
                reviews[digest] = row
    resolve_groups(tracks, history, reviews)
    result = population(tracks)
    group_status = {t["recording_group_id"]: t["status"] for t in tracks}
    counts = Counter(eligible=0, pending=0, exposed=0)
    counts.update(group_status.values())
    sources = dict(format_version=1, sources=history.sources, file_count=len(tracks),
                   unique_audio_hashes=len(history.digests), groups_by_status=dict(counts))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as scratch:
        bundle = Path(scratch) / "bundle"
        bundle.mkdir()
        catalog = bundle / "exposure_tracks.csv"
        with catalog.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(tracks[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(tracks)
        for name, data in (("exposure_sources", sources), ("evaluation_population", result)):
            data["exposure_tracks_sha256"] = sha(catalog)
            (bundle / (name + ".json")).write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode())
        bundle.rename(destination)
    print(json.dumps({**{k: v for k, v in sources.items() if k != "sources"},
                      "sources": len(history.sources), "status": result["status"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--extra", type=Path, help="Additional directory of original recordings")
    parser.add_argument("--clearance", type=Path, help="Documented, SHA-keyed metadata decisions (CSV)")
    args = parser.parse_args()
    run(args.destination, args.extra, args.clearance)
