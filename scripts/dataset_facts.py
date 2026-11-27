"""Print the Microcosm source-file shares the README cites (aggregates only).

Reads the certified 2024 source file that run_year.py downloads
(populace_us_2024.h5, build populace-us-2024-spm-20260915) and prints
household-weighted shares of people: Medicaid take-up flags, employer coverage,
SNAP and premium tax credit take-up flags, immigration statuses, and school-age
children in the states that policyengine-us treats as having universal free
school meals. "Reporters" are people whose has_medicaid_health_coverage_at_interview
is true ("Person currently has Medicaid health coverage"). These use the 2024
file's weights, not a year file's uprated ones. No record leaves this script.

Run: uv run python scripts/dataset_facts.py [--h5 PATH]
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
H5 = (
    ROOT
    / "data/microcosm/releases/microcosm-us-2024-national/populace-us-2024-spm-20260915/populace_us_2024.h5"
)
# policyengine-us 2.2.2, gov/usda/school_meals/state_universal_free_meals.yaml: true, with no end date, for these.
UNIVERSAL_MEALS = {"CA", "CO", "MA", "ME", "MI", "MN", "NM", "NY", "VT"}
FIPS = {6: "CA", 8: "CO", 25: "MA", 23: "ME", 26: "MI", 27: "MN", 35: "NM", 36: "NY", 50: "VT"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--h5", type=Path, default=H5)
    args = parser.parse_args()
    warnings.filterwarnings("ignore")
    with pd.HDFStore(args.h5, "r") as store:
        person = store.select(
            "person",
            columns=[
                "person_household_id",
                "person_spm_unit_id",
                "person_tax_unit_id",
                "age",
                "has_medicaid_health_coverage_at_interview",
                "has_esi",
                "takes_up_medicaid_if_eligible",
                "immigration_status_str",
            ],
        )
        household = store.select("household", columns=["household_id", "household_weight", "state_fips"])
        spm = store.select("spm_unit", columns=["spm_unit_id", "takes_up_snap_if_eligible"])
        tax_unit = store.select("tax_unit", columns=["tax_unit_id", "takes_up_aca_if_eligible"])
        person_columns = list(store.select("person", stop=1).columns)
    p = person.merge(household, left_on="person_household_id", right_on="household_id", how="left")
    p = p.merge(spm, left_on="person_spm_unit_id", right_on="spm_unit_id", how="left")
    p = p.merge(tax_unit, left_on="person_tax_unit_id", right_on="tax_unit_id", how="left")
    if len(p) != len(person):
        raise SystemExit("a merge duplicated people")
    # A missing value would read as True under astype(bool).
    for col in ("household_weight", "state_fips", "takes_up_snap_if_eligible", "takes_up_aca_if_eligible",
                "has_medicaid_health_coverage_at_interview", "takes_up_medicaid_if_eligible", "has_esi", "age"):
        if p[col].isna().any():
            raise SystemExit(f"{col} is missing for some people")
    w = p["household_weight"]
    reported = p["has_medicaid_health_coverage_at_interview"].astype(bool)
    flagged = p["takes_up_medicaid_if_eligible"].astype(bool)
    esi = p["has_esi"].astype(bool)

    def share(mask, of) -> float:
        return w[mask & of].sum() / w[of].sum()

    print(f"People: {w.sum() / 1e6:.2f} M (2024 weights)")
    print(f"Medicaid reporters: {w[reported].sum() / 1e6:.2f} M; flagged to take up Medicaid: {share(flagged, reported):.4f}")
    print(f"Non-reporters: {w[~reported].sum() / 1e6:.2f} M; flagged: {share(flagged, ~reported):.4f}")
    print(f"Non-reporters with employer coverage: flagged {share(flagged, ~reported & esi):.4f}")
    by_state = (
        p[~reported].assign(fw=w[~reported] * flagged[~reported]).groupby("state_fips")[["fw", "household_weight"]].sum()
    )
    rate = by_state["fw"] / by_state["household_weight"]
    print(
        f"Non-reporters' flag rate by state: min {rate.min():.3f}, max {rate.max():.3f}, "
        f"states at 1.0: {(rate >= 1 - 1e-12).sum()} of {len(rate)}"
    )
    print(f"Medicaid reporters who also report employer coverage: {share(esi, reported):.4f}")
    everyone = w == w
    print(f"SNAP take-up flag, share of people: {share(p['takes_up_snap_if_eligible'].astype(bool), everyone):.4f}")
    print(f"Premium tax credit take-up flag (tax unit), share of people: {share(p['takes_up_aca_if_eligible'].astype(bool), everyone):.4f}")
    print("Immigration status, millions of people:")
    for status, weight in w.groupby(p["immigration_status_str"]).sum().sort_values(ascending=False).items():
        print(f"  {status}: {weight / 1e6:.2f}")
    print(f"Entry-year column in the person table: {'yes' if any('entry' in c for c in person_columns) else 'none'}")
    school_age = (p["age"] >= 5) & (p["age"] <= 17)
    universal = p["state_fips"].map(FIPS).isin(UNIVERSAL_MEALS)
    print(f"People aged 5-17 in the nine universal-free-meal states: {share(universal, school_age):.4f}")


if __name__ == "__main__":
    main()
