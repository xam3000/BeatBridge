"""Rebuild a producer root from complete, immutable pair manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def recover_variable_producer_root(
    partial_root_path,
    corpus_manifest_path,
    split_map_path,
    output_directory,
    *,
    supplemental_roots=(),
):
    """Publish a new root over complete pair files without mutating the partial root."""

    from src.features.variable_split import load_variable_split_authority
    from src.variable_producer import _write_json_atomic

    partial_root_path = Path(partial_root_path).resolve()
    corpus_manifest_path = Path(corpus_manifest_path).resolve()
    split_map_path = Path(split_map_path).resolve()
    output_directory = Path(output_directory)
    output_path = output_directory / "manifest.json"
    if output_directory.exists() and any(output_directory.iterdir()):
        raise FileExistsError(f"Recovery output must be new or empty: {output_directory}")

    partial = json.loads(partial_root_path.read_text(encoding="utf-8"))
    corpus = json.loads(corpus_manifest_path.read_text(encoding="utf-8"))
    split_authority = load_variable_split_authority(split_map_path, ())
    tracks_by_sha = {
        str(row["sha256"]).lower(): row
        for row in corpus.get("tracks", ())
    }
    source_rows = partial.get("sources", ())
    sources_by_sha = {
        str(row["source_audio_sha256"]).lower(): row
        for row in source_rows
    }
    if len(sources_by_sha) != len(source_rows):
        raise ValueError("Partial producer root repeats source audio SHAs")
    for audio_sha in sources_by_sha:
        if audio_sha not in tracks_by_sha:
            raise ValueError(f"Partial producer source is absent from corpus manifest: {audio_sha}")
        if split_authority.assignments.get(audio_sha) == "test":
            raise ValueError(f"Closed test source found in partial producer root: {audio_sha}")

    pair_root = partial_root_path.parent / "pairs"
    pair_paths = sorted(pair_root.rglob("manifest.json"))
    if not pair_paths:
        raise ValueError("Partial producer root contains no pair manifests")

    pairs_by_source = {}
    pair_records_by_path = {}
    supplemental_pair_paths = []

    def add_pair(pair_path, *, expected_request_sha256):
        pair_payload = json.loads(pair_path.read_text(encoding="utf-8"))
        source_sha = str(pair_payload.get("source_audio_sha256", "")).lower()
        target_sha = str(pair_payload.get("target_audio_sha256", "")).lower()
        split = pair_payload.get("split")
        if source_sha not in sources_by_sha:
            raise ValueError(f"Pair source is absent from partial producer root: {pair_path}")
        if source_sha not in tracks_by_sha or target_sha not in tracks_by_sha:
            raise ValueError(f"Pair audio SHA is absent from corpus manifest: {pair_path}")
        if split not in ("train", "validation"):
            raise ValueError(f"Pair is outside the open Train/Validation splits: {pair_path}")
        if split_authority.assignments.get(source_sha) != split:
            raise ValueError(f"Pair source split differs from frozen authority: {pair_path}")
        if split_authority.assignments.get(target_sha) != split:
            raise ValueError(f"Pair target split differs from frozen authority: {pair_path}")
        if pair_payload.get("producer_request_config_sha256") != expected_request_sha256:
            raise ValueError(f"Pair producer request SHA differs from its root: {pair_path}")
        pair_sha = _file_sha256(pair_path)
        candidate_payloads = pair_payload.get("candidate_generation", {}).get("candidates", ())
        candidate_counts = pair_payload.get("candidate_generation", {}).get(
            "generated_candidate_counts_by_length", {}
        )
        ranking_failures = pair_payload.get("candidate_ranking", {}).get("failures", ())
        pair_record = {
            "source_audio_sha256": source_sha,
            "target_audio_sha256": target_sha,
            "split": split,
            "status": "completed",
            "manifest_path": str(pair_path.resolve()),
            "pair_manifest_sha256": pair_sha,
            "selected_candidate_count": len(candidate_payloads),
            "generated_candidate_counts_by_length": candidate_counts,
            "ranking_failure_count": len(ranking_failures),
        }
        if len(candidate_payloads) > 0 and pair_payload.get("failures"):
            raise ValueError(f"Selected pair manifest also declares failures: {pair_path}")
        pairs_by_source.setdefault(source_sha, []).append(pair_record)
        pair_records_by_path[pair_path.resolve()] = pair_record

    for pair_path in pair_paths:
        add_pair(
            pair_path,
            expected_request_sha256=partial.get("producer_request_config_sha256"),
        )

    supplemental_root_records = []
    for supplemental_root_path in supplemental_roots:
        supplemental_root_path = Path(supplemental_root_path).resolve()
        supplemental = json.loads(supplemental_root_path.read_text(encoding="utf-8"))
        selected_count = 0
        for source in supplemental.get("sources", ()):
            for pair in source.get("pairs", ()):
                if pair.get("status") != "completed" or pair.get("split") != "validation":
                    continue
                supplemental_pair_path = (
                    supplemental_root_path.parent / pair["manifest_path"]
                ).resolve()
                if not supplemental_pair_path.is_file():
                    raise FileNotFoundError(
                        f"Supplemental pair manifest does not exist: {supplemental_pair_path}"
                    )
                if pair.get("pair_manifest_sha256") != _file_sha256(supplemental_pair_path):
                    raise ValueError(
                        f"Supplemental pair SHA differs: {supplemental_pair_path}"
                    )
                add_pair(
                    supplemental_pair_path,
                    expected_request_sha256=supplemental.get(
                        "producer_request_config_sha256"
                    ),
                )
                supplemental_pair_paths.append(supplemental_pair_path)
                selected_count += 1
        supplemental_root_records.append(
            {
                "path": str(supplemental_root_path),
                "sha256": _file_sha256(supplemental_root_path),
                "selected_validation_pair_count": selected_count,
                "producer_request_config_sha256": supplemental.get(
                    "producer_request_config_sha256"
                ),
            }
        )

    if set(pairs_by_source) != set(sources_by_sha):
        missing = sorted(set(sources_by_sha) - set(pairs_by_source))
        extra = sorted(set(pairs_by_source) - set(sources_by_sha))
        raise ValueError(f"Pair/source coverage differs (missing={len(missing)}, extra={len(extra)})")
    if any(not items for items in pairs_by_source.values()):
        raise ValueError("Every producer source must have a completed target pair")
    if any(
        len({pair["target_audio_sha256"] for pair in items}) != len(items)
        for items in pairs_by_source.values()
    ):
        raise ValueError("A source repeats the same target pair")

    for source in source_rows:
        for declared_pair in source.get("pairs", ()):
            declared_path = (partial_root_path.parent / declared_pair["manifest_path"]).resolve()
            rebuilt_pair = pair_records_by_path.get(declared_path)
            if rebuilt_pair is None:
                raise ValueError(f"Partial root references a missing pair manifest: {declared_path}")
            if declared_pair.get("pair_manifest_sha256") != rebuilt_pair["pair_manifest_sha256"]:
                raise ValueError(f"Partial root pair SHA differs: {declared_path}")

    recovered_sources = []
    for source in source_rows:
        source_sha = str(source["source_audio_sha256"]).lower()
        row = dict(source)
        row["pairs"] = pairs_by_source[source_sha]
        row["status"] = "completed"
        if source.get("status") != "completed":
            row["song_ranking"] = None
            row["song_ranking_recovered"] = False
        recovered_sources.append(row)

    recovered = dict(partial)
    recovered["sources"] = recovered_sources
    recovered["status"] = "completed_recovered_from_pair_manifests"
    recovered["failures"] = []
    recovered["recovery"] = {
        "method": "validated_pair_manifest_aggregation_v1",
        "source_partial_root": str(partial_root_path),
        "source_partial_root_sha256": _file_sha256(partial_root_path),
        "corpus_manifest_sha256": _file_sha256(corpus_manifest_path),
        "split_authority_file_sha256": _file_sha256(split_map_path),
        "pair_manifest_count": len(pair_paths),
        "supplemental_validation_pair_count": len(supplemental_pair_paths),
        "supplemental_roots": supplemental_root_records,
        "source_ranking_count_recovered": sum(
            source.get("status") != "completed" for source in source_rows
        ),
        "pair_paths_are_absolute": True,
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(output_path, recovered)
    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("partial_root")
    parser.add_argument("corpus_manifest")
    parser.add_argument("split_map")
    parser.add_argument("output_directory")
    parser.add_argument("--supplemental-root", action="append", default=[])
    args = parser.parse_args(argv)
    print(
        recover_variable_producer_root(
            args.partial_root,
            args.corpus_manifest,
            args.split_map,
            args.output_directory,
            supplemental_roots=args.supplemental_root,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
