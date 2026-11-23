"""Read historical September training contracts without rebuilding their caches."""

import json
from pathlib import Path

import torch

from src.evaluation.all_models_control_study import _load_control_model
from src.evaluation.comparison import Comparison, Evaluator, raw_result, save_comparison
from src.evaluation.four_model_listening_study import DEFAULT_V2_DATASET, MODEL_RUNS
from src.evaluation.ml_control_study import _file_sha256
from src.evaluation.nontrivial_model_examples import _load_variable_tcn
from src.artifact_paths import artifact_path
from src.ml.data import FeatureControlDataset, _load_cached_vocal_bridge
from src.ml.inference_contract import fixed_preview_renderer_options, load_fixed_inference_contract
from src.ml.variable_data import VariableFeatureDataset
from src.ml.variable_waveform_cache import build_variable_cache_loader


FAMILIES = dict(zip(("R1", "R2", "R3", "R4"), (
    "time_shared_mlp_v1", "vocal_time_shared_mlp_v2", "tcn_bilstm_transition_control_v1",
    "variable_tcn_bilstm_transition_control_v1",
)))
RUNS = Path("output/training_runs")
VARIABLE_CACHE = Path("output/ml_cache/variable_bridge_waveform_v2/prive_scantraxx_extension_run02_wandb_full_20260926")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pair_of(example):
    return tuple(example[role + "_track"]["sha256"] for role in ("source", "target"))


class NativeSplit:
    def __init__(self, dataset, limit, vocal_records=None, indexed=None):
        self.data = dataset
        self.examples = dataset.examples[:limit]
        self.vocal_records = vocal_records
        self.indexed = indexed

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, index):
        example = self.examples[index]
        eid = example["example_id"]
        if self.vocal_records is None:
            item = self.data[index]
            directory = Path(item["waveform_cache_directory"])
            meta = load_json(directory / "manifest.json")
            if self.indexed is not None:
                record = self.indexed[eid]
                if (_file_sha256(directory / "manifest.json") != record["manifest_sha256"]
                        or meta["waveforms"]["file_sha256"] != record["waveforms_sha256"]):
                    raise ValueError(f"Waveform differs from sealed index for {eid}")
        else:
            # R2 binds exact cache manifests, including the stem extractor. Reading
            # the trained waveforms avoids a fresh, potentially different separation.
            record = self.vocal_records[eid]
            path = artifact_path(record["path"])
            if _file_sha256(path) != record["sha256"]:
                raise ValueError(f"Waveform manifest hash differs for {eid}")
            directory = path.parent
            cache = _load_cached_vocal_bridge(directory, {
                "example_id": eid, "candidate_id": example["candidate_id"],
                "training_sample_rate": 11025, "render_sample_rate": 44100,
                "source_sha256": pair_of(example)[0], "target_sha256": pair_of(example)[1],
            })
            if cache is None:
                raise ValueError(f"Invalid bound vocal cache for {eid}")
            meta = cache.manifest
            item = {k: torch.from_numpy(getattr(cache, k)) for k in (
                "source_audio", "target_audio", "source_vocal_audio", "target_vocal_audio",
            )}
            item.update({k: torch.from_numpy(getattr(self.data, k)[index])
                         for k in ("features_a", "features_b", "global_features")})
        return {
            **item, "example_id": eid, "candidate_id": example["candidate_id"],
            "split": example["split"], "pair": pair_of(example),
            "sample_rate": meta["training_sample_rate"], "transition_length_bars": example["transition_length_bars"],
            "geometry": {
                "cache_manifest": str(directory / "manifest.json"),
                "cache_manifest_sha256": _file_sha256(directory / "manifest.json"),
                "window": meta.get("geometry", meta.get("alignment", {}).get("raw_windows")),
            },
        }


