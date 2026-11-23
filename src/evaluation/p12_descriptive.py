"""Decode sealed P11 v2 originals and summarize the seven independent track pairs."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

from src.evaluation.p11_session import FINAL_PAIRS, SELECTORS, VERSION, digest, layout, neutral_check, public_layout, read
from src.features.p07_mert import file_sha256


CELLS = tuple((s, c) for s in SELECTORS for c in ("E", "D"))
NAMES = ("ssl_minus_rule", "top_minus_random", "direct_minus_equal", "absolute_where_minus_how")


def effects(values):
    """Last dimension is (ssl/E, ssl/D, rule/E, rule/D, random/E, random/D)."""
    ssl, rule, random = (values[..., i:i+2].mean(-1) for i in (0, 2, 4))
    where = (ssl + rule)/2 - random
    how = (values[..., 1::2] - values[..., ::2]).mean(-1)
    return np.stack((ssl-rule, where, how, np.abs(where)-np.abs(how)), axis=-1)


def numbers(values):
    return dict(zip(NAMES, map(float, values), strict=True))


def read_neutral(originals):
    receipt = read(originals / "receipt.json")
    records = []
    for name, claimed in receipt["files"].items():
        path = originals / name
        if path.name != name or file_sha256(path) != claimed:
            raise ValueError("Sealed original checksum differs")
        record = read(path)
        if record["version"] != VERSION or name != record["sid"] + ".json" or not record["state"]["finished"]:
            raise ValueError("Invalid or unfinished original")
        records.append(record)
    audit = originals / "neutral_check.json"
    if file_sha256(audit) != receipt["neutral_check_sha256"] or read(audit) != neutral_check(records):
        raise ValueError("Blind validation report differs from the sealed originals")
    return records, receipt["incomplete"]


def decode(records, key):
    data, anchors, excluded = {}, [], []
    people = Counter(r["person"] for r in records)
    ordinals = Counter(r["ordinal"] for r in records)
    for r in records:
        person, state = r["person"], r["state"]
        if people[person] != 1 or ordinals[r["ordinal"]] != 1:
            excluded.append(dict(person=person, reason="duplicate participant or seat"))
            continue
        mapping = layout(key, r["ordinal"])
        if (state["split"] != key["split"] or state["protocol_sha256"] != key["protocol_sha256"]
                or r["key_hash"] != digest(mapping) or public_layout(mapping) != r["pages"]):
            raise ValueError("Wrong assignment, protocol, split or clip SHA for sealed session")
        for page in r["pages"][1:]:
            cells, anchor = {}, None
            pair = mapping[page[0]["code"]]["pair"]
            for clip in page:
                code = clip["code"]
                a = mapping[code]
                value = state["ratings"].get(code)
                if (type(value) is not int or not 0 <= value <= 100 or code not in state["heard"]
                        or state["plays"].get(code, 0) < 1):
                    continue
                if a["condition"] == "anchor":
                    anchor = dict(person=person, pair=pair, selector=a["selector"], score=value)
                else:
                    cells[a["selector"], a["condition"]] = value
            if anchor is None:
                excluded.append(dict(person=person, pair=pair, reason="missing anchor"))
            else:
                anchors.append(anchor)
            if cells.keys() != set(CELLS):
                excluded.append(dict(person=person, pair=pair, reason="incomplete factorial panel"))
                continue
            data[person,pair] = [cells[c] for c in CELLS]
    return data, anchors, excluded


def pair_means(data):
    pairs = sorted({pair for _,pair in data})
    return pairs, np.asarray([np.mean([row for (_,p),row in data.items() if p == pair], axis=0)
                              for pair in pairs])


def correlation(left, right):
    a, b = np.asarray(left), np.asarray(right)
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def anchor_report(pairs, anchors):
    result = {}
    for pair in sorted(pairs):
        values = [a for a in anchors if a["pair"] == pair]
        by_selector = {}
        for selector in SELECTORS:
            ratings = [a["score"] for a in values if a["selector"] == selector]
            by_selector[selector] = dict(n=len(ratings), mean=float(np.mean(ratings)) if ratings else None)
        result[pair] = dict(scores=values, n=len(values),
                            mean=float(np.mean([a["score"] for a in values])) if values else None,
                            by_selector=by_selector)
    return result


def analyse(originals, key_path, expected_split):
    records, incomplete = read_neutral(originals)
    key = read(key_path)
    if key["split"] != expected_split or key["version"] != VERSION:
        raise ValueError("Study split or application version differs")
    if expected_split == "final":
        groups = key["groups"]
        if (set(key["panels"]) != FINAL_PAIRS or groups.keys() != FINAL_PAIRS
                or any(len(g) != 2 for g in groups.values())
                or len({g for pair in groups.values() for g in pair}) != 14):
            raise ValueError("Final analysis requires seven pairs and fourteen disjoint recording groups")
    data, anchors, excluded = decode(records, key)
    counts = Counter(r["person"] for r in records)
    profiles = {r["person"]:r["state"]["profile"] for r in records if counts[r["person"]]==1}
    base = dict(version=VERSION, split=expected_split, analysis="descriptive", profiles=profiles,
                completed_sessions=len(records), incomplete_sessions=incomplete,
                available_panels=sum(len(r["pages"])-1 for r in records), valid_panels=len(data),
                exclusions=excluded, anchors=anchor_report(key["panels"], anchors),
                raw_receipt_sha256=file_sha256(originals / "receipt.json"))
    if not data:
        return dict(**base, independent_pairs=0, people=0, pair_weighted_effects=None, pairs=[])
    pairs, means = pair_means(data)
    people = sorted({person for person,_ in data})
    contrasts = effects(means.mean(0))
    n = len(pairs)
    draws = np.random.default_rng(20261121).integers(n, size=(10000,n))
    intervals = {}
    if n >= 2:
        intervals = dict(zip(NAMES, np.percentile(effects(means[draws].mean(1)), [2.5,97.5], axis=0).T.tolist()))
    per_pair = []
    secondary = defaultdict(dict)
    for pair, values in zip(pairs, means):
        cells = {f"{s}_{c}":float(v) for (s,c),v in zip(CELLS,values,strict=True)}
        scores = {(a["selector"],a["condition"]):a.get("metrics") for a in key["panels"][pair]}
        if all(scores[c] is not None for c in CELLS):
            for name in ("proxy","rule","render","ssl"):
                secondary[name][pair] = correlation(values, [scores[c][name] for c in CELLS])
        per_pair.append(dict(pair=pair, people=sum(p==pair for _,p in data), cells=cells,
                             effects=numbers(effects(values))))
    rho = {}
    for metric, by_pair in secondary.items():
        valid = [v for v in by_pair.values() if v is not None]
        bounds = None
        if len(valid) >= 2:
            sampled = np.random.default_rng(20261121).choice(valid, size=(10000,len(valid)), replace=True)
            bounds = np.percentile(sampled.mean(1), [2.5,97.5]).tolist()
        rho[metric] = dict(pairs=by_pair, valid=len(valid), mean=float(np.mean(valid)) if valid else None,
                           descriptive_interval=bounds)
    omitted = {}
    if len(people) > 1:
        for person in people:
            _, remaining = pair_means({k:v for k,v in data.items() if k[0] != person})
            omitted[person] = numbers(effects(remaining.mean(0)))
    return dict(**base,
                recording_groups={pair:key["groups"][pair] for pair in pairs} if expected_split == "final" else None,
                independent_pairs=n, people=len(people),
                cell_order=[list(c) for c in CELLS], pairs=per_pair,
                person_panels=[dict(person=p,pair=k,cells=row,effects=numbers(effects(np.array(row))))
                               for (p,k),row in sorted(data.items())],
                pair_weighted_effects=numbers(contrasts), descriptive_95=intervals,
                h3_reference_points=-5., h3_distance_points=float(contrasts[2]+5),
                pair_effect_range=dict(zip(NAMES,np.stack((effects(means).min(0),effects(means).max(0)),axis=1).tolist())),
                leave_one_person_out=omitted, secondary_spearman=rho)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("originals", type=Path)
    parser.add_argument("key", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--split", choices=("final", "development"), required=True)
    args = parser.parse_args()
    result = analyse(args.originals, args.key, args.split)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
