"""Run the PolicyEngine baseline and each reform for one calendar year.

Writes outputs/year_<YEAR>.json: budgetary impact (policyengine's
federal/state/unattributed partition), and baseline and reform totals for
the component variables compared with Fiscal Lab's lines.

Run one year per process, under the heavy-run wrapper:
    heavy_run.sh fiscal-lab-2030 uv run python scripts/run_year.py 2030
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import resource
import sys
import time
import weakref

import numpy as np
import pandas as pd
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import policyengine as pe  # noqa: E402
from policyengine.core import Simulation  # noqa: E402
from policyengine.outputs import Aggregate, AggregateType  # noqa: E402
from policyengine.tax_benefit_models.us.analysis import (  # noqa: E402
    calculate_budgetary_impact,
    configure_budgetary_impact_variables,
)

from fiscal_lab_comparison.reforms import REFORMS  # noqa: E402

# A reform runs in a year only if it changes some parameter in force that
# year. Years before a reform's first change are identical to baseline by
# construction; scripts/check_reforms.py asserts that on parameter values.
FIRST_YEAR = {"hr4849_coverage": 2027, "hr1428_poverty_line": 2030}

# Component variables: dollars (sums) and people (sums of booleans).
DOLLARS = [
    "aca_ptc",  # every eligible filer, before take-up
    "assigned_aca_ptc",  # aca_ptc times take-up: what household_health_benefits counts
    "used_aca_ptc",  # also capped at the selected plan's premium, for units that pay one
    "medicaid_cost",
    "medicaid_federal_cost",
    "medicaid_state_cost",
    "chip",
    "chip_federal_cost",
    "chip_state_cost",
    "msp_federal_cost",
    "basic_health_program",
    "federal_benefit_cost",
    "state_benefit_cost",
    "snap",
    "school_meal_net_subsidy",
    "wic",
    "income_tax",
    "state_income_tax",
    "employee_payroll_tax",
    "household_tax",
    "household_benefits",
]
PEOPLE = [
    "medicaid_enrolled",
    "chip_enrolled",
    "person_receives_aca",
    "basic_health_program_enrolled",
]
# People counted as "Marketplace, subsidized": person_receives_aca in tax units
# whose credit, after the cap at the enrolled plan's premium, is positive.
# person_receives_aca alone also counts people with a $0 credit.
SUBSIDIZED = {
    "name": "person_receives_aca_with_credit",
    "variable": "person_receives_aca",
    "filter_variable": "used_aca_ptc",
    "filter_variable_geq": 0.01,
}


# A reform simulation builds a second, baseline-policy simulation (core's
# "baseline" branch) for one formula: medicaid_slcsp_state_denominator reads
# the baseline's state Medicaid enrollment to price the reform's enrollees
# (policyengine_us/variables/gov/hhs/medicaid/costs/
# medicaid_slcsp_state_denominator.py). Computing it there pulls Medicaid
# eligibility and the federal income tax chain into memory a second time.
# The baseline process computes the same variable with the same policy and
# inputs, so it saves the values and each reform sets them as an input on
# that branch, which then computes nothing. runs/memory-review in the
# comparison notes has the code trace.
DENOMINATOR = "medicaid_slcsp_state_denominator"


def denominator_file(out_dir: Path, year: int) -> Path:
    # Person ids and values: kept out of git (*.npz in .gitignore).
    return out_dir / f"year_{year}" / f"baseline.{DENOMINATOR}.npz"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inject_baseline_denominator(saved: pd.Series, record: dict) -> None:
    """Set the baseline process's denominator as an input on the reform's
    baseline branch as policyengine builds it, and record which variables the
    branch is asked for (expected: the denominator alone)."""
    from policyengine.tax_benefit_models.us.model import PolicyEngineUSLatest

    original = PolicyEngineUSLatest._build_simulation_from_dataset

    def build(self, microsim, dataset, system):
        renames = original(self, microsim, dataset, system)
        if microsim.branch_name == "baseline":
            values = saved.reindex(microsim.populations["person"].ids).to_numpy()
            if np.isnan(values).any():
                raise SystemExit(f"baseline {DENOMINATOR} missing for {int(np.isnan(values).sum())} people")
            microsim.set_input(DENOMINATOR, dataset.year, values)
            record["persons"].append(len(values))
            # Count on the class with an identity check, not on the instance: a
            # branch cloned from this one would copy an instance attribute.
            # A weak reference, so the count keeps nothing alive after run().
            branch = weakref.ref(microsim)
            cls = type(microsim)
            calculate = cls.calculate

            def counted(self, variable_name, *args, **kwargs):
                if self is branch():
                    record["requested"][variable_name] = record["requested"].get(variable_name, 0) + 1
                return calculate(self, variable_name, *args, **kwargs)

            cls.calculate = counted
        return renames

    PolicyEngineUSLatest._build_simulation_from_dataset = build


def extra_variables() -> dict[str, list[str]]:
    # The module's own system, not a second CountryTaxBenefitSystem().
    from policyengine_us.system import system

    variables = system.variables
    by_entity: dict[str, list[str]] = {}
    for name in DOLLARS + PEOPLE:
        by_entity.setdefault(variables[name].entity.key, []).append(name)
    return by_entity


def totals(simulation: Simulation) -> dict[str, float]:
    out = {}
    for name in DOLLARS + PEOPLE:
        agg = Aggregate(simulation=simulation, variable=name, aggregate_type=AggregateType.SUM)
        agg.run()
        out[name] = float(agg.result)
    return out


def bundle_provenance() -> dict:
    manifest_path = Path(metadata.distribution("policyengine").locate_file("policyengine/data/bundle/manifest.json"))
    us = json.loads(manifest_path.read_text())["data_releases"]["us"]
    return {k: us.get(k) for k in ("default_dataset", "build_id")}


def rss_gb() -> float:
    # ru_maxrss is bytes on macOS.
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2)


def log(message: str) -> None:
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {message} (peak rss {rss_gb()} GB)", flush=True)


# A defaults-only run (memory measurement) records these default US outputs:
# five of the seven variables calculate_budgetary_impact reads
# (tax_benefit_models/us/analysis.py; federal_benefit_cost and
# state_benefit_cost are not default outputs), plus net income and SNAP.
DEFAULT_TOTALS = [
    "household_tax",
    "household_benefits",
    "income_tax",
    "employee_payroll_tax",
    "state_income_tax",
    "household_net_income",
    "snap",
]


def fingerprint(simulation: Simulation, year_file: Path | None) -> dict:
    """What every simulation for a year must share for reform-minus-baseline
    sums from separate processes to be valid."""
    out = {"year_file_sha256": None, "household_weight_sum": None, "person_weight_sum": None}
    if year_file is not None and year_file.exists():
        out["year_file_sha256"] = file_sha256(year_file)
    try:
        data = simulation.output_dataset.data
        out["household_weight_sum"] = float(np.asarray(data.household["household_weight"], dtype=float).sum())
        out["person_weight_sum"] = float(np.asarray(data.person["person_weight"], dtype=float).sum())
    except Exception as exc:  # a measurement run must still write its numbers
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def repo_provenance() -> dict:
    """The commit this run's code came from, and whether the files a run depends on differed from it."""
    import subprocess

    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True).stdout.strip()

    run_paths = ("scripts/run_year.py", "fiscal_lab_comparison", "pyproject.toml", "uv.lock")
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain", "--untracked-files=no", "--", *run_paths))}