def native_setup(profile, bars, run, dataset_path, cache_root, limit):
    manifest = load_json(run / "manifest.json")
    contract = manifest["contract"]
    variable = profile == "R4"
    family = contract.get("model_name") if variable else contract["model"]["name"]
    if family != FAMILIES[profile]:
        raise ValueError(f"{profile} cannot evaluate {family}")
    dataset_path = Path(dataset_path or (DEFAULT_V2_DATASET if variable else artifact_path(contract["dataset"]["path"])))
    dataset_file = dataset_path / "manifest.json"
    dataset = load_json(dataset_file)
    renderer = contract["renderer"]
    cfg = Comparison(profile, bars, renderer["sample_rate"], renderer["lowpass_kernel_size"],
                     renderer["lowpass_cutoff_hz"], renderer.get("midpass_cutoff_hz", 3500.),
                     contract["model"]["config"]["increment_logit_bound"],
                     contract["model"]["config"].get("maximum_vocal_ducking", 0.75))
    splits = {}
    if variable:
        model, provenance, _ = _load_variable_tcn(run, dataset_path)
        if (renderer["name"] != "DifferentiableVocalAwareRenderer" or
                contract["objective_name"] != "objective_v5_time_normalized_variable_tcn_bilstm_v1"):
            raise ValueError("Incompatible variable renderer or objective")
        cache = Path(cache_root or VARIABLE_CACHE)
        for name, field in (("index", "waveform_cache_index_sha256"),
                            ("manifest", "waveform_cache_root_manifest_sha256")):
            if _file_sha256(cache / f"{name}.json") != contract[field]:
                raise ValueError(f"Variable cache {name} differs from run")
        index = load_json(cache / "index.json")
        entries = {row["example_id"]: row for row in index["entries"]}
        loader = build_variable_cache_loader(dataset_path, cache_root=cache)
        for split in ("train", "validation"):
            accepted = {key for key, row in entries.items()
                        if row["split"] == split and row["transition_length_bars"] == bars}
            data = VariableFeatureDataset(dataset_path, bars, split, waveform_loader=loader,
                                          include_example_ids=accepted)
            if set(data.example_ids) != accepted:
                raise ValueError(f"Variable index and {split} shard disagree")
            splits[split] = NativeSplit(data, limit, indexed=entries)
        evaluator = Evaluator(cfg)
    else:
        inputs = load_fixed_inference_contract(contract, transition_bars=bars)
        fixed_preview_renderer_options(contract, sample_rate=cfg.sample_rate)
        loaded = _load_control_model(run, dataset, dataset_file)
        model, provenance = loaded.model, loaded.provenance
        objective = contract["objective"]
        if objective["version"] != (5 if cfg.vocal else 4) or objective["energy_frames"] != cfg.points:
            raise ValueError("Incompatible fixed objective version or frame count")
        evaluator = Evaluator(cfg, objective["config"])
        for split in ("train", "validation"):
            options = {"waveform_cache_root": cache_root} if cache_root else {}
            data = FeatureControlDataset(dataset_path, split, **options)
            records = None
            if inputs.waveform_vocals:
                if cache_root is not None:
                    raise ValueError("R2 uses exact waveform paths bound in its training manifest")
                rows = contract["dataset"]["vocal_waveform_cache_manifests"][split]
                records = {r["example_id"]: r for r in rows}
                if set(records) != set(data.example_ids):
                    raise ValueError(f"R2 waveform population differs from {split}")
            splits[split] = NativeSplit(data, limit, records)
    protocol = {
        **evaluator.protocol(), "run_id": manifest["run_id"], "run_directory": str(run),
        "run_manifest_sha256": _file_sha256(run / "manifest.json"),
        "checkpoint_sha256": manifest["files"]["best_checkpoint"]["sha256"],
        "checkpoint_epoch": provenance["checkpoint_epoch"], "seed": contract["training"]["seed"],
        "model": family, "model_config": contract["model"]["config"],
        "dataset_id": dataset["dataset_id"], "dataset_manifest_sha256": _file_sha256(dataset_file),
        "feature_protocol": dataset["feature_protocol_version"], "normalization": dataset["normalization"],
        "feature_vocal_backend": dataset["vocal_backend"], "feature_vocal_model": dataset["vocal_model"],
        "waveform_vocals": ("dataset_v2_index_bound_stems" if variable else
                            contract.get("waveform_cache") if cfg.vocal else None),
        "run_renderer": renderer,
        "control_initialization": contract["model"]["config"].get("control_initialization", "legacy"),
    }
    return evaluator, model, splits, protocol


def diagnose(stage, args):
    run = args.run or RUNS / MODEL_RUNS[FAMILIES[args.profile]]
    evaluator, model, splits, protocol = native_setup(
        args.profile, args.bars, run, args.dataset, args.cache, args.limit,
    )
    train, validation = splits["train"], splits["validation"]
    if not len(validation):
        raise ValueError("Empty evaluation population")
    pairs = [pair_of(example) for example in train.examples]
    fixed = evaluator.optimize(train, pairs, steps=args.steps, fixed=True)
    equal = evaluator.equal_power()
    rows = []
    for index in range(len(validation)):
        item = validation[index]
        direct = evaluator.optimize([item], [item["pair"]], steps=args.steps, fixed=False)
        for condition, controls in (("E", equal), ("F", fixed), ("M", evaluator.learned(model, item)), ("D", direct)):
            _, row = raw_result(evaluator, item, condition, controls)
            rows.append(row)
    save_comparison(stage, {
        **protocol, "updates": args.steps, "limit_per_split": args.limit,
        "fit_train_ids": [e["example_id"] for e in train.examples],
        "train_pair_count": len(set(pairs)), "validation_examples": len(validation),
    }, rows)
