r"""Check revision invariants against the saved pre-edit sources and study data.

Run from the repository root using .venv\Scripts\python.exe -X utf8 -B.
Reads no audio or test tensors; never opens an answer key as JSON.
"""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
THESIS = ROOT / "overleaf"


def active(text):
    return "\n".join(re.split(r"(?<!\\)%", line)[0] for line in text.splitlines())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    checks = {}
    before = zipfile.ZipFile(ROOT / "output/thesis_revision_20261111/sources_before.zip")
    current = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8")
               for p in THESIS.rglob("*.tex")}
    for name in ("meta.tex", "CGThesis.tex"):
        key = "overleaf/" + name
        checks["formal_active_source_unchanged:" + name] = (
            active(before.read(key).decode()).split() == active(current[key]).split()
        )
    for name in ("cg.cls", "bibliography.bib"):
        checks["unchanged:" + name] = (before.read("overleaf/" + name) == (THESIS / name).read_bytes())
    for name in ["02_relatedWork", "03_mainPart", "04_implementation", "05_results", "06_discussion"]:
        key = "overleaf/chapters/" + name + ".tex"
        old, new = before.read(key).decode(), current[key]
        pattern = r"\\begin\{(equation|align|lstlisting)\}.*?\\end\{\1\}"
        checks["math_and_listings_unchanged:" + name] = (
            [m.group(0) for m in re.finditer(pattern, old, re.S)]
            == [m.group(0) for m in re.finditer(pattern, new, re.S)]
        )
    citation_pattern = r"\\cite\w*\*?(?:\[[^]]*\])*\{([^}]+)\}"
    old_cites = {k for n in before.namelist() if n.endswith(".tex")
                 for k in re.findall(citation_pattern, active(before.read(n).decode()))}
    new_cites = {k for t in current.values() for k in re.findall(citation_pattern, active(t))}
    checks["citation_sets_unchanged"] = old_cites == new_cites
    all_text = "\n".join(current.values())
    checks["no_gui_or_todo_including_comments"] = not re.search(
        r"\bGUI\b|graphical|native interface|implementation-gui|TODO", all_text, re.I)
    checks["removed_empty_user_results"] = "results-user-evaluation" not in all_text
    checks["no_stale_missing_model_listening_claim"] = not re.search(
        r"models have no completed perceptual|controllers have no completed listening|"
        r"whose listening exports remain unrated", all_text, re.I)
    paths = re.findall(r"\\path\{([^}]+)\}", current["overleaf/chapters/A0_appendixA.tex"])
    checks["appendix_repository_paths_exist"] = all(
        (ROOT / p).exists() for p in paths if p.startswith(("docs/", "config/", "output/")))
    checks["appendix_run_roots_exist"] = all(
        (ROOT / "output/training_runs" / p).is_dir() for p in paths if p.startswith("prive_scantraxx_"))
    analysis_path = ROOT / "docs/LISTENING_STUDY_ANALYSE_20261106.json"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    study = ROOT / analysis["study_directory"]
    ratings = json.loads((study / "ratings.json").read_text(encoding="utf-8"))["ratings"]
    ranked = [row for row in ratings if all(v is not None for v in row["ranks"].values())]
    excluded = [row["pair_index"] for row in ratings if all(v is None for v in row["ranks"].values())]
    checks["19_explicit_five_way_ties_one_exclusion_11"] = (
        len(ratings) == 20 and len(ranked) == analysis["ranked_pair_count"] == 19
        and excluded == [11] and all(list(row["ranks"].values()) == [1] * 5 for row in ranked)
        and sum(len(row["ranks"]) for row in ranked) == analysis["valid_explicit_rank_count"] == 95)
    checks["study_input_hashes_match_analysis"] = all(
        digest(study / name) == sha for name, sha in analysis["input_sha256"].items())
    checks["study_records_100_previously_verified_audio_hashes"] = (
        analysis["audio_sha256_match_count"] == len(analysis["audio_sha256_checks"]) == 100)
    report = {"checks": checks, "all_passed": all(checks.values()),
              "scope": "Source invariants and existing study metadata; no audio or test tensor reads; "
                       "no answer-key content read; no new experiments or layout certification."}
    dest = ROOT / "docs/masterarbeit/revision_invariants_20261111.json"
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