SMOKE_DIR = ROOT / "data" / "microcosm" / "smoke"


def subsample(dataset, households: int, seed: int = 0):
    """The year's dataset cut to a random set of whole households, saved under
    data/microcosm/smoke/, for a fast check of the output path (--sample)."""
    from microdf import MicroDataFrame
    from policyengine.tax_benefit_models.us.datasets import PolicyEngineUSDataset, USYearData

    d = dataset.data
    ids = pd.DataFrame(d.household)["household_id"].to_numpy()
    keep = set(np.random.default_rng(seed).choice(ids, size=min(households, len(ids)), replace=False).tolist())
    person = pd.DataFrame(d.person)
    person = person[person["person_household_id"].isin(keep)]
    frames = {"person": person}
    for entity in ("household", "tax_unit", "spm_unit", "family", "marital_unit"):
        frame = pd.DataFrame(getattr(d, entity))
        frames[entity] = frame[frame[f"{entity}_id"].isin(set(person[f"person_{entity}_id"]))]
    data = USYearData(
        **{k: MicroDataFrame(v.reset_index(drop=True), weights=f"{k}_weight") for k, v in frames.items()}
    )
    sample = PolicyEngineUSDataset(
        id=f"{dataset.id}-sample{households}",
        name=f"{dataset.name} sample",
        description=f"{households} households of {dataset.name}",
        filepath=str(SMOKE_DIR / f"sample_{dataset.year}.h5"),
        year=dataset.year,
        data=data,
        metadata=dict(dataset.metadata),
    )
    sample.save()
    return sample


def run_single(year: int, sim_name: str, defaults_only: bool, out_dir: Path, sample: int | None = None) -> None:
    """One simulation per process: 'baseline' or one reform. With `sample`,
    the same steps on that many households (a smoke test; out_dir must not be
    outputs/)."""
    if sample and out_dir.resolve() == (ROOT / "outputs").resolve():
        raise SystemExit("--sample writes a smoke test; pass --out somewhere other than outputs/")
    path = out_dir / f"year_{year}" / f"{sim_name}{'.defaults' if defaults_only else ''}.json"
    if path.exists():
        print(f"{path} exists; skipping")
        return
    denominator_path = denominator_file(out_dir, year)
    if sim_name != "baseline" and not denominator_path.exists():
        raise SystemExit(f"{denominator_path} missing: run this year's baseline into {out_dir} first")
    started = time.time()
    datasets = pe.us.ensure_datasets(years=[year], data_folder=str(ROOT / "data" / "microcosm"))
    dataset = next(iter(datasets.values()))
    year_files = sorted((ROOT / "data" / "microcosm").glob(f"*_year_{year}.h5"))
    year_sha = file_sha256(year_files[0]) if year_files else None
    if sample:
        dataset = subsample(dataset, sample)
    log("dataset ready")
    kwargs = {"dataset": dataset, "tax_benefit_model_version": pe.us.model}
    if not defaults_only:
        kwargs["extra_variables"] = extra_variables()
        if sim_name == "baseline":
            kwargs["extra_variables"].setdefault("person", []).append(DENOMINATOR)
    injection = None
    if sim_name != "baseline":
        kwargs["policy"] = REFORMS[sim_name]()
        # The reform dict holds plain values; free the parameter tree built to make it.
        from fiscal_lab_comparison.reforms import _baseline_parameters

        _baseline_parameters.cache_clear()
        gc.collect()
        with np.load(denominator_path) as saved:
            if str(saved["year_file_sha256"]) != year_sha or int(saved["sample"]) != (sample or 0):
                raise SystemExit(f"{denominator_path} comes from another year file or sample")
            by_id = pd.Series(saved["value"], index=saved["person_id"])
        injection = {"file": denominator_path.name, "persons": [], "requested": {}}
        inject_baseline_denominator(by_id, injection)
    sim = Simulation(**kwargs)
    t = time.time()
    sim.ensure()
    sim_seconds = round(time.time() - t, 1)
    log(f"{sim_name} simulation done")
    if injection is not None and len(injection["persons"]) != 1:
        raise SystemExit(f"denominator injection ran {len(injection['persons'])} times, expected once")
    denominator = None
    if sim_name == "baseline" and not defaults_only:
        person = pd.DataFrame(sim.output_dataset.data.person)
        values = person[DENOMINATOR].to_numpy()
        denominator_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_npz = denominator_path.with_name(denominator_path.name + ".tmp")
        with open(tmp_npz, "wb") as f:
            np.savez(f, person_id=person["person_id"].to_numpy(), value=values, year_file_sha256=year_sha, sample=sample or 0)
        tmp_npz.replace(denominator_path)
        # A state total repeated for each person: at most one value per state.
        denominator = {"file": denominator_path.name, "persons": len(values), "distinct_values": int(np.unique(values).size)}
        del person
    names = DEFAULT_TOTALS if defaults_only else DOLLARS + PEOPLE
    # Each total is computed on its own, so one failure after an hour's
    # simulation keeps the others (written to <sim>.partial.json, which the
    # runner's skip check ignores) and names the one that failed.
    sums, errors = {}, {}
    for name in names:
        try:
            agg = Aggregate(simulation=sim, variable=name, aggregate_type=AggregateType.SUM)
            agg.run()
            sums[name] = float(agg.result)
        except Exception as exc:  # noqa: BLE001 - recorded and fails the process below
            errors[name] = f"{type(exc).__name__}: {exc}"
    if not defaults_only:
        try:
            agg = Aggregate(
                simulation=sim,
                variable=SUBSIDIZED["variable"],
                aggregate_type=AggregateType.SUM,
                filter_variable=SUBSIDIZED["filter_variable"],
                filter_variable_geq=SUBSIDIZED["filter_variable_geq"],
            )
            agg.run()
            sums[SUBSIDIZED["name"]] = float(agg.result)
        except Exception as exc:  # noqa: BLE001
            errors[SUBSIDIZED["name"]] = f"{type(exc).__name__}: {exc}"
    result = {
        "year": year,
        "simulation": sim_name,
        "defaults_only": defaults_only,
        "versions": {p: metadata.version(p) for p in ("policyengine", "policyengine-us", "policyengine-core")},
        "dataset": {"id": dataset.id, "year": dataset.year},
        "bundle": bundle_provenance(),
        "repo": repo_provenance(),
        "fingerprint": fingerprint(sim, year_files[0] if year_files else None),
        "include_health_benefits_in_net_income": bool(
            pe.us.model.get_parameter("gov.simulation.include_health_benefits_in_net_income")._core_param(f"{year}-01-01")
        ),
        "totals": sums,
        "timing_seconds": {"simulation": sim_seconds, "all": round(time.time() - started, 1)},
        "peak_rss_gb": rss_gb(),
        "year_file_bytes": sum(f.stat().st_size for f in year_files),
    }
    if sample:
        result["sample_households"] = sample
    if denominator is not None:
        result["denominator_saved"] = denominator
    if injection is not None:
        result["denominator_injected"] = {"file": injection["file"], "persons": injection["persons"][0], "baseline_branch_requests": injection["requested"]}
    if errors:
        result["errors"] = errors
        path = path.with_name(path.stem + ".partial.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result, indent=1))
    tmp.replace(path)
    # Simulation.ensure() saves its output dataset next to the year file; the
    # totals are in the JSON now, so remove it (the host is short of disk).
    output_file = getattr(sim.output_dataset, "filepath", None)
    if output_file and Path(output_file).exists() and Path(output_file).resolve() not in {f.resolve() for f in year_files}:
        result_bytes = Path(output_file).stat().st_size
        Path(output_file).unlink()
        print(f"removed output dataset {output_file} ({result_bytes} bytes)", flush=True)
    if sample:
        (SMOKE_DIR / f"sample_{year}.h5").unlink(missing_ok=True)
    print(json.dumps({k: result[k] for k in ("year", "simulation", "defaults_only", "timing_seconds", "peak_rss_gb", "year_file_bytes", "fingerprint")}, indent=1))
    if errors:
        raise SystemExit(f"{len(errors)} total(s) failed; partial totals in {path}: {errors}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int)
    parser.add_argument("--out", default=str(ROOT / "outputs"))
    parser.add_argument("--keep-year-file", action="store_true")
    parser.add_argument(
        "--reforms",
        nargs="*",
        default=list(REFORMS),
        help="reforms to run in this process; results merge into the year's JSON, so one "
        "reform per process keeps memory to the baseline plus one reform",
    )
    parser.add_argument("--sim", help="run one simulation only: 'baseline' or a reform name")
    parser.add_argument("--defaults-only", action="store_true", help="with --sim: policyengine's default outputs only (memory measurement)")
    parser.add_argument("--sample", type=int, help="with --sim: run on this many households (smoke test of the output path)")
    args = parser.parse_args()
    year = args.year
    if args.sim:
        if args.sim != "baseline" and args.sim not in REFORMS:
            raise SystemExit(f"unknown simulation {args.sim!r}")
        run_single(year, args.sim, args.defaults_only, Path(args.out), args.sample)
        return
    out_path = Path(args.out) / f"year_{year}.json"
    wanted = [name for name in args.reforms if year >= FIRST_YEAR[name]]
    previous = json.loads(out_path.read_text()) if out_path.exists() else None
    if previous is not None:
        wanted = [name for name in wanted if name not in previous["reforms"]]
        if not wanted:
            print(f"{out_path} already has {sorted(previous['reforms'])}; skipping")
            return

    started = time.time()
    datasets = pe.us.ensure_datasets(years=[year], data_folder=str(ROOT / "data" / "microcosm"))
    dataset = next(iter(datasets.values()))
    extras = extra_variables()
    log("dataset ready")

    result = {
        "year": year,
        "versions": {p: metadata.version(p) for p in ("policyengine", "policyengine-us", "policyengine-core")},
        "dataset": {"id": dataset.id, "year": dataset.year},
        "bundle": bundle_provenance(),
        "baseline": None,
        "reforms": {},
        "timing_seconds": {},
    }

    baseline = Simulation(dataset=dataset, tax_benefit_model_version=pe.us.model, extra_variables=extras)
    t = time.time()
    baseline.ensure()
    result["baseline"] = totals(baseline)
    result["timing_seconds"]["baseline"] = round(time.time() - t, 1)
    log("baseline done")
    if previous is not None:
        # The baseline is deterministic; a merge must see the same one.
        for key in ("versions", "dataset", "bundle"):
            if previous[key] != result[key]:
                raise SystemExit(f"{out_path}: {key} differs from this run; not merging")
        for name, value in result["baseline"].items():
            old = previous["baseline"].get(name)
            if old is None or abs(old - value) > 1e-6 * max(1.0, abs(value)):
                raise SystemExit(f"{out_path}: baseline {name} {old} != {value}; not merging")
        result["reforms"] = previous["reforms"]
        result["timing_seconds"] = {**previous["timing_seconds"], **result["timing_seconds"]}

    for name in wanted:
        sim = Simulation(
            dataset=dataset,
            tax_benefit_model_version=pe.us.model,
            policy=REFORMS[name](),
            extra_variables=extras,
        )
        configure_budgetary_impact_variables(baseline, sim)
        t = time.time()
        sim.ensure()
        budget = calculate_budgetary_impact(baseline, sim)
        result["reforms"][name] = {
            "budgetary_impact": {
                "total": budget.total,
                "federal": budget.federal,
                "state": budget.state,
                "unattributed": budget.unattributed,
            },
            "totals": totals(sim),
        }
        result["timing_seconds"][name] = round(time.time() - t, 1)
        del sim, budget
        gc.collect()
        log(f"{name} done")

    result["timing_seconds"]["all_this_process"] = round(time.time() - started, 1)
    result["peak_rss_gb"] = max(rss_gb(), (previous or {}).get("peak_rss_gb", 0))
    year_files = sorted((ROOT / "data" / "microcosm").glob(f"*_year_{year}.h5"))
    result["year_file_bytes"] = max(sum(f.stat().st_size for f in year_files), (previous or {}).get("year_file_bytes", 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result, indent=1))
    tmp.replace(out_path)
    # The year file is rebuilt from the certified source on demand. Remove it once
    # every reform for the year is in, so a full run keeps at most one on disk.
    done = set(result["reforms"]) >= {n for n in REFORMS if year >= FIRST_YEAR[n]}
    if done and not args.keep_year_file:
        for f in year_files:
            f.unlink()
    print(json.dumps({k: result[k] for k in ("year", "versions", "dataset", "timing_seconds", "peak_rss_gb", "year_file_bytes")}, indent=1))


if __name__ == "__main__":
    main()
