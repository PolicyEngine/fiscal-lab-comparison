"""Line up PolicyEngine's results with Fiscal Lab's published components.

Reads PolicyEngine totals from outputs/ (written by run_year.py) and Fiscal
Lab's figures from data/fiscal_lab/two_bills.json (written by
fetch_fiscal_lab.py). Writes results/comparison.md and results/comparison.csv,
which are kept out of git because they repeat Fiscal Lab's figures, and
tables/policyengine_*.csv, PolicyEngine's side alone, which are committed (in
the fiscal-year table's policyengine_cost_bn, a cost to the government is
positive, as in the line table).

Counting by fiscal year. PolicyEngine runs calendar years. Each line's
calendar-year change is counted by fiscal year with the rule that fits how the
program's change is timed (these rules are this comparison's choices, not
policyengine-us's):

- coverage lines (Medicaid and CHIP, premium tax credit, Basic Health Program,
  Medicare Savings Programs): FY t = 0.25 CY(t-1) + 0.75 CY t, the rule Fiscal
  Lab uses for its coverage model;
- SNAP, which runs on an October 1 cycle (snap_fpg reads the October 1
  guideline and the standard-deduction change starts October 1, 2030): the same
  rule, except that the first calendar year's change, mostly in October to
  December (inferred; not computed), goes wholly to the next fiscal year (broad-based
  categorical eligibility limits move to the new line from January to April in
  Maine, Massachusetts, Oregon and Washington);
- school meals, whose income guidelines apply to the school year from July 1
  (42 U.S.C. 1758(b)(1)(A)): PolicyEngine's calendar-year-t change, built on the
  year-t guideline, is read as school year t, and FY t = (1 - s) SY(t-1) + s SY
  t, where s = 1/6 is the share of school days in August and September (an
  assumption from a typical 180-day calendar).

A calendar year before a reform's first year is zero by construction (the
reform changes no parameter in force then).

Run: uv run python scripts/compare.py [--outputs DIR] [--results DIR] [--tables DIR]
(--tables defaults to tables/ only when --outputs is the default outputs/.)
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YEARS = list(range(2027, 2037))
# Also in run_year.py, which imports policyengine; facts.py imports this copy.
FIRST_YEAR = {"hr4849_coverage": 2027, "hr1428_poverty_line": 2030}
AUG_SEP_SCHOOL_DAY_SHARE = 1 / 6

MEDICAID_PRICE = (
    "PolicyEngine holds each state's Medicaid spending at its 2023 total and shares it among enrollees by a "
    "benchmark-premium index (age-rated, except family tiers in New York and Vermont) over the baseline's index-weighted "
    "enrollment, so the average price per enrollee has no medical-cost growth and rises only as baseline enrollment "
    "falls, and no price varies by eligibility group or other coverage"
)
CHIP_TAKEUP = "PolicyEngine counts every CHIP-eligible person as enrolled"
PTC_BASELINE = (
    "PolicyEngine's baseline holds the 2026 applicable percentages fixed for 2027-2036, while current law "
    "indexes them (2.15 to 10.22 percent in 2027), so it understates the gain below 400 percent of the line"
)
PTC_TAKEUP = (
    "PolicyEngine's line is the credit tax units use (used_aca_ptc), which only units carrying Microcosm's "
    "takes_up_aca_if_eligible flag and paying a premium receive"
)
NO_IMMIGRANT_RECORDS = (
    "Microcosm codes non-citizens only as permanent residents, undocumented immigrants, Cuban/Haitian entrants or DACA "
    "recipients and records no entry year, so the immigrant repeals reach no one"
)
FACTOR_1428_COVERAGE = (
    "Fiscal Lab's coverage model applies one factor by state (averaging 1.97) to every household; PolicyEngine applies "
    "1.97 everywhere, in every year"
)
FACTOR_1428_OWN_LINE = "Fiscal Lab uses each household's own line; PolicyEngine applies 1.97 everywhere"

# Each line: Fiscal Lab's Table 1 row label(s), the PolicyEngine variables whose
# reform-minus-baseline change is its counterpart, the fiscal-year rule, and
# whether the two rest on the same policy input.
LINES = {
    "hr4849_coverage": {
        "bill": "H.R. 4849",
        "lines": [
            {
                "label": "Federal Medicaid and CHIP spending",
                "fiscal_lab": ["Federal Medicaid and CHIP spending"],
                "pe": ["medicaid_federal_cost", "chip_federal_cost"],
                "fy": "coverage",
                "same_input": "no: PolicyEngine's change is the work-requirement repeal alone. Its baseline requirement is an "
                "annual test (survey hours, exemptions, or household MAGI of at least $6,960 a year, PolicyEngine's annual version "
                "of the $580-a-month income test in 42 CFR 435.552(f)) with no reporting or verification loss, in full from "
                "January 2027, so the repeal restores about 1.0 to 1.1 million people a year; "
                "Fiscal Lab's line also covers six-month redeterminations and immigrant limits. PolicyEngine does not encode "
                "the redeterminations or OBBBA's CHIP immigrant limit, and " + NO_IMMIGRANT_RECORDS + ". " + MEDICAID_PRICE
                + "; it prices the restored adults about a quarter to a third above its average enrollee, Fiscal Lab below "
                "its average. PolicyEngine's CHIP change is zero",
            },
            {
                "label": "Premium tax credits",
                "fiscal_lab": ["Premium tax credits for marketplace coverage"],
                "pe": ["used_aca_ptc"],
                "fy": "coverage",
                "same_input": "no, though the totals are close: Fiscal Lab's coverage model puts $132.2 billion on restoring "
                "immigrants' credits, and " + NO_IMMIGRANT_RECORDS + ". If that sum is inside this line, PolicyEngine is "
                "about 43 percent above Fiscal Lab on the rest (inferred), although " + PTC_BASELINE + "; the source of the "
                "gap is not identified. " + PTC_TAKEUP,
            },
            {
                "label": "Basic Health Program",
                "fiscal_lab": ["Basic Health Program"],
                "pe": ["basic_health_program"],
                "fy": "coverage",
                "same_input": "partly: the same frozen baseline applicable percentages. BHP eligibility excludes DACA "
                "recipients and undocumented immigrants in both runs, and Microcosm has no refugee, asylee, parolee or TPS "
                "records, so the Medicaid immigrant repeal moves no one into or out of BHP; PolicyEngine's BHP payment does "
                "not apply the credit's immigrant test, so the credit's immigrant repeal moves no BHP dollar. PolicyEngine's "
                "BHP enrollment is unchanged in every year. It models BHP in MN, NY (the Essential Plan), OR and DC and "
                "counts every eligible person as enrolled; Fiscal Lab does not publish its BHP base",
            },
            {
                "label": "Cost-sharing reductions",
                "fiscal_lab": ["Cost-sharing reductions"],
                "pe": None,
                "fy": "coverage",
                "same_input": "not modeled: PolicyEngine computes no cost-sharing reduction payments",
            },
            {
                "label": "Employer coverage tax exclusion",
                "fiscal_lab": ["The tax exclusion for employer coverage"],
                "pe": None,
                "fy": "coverage",
                "same_input": "not modeled: PolicyEngine moves no one out of employer coverage",
            },
        ],
        "coverage": [
            ("Medicaid and CHIP", ["medicaid_enrolled", "chip_enrolled"]),
            ("Marketplace, subsidized", ["person_receives_aca_with_credit"]),
        ],
    },
    "hr1428_poverty_line": {
        "bill": "H.R. 1428",
        "lines": [
            {
                "label": "Federal Medicaid and CHIP spending",
                "fiscal_lab": ["Federal Medicaid and CHIP spending"],
                "pe": ["medicaid_federal_cost", "chip_federal_cost"],
                "fy": "coverage",
                "same_input": "no: " + MEDICAID_PRICE + ", so it prices every new enrollee at the state's average for their index "
                "even when they keep employer coverage or Medicare, which pay first (42 U.S.C. 1396a(a)(25)). Microcosm's Medicaid take-up flag "
                "(takes_up_medicaid_if_eligible) is set for about 91 percent of people the file does not mark as having "
                "Medicaid (2024 weights; 51 to 100 percent by state), including people with employer coverage, who keep it. "
                + FACTOR_1428_COVERAGE + ", so PolicyEngine's enrollment gain stays flat; Fiscal Lab's declines, for reasons it does not publish. Fiscal "
                "Lab applies a 120 percent limit to people 65 and older in every state, PolicyEngine each state's own aged "
                "and disabled limit times 1.97. " + CHIP_TAKEUP,
            },
            {
                "label": "Premium tax credits",
                "fiscal_lab": ["Premium tax credits for marketplace coverage"],
                "pe": ["used_aca_ptc"],
                "fy": "coverage",
                "same_input": "partly: " + FACTOR_1428_COVERAGE + ". The credit's own income test reads the prior year's "
                "guideline, so it changes from 2031. In 2030 the credit falls because people become eligible for Medicaid, "
                "CHIP or (in MN, NY, OR and DC) the Basic Health Program, whose tests read the current year's line; "
                "eligibility alone ends the credit, so newly eligible people who do not take up Medicaid lose it too. From "
                "2031 the new line lowers applicable percentages and moves the 400 percent limit to 7.9 times today's line, "
                "and units that take up the credit claim more, so PolicyEngine's line rises while Fiscal Lab's falls (the "
                "credit summed over every eligible unit, aca_ptc, falls). " + PTC_TAKEUP,
            },
            {
                "label": "Basic Health Program",
                "fiscal_lab": ["Basic Health Program"],
                "pe": ["basic_health_program"],
                "fy": "coverage",
                "same_input": "partly: " + FACTOR_1428_COVERAGE + ". PolicyEngine models BHP in MN, NY (the Essential "
                "Plan), OR and DC. Every baseline enrollee's income falls under the new Medicaid limit, while BHP's own "
                "band moves up with the current year's line, so BHP enrollment falls on net. PolicyEngine counts every "
                "eligible person as enrolled; Fiscal Lab does not publish its BHP base",
            },
            {
                "label": "Medicare Savings Programs (federal Medicaid share)",
                "fiscal_lab": [
                    "Medicaid: Part B premiums for new Qualified Medicare Beneficiary and other Medicare Savings Program enrollees, federal share",
                    "Medicaid: cost sharing for new Qualified Medicare Beneficiaries, federal share",
                    # Fiscal Lab nets out people 65+ its coverage model already put in Medicaid.
                    "Less: premiums and cost sharing of people 65+ already in Fiscal Lab’s coverage model’s Medicaid run of the bill",
                ],
                "pe": ["msp_federal_cost"],
                "fy": "coverage",
                "same_input": "no: Fiscal Lab's line for a Medicare couple averages about 1.63 times today's line; PolicyEngine "
                "applies 1.97 to everyone and counts every eligible person as enrolled (no take-up step). PolicyEngine's MSP "
                "cost is zero for anyone in full Medicaid, so people H.R. 1428 moves into Medicaid count in the Medicaid line, "
                "much as Fiscal Lab's line nets out people its coverage model puts in Medicaid. PolicyEngine's "
                "fiscal-year rule puts three quarters of calendar 2030 in FY2030; Fiscal Lab's Medicare lines appear to "
                "start about April 2030 (inferred)",
            },
            {
                "label": "SNAP",
                "fiscal_lab": [
                    "SNAP: current participants, standard deduction at 8.31 percent of the household’s own line (no ramp)",
                    "SNAP: newly eligible households, with take-up ramp",
                ],
                "pe": ["snap"],
                "fy": "october",
                "same_input": "partly: " + FACTOR_1428_OWN_LINE + ". Fiscal Lab ramps take-up for newly eligible "
                "households; PolicyEngine fixes take-up at Microcosm's flags (takes_up_snap_if_eligible), with no ramp. "
                "PolicyEngine counts the change mostly from October 2030 (earlier for broad-based categorical eligibility in "
                "four states; the split was not computed); Fiscal Lab's yearly figures appear to start in January 2031 "
                "(inferred)",
            },
            {
                "label": "School meals",
                "fiscal_lab": [
                    "School meals, children outside community eligibility schools: category and meal-taking under the household’s line",
                    "School meals, CEP schools: free claim rises with the identified-student percentage",
                ],
                "pe": ["school_meal_net_subsidy"],
                "fy": "school_year",
                "same_input": "partly: " + FACTOR_1428_OWN_LINE + ". In the nine states with universal free school meals "
                "(CA, CO, MA, ME, MI, MN, NM, NY, VT), about a quarter of people aged 5-17 (2024 weights), PolicyEngine puts every "
                "student on the free tier, so H.R. 1428 changes no school-meal dollar there. PolicyEngine does not model "
                "community eligibility schools and counts everyone aged 5 to 17 as a student eating breakfast and lunch on "
                "all 180 school days (no meal-taking step)",
            },
            {
                "label": "Cost-sharing reductions",
                "fiscal_lab": ["Cost-sharing reductions"],
                "pe": None,
                "fy": "coverage",
                "same_input": "not modeled: PolicyEngine computes no cost-sharing reduction payments",
            },
            {
                "label": "Employer coverage tax exclusion",
                "fiscal_lab": ["The tax exclusion for employer coverage"],
                "pe": None,
                "fy": "coverage",
                "same_input": "not modeled: PolicyEngine moves no one out of employer coverage",
            },
        ],
        "coverage": [
            ("Medicaid and CHIP", ["medicaid_enrolled", "chip_enrolled"]),
            ("Marketplace, subsidized", ["person_receives_aca_with_credit"]),
        ],
    },
}

FINGERPRINT_KEYS = ("year_file_sha256", "household_weight_sum", "person_weight_sum")


def same(a: float, b: float) -> bool:
    """Equal up to floating-point summation order."""
    return abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1.0)


def load_pe(outputs: Path) -> dict[int, dict]:
    """Per year: baseline totals, reform totals, and the health flag.

    run_year.py --sim writes <outputs>/year_<Y>/<simulation>.json, one
    simulation per process. A reform-minus-baseline sum across processes is
    valid only on the same records and weights, so every simulation's
    fingerprint must match the baseline's.
    """
    if not outputs.is_dir():
        raise SystemExit(f"{outputs} is not a folder")
    runs: dict[int, dict] = {}
    for ydir in sorted(outputs.glob("year_*")):
        if not ydir.is_dir():
            continue
        sims = {}
        for path in sorted(ydir.glob("*.json")):
            if path.name.endswith((".defaults.json", ".partial.json")):
                continue  # memory measurements (default outputs only) and failed runs
            run = json.loads(path.read_text())
            name = run["simulation"]
            if path.stem != name:  # so one folder cannot hold two files for one simulation
                raise SystemExit(f"{path}: holds simulation {name!r}")
            if run.get("sample_households") or run.get("defaults_only"):
                raise SystemExit(f"{path}: a sample or defaults-only run, not a full one")
            sims[name] = run
        if "baseline" not in sims:
            continue
        ref = sims["baseline"]
        year = ref["year"]
        if ydir.name != f"year_{year}":
            raise SystemExit(f"{ydir}: the baseline's year is {year}")
        if any(ref["fingerprint"].get(key) is None for key in FINGERPRINT_KEYS):
            raise SystemExit(f"{ydir}: the baseline's fingerprint is incomplete")
        for name, run in sims.items():
            if run["year"] != year or run["dataset"]["year"] != year:
                raise SystemExit(f"{ydir}/{name}: year {run['year']}, dataset year {run['dataset']['year']}, not {year}")
            for key in FINGERPRINT_KEYS:
                if run["fingerprint"].get(key) != ref["fingerprint"].get(key):
                    raise SystemExit(f"{ydir}/{name}: {key} differs from the baseline's; not comparable")
            for key in ("versions", "bundle", "include_health_benefits_in_net_income"):
                if run[key] != ref[key]:
                    raise SystemExit(f"{ydir}/{name}: {key} differs from the baseline's; not comparable")
            # Same code: a clean checkout of one commit for every simulation of the year.
            repo = run.get("repo") or {}
            if repo.get("dirty") is not False or repo.get("commit") != (ref.get("repo") or {}).get("commit"):
                raise SystemExit(f"{ydir}/{name}: repo {repo} is not a clean run of the baseline's commit")
            # Same draws: neither bill touches payroll tax, so a difference means
            # the processes did not compute the same population.
            if not same(run["totals"]["employee_payroll_tax"], ref["totals"]["employee_payroll_tax"]):
                raise SystemExit(f"{ydir}/{name}: employee_payroll_tax differs from the baseline's; outputs not deterministic")
        # The memory measurement ran the same baseline with default outputs only:
        # every total the two share must match (household_net_income is recorded
        # only there).
        measured = ydir / "baseline.defaults.json"
        if measured.exists():
            defaults = json.loads(measured.read_text())["totals"]
            shared = sorted(set(defaults) & set(ref["totals"]))
            if not shared:
                raise SystemExit(f"{ydir}: baseline.defaults.json shares no total with baseline.json")
            for key in shared:
                if not same(ref["totals"][key], defaults[key]):
                    raise SystemExit(f"{ydir}: baseline {key} differs from baseline.defaults.json; outputs not deterministic")
        runs[year] = {
            "baseline": ref["totals"],
            "reforms": {name: run["totals"] for name, run in sims.items() if name != "baseline"},
            "include_health": ref["include_health_benefits_in_net_income"],
        }
    return runs


def change_by_cy(runs: dict[int, dict], reform: str, variables: list[str]) -> dict[int, float | None]:
    """Reform-minus-baseline change by calendar year; None where a year is missing."""
    out: dict[int, float | None] = {}
    for year in range(2026, 2037):
        if year < FIRST_YEAR[reform]:
            out[year] = 0.0
            continue
        run = runs.get(year)
        if run is None or reform not in run["reforms"]:
            out[year] = None
            continue
        r, b = run["reforms"][reform], run["baseline"]
        out[year] = sum(r[v] - b[v] for v in variables)
    return out


def to_fiscal_years(cy: dict[int, float | None], rule: str, first_year: int) -> dict[int, float | None]:
    fy: dict[int, float | None] = {}
    for t in YEARS:
        a, b = cy.get(t - 1), cy.get(t)
        if a is None or b is None:
            fy[t] = None
        elif rule == "coverage":
            fy[t] = 0.25 * a + 0.75 * b
        elif rule == "october":
            # The first calendar year's change, mostly in October-December, goes to the next fiscal year.
            if t == first_year:
                fy[t] = 0.0
            elif t == first_year + 1:
                fy[t] = a + 0.75 * b
            else:
                fy[t] = 0.25 * a + 0.75 * b
        elif rule == "school_year":
            s = AUG_SEP_SCHOOL_DAY_SHARE
            fy[t] = (1 - s) * a + s * b
        else:
            raise ValueError(rule)
    return fy


def partition(b: dict, r: dict, include_health: bool) -> dict[str, float]:
    """policyengine 6.20.3's calculate_budgetary_impact (tax_benefit_models/us/
    analysis.py), rebuilt from per-simulation totals. Positive = government better off."""
    d = lambda v: r[v] - b[v]  # noqa: E731
    total = d("household_tax") - d("household_benefits")
    if not include_health:
        total -= d("federal_benefit_cost") + d("state_benefit_cost")
    federal = d("income_tax") + d("employee_payroll_tax") - d("federal_benefit_cost")
    state = d("state_income_tax") - d("state_benefit_cost")
    return {"total": total, "federal": federal, "state": state, "unattributed": total - federal - state}


def fiscal_lab_line(fl_bill: dict, labels: list[str]) -> list[float]:
    rows = {r["label"]: r["values"] for r in fl_bill["t1"]["rows"]}
    missing = [label for label in labels if label not in rows]
    if missing:
        raise KeyError(f"Fiscal Lab rows not found: {missing}")
    return [sum(rows[label][i] for label in labels) for i in range(len(YEARS))]


def fmt(x: float | None, digits: int = 1) -> str:
    return "—" if x is None else f"{x:,.{digits}f}"


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outputs", type=Path, default=ROOT / "outputs", help="run_year.py's output folder")
    parser.add_argument("--results", type=Path, default=ROOT / "results", help="side-by-side tables (not committed)")
    parser.add_argument(
        "--tables", type=Path, help="PolicyEngine-only tables; default tables/ (committed) only with the default --outputs"
    )
    args = parser.parse_args()
    if args.tables is None:
        if args.outputs.resolve() != (ROOT / "outputs").resolve():
            raise SystemExit("with a non-default --outputs, give --tables too, so the committed tables/ stay as they are")
        args.tables = ROOT / "tables"

    fl = json.loads((ROOT / "data" / "fiscal_lab" / "two_bills.json").read_text())
    if fl["years"] != YEARS:
        raise SystemExit(f"Fiscal Lab years {fl['years']} != {YEARS}")
    runs = load_pe(args.outputs)
    if not runs:
        raise SystemExit(f"{args.outputs}: no year has a baseline")
    args.results.mkdir(parents=True, exist_ok=True)
    args.tables.mkdir(parents=True, exist_ok=True)

    csv_rows, pe_fy_rows, pe_coverage_rows = [], [], []
    incomplete = [
        f"{t} {reform}" for reform in LINES for t in YEARS
        if t >= FIRST_YEAR[reform] and (t not in runs or reform not in runs[t]["reforms"])
    ]
    md = [
        "# Line-by-line comparison",
        "",
        f"PolicyEngine calendar years with a baseline: {', '.join(map(str, sorted(runs)))}. "
        "Dollar figures are billions over fiscal years 2027–2036, as effects on the deficit (a cost is positive). "
        f"Fiscal Lab's figures are from its dashboard (built {fl['built']}). PolicyEngine's are reform-minus-baseline "
        "changes, counted by fiscal year as `scripts/compare.py` describes."
        + (f" A dash means a year is not run yet (missing: {', '.join(incomplete)})." if incomplete else ""),
        "",
    ]
    for reform, spec in LINES.items():
        fl_bill = fl["bills"][spec["bill"]]
        md += [f"## {spec['bill']}: {fl_bill['title']}", ""]
        md += ["| Line | Fiscal Lab | PolicyEngine | Same policy input? |", "|---|---:|---:|---|"]
        for line in spec["lines"]:
            if "|" in line["same_input"] or "\n" in line["same_input"]:
                raise ValueError(f"{line['label']}: a table cell cannot hold '|' or a newline")
            fl_values = fiscal_lab_line(fl_bill, line["fiscal_lab"])
            if line["pe"] is None:
                pe_fy = {t: None for t in YEARS}
                pe_cell = "not modeled"
            else:
                cy = change_by_cy(runs, reform, line["pe"])
                pe_fy = to_fiscal_years(cy, line["fy"], FIRST_YEAR[reform])
                pe_fy = {t: (None if v is None else v / 1e9) for t, v in pe_fy.items()}
                pe_cell = fmt(None if any(v is None for v in pe_fy.values()) else sum(pe_fy.values()))
            md.append(f"| {line['label']} | {fmt(sum(fl_values))} | {pe_cell} | {line['same_input']} |")
            for i, t in enumerate(YEARS):
                csv_rows.append(
                    {
                        "bill": spec["bill"],
                        "line": line["label"],
                        "fiscal_year": t,
                        "fiscal_lab_bn": round(fl_values[i], 3),
                        "policyengine_bn": None if pe_fy[t] is None else round(pe_fy[t], 3),
                        "same_input": line["same_input"],
                    }
                )
                if line["pe"] is not None:
                    pe_fy_rows.append(
                        {
                            "bill": spec["bill"],
                            "line": line["label"],
                            "policyengine_variables": " + ".join(line["pe"]),
                            "fiscal_year_rule": line["fy"],
                            "fiscal_year": t,
                            "policyengine_cost_bn": None if pe_fy[t] is None else round(pe_fy[t], 3),
                        }
                    )
        md.append("")
        compared = {label for line in spec["lines"] for label in line["fiscal_lab"]}
        left_out = [r for r in fl_bill["t1"]["rows"] if r["label"] not in compared]
        if left_out:
            md += ["Fiscal Lab lines outside this comparison (no PolicyEngine counterpart), billions:", ""]
            md += [f"- {r['label']}: {fmt(sum(r['values']))}" for r in left_out]
            md.append("")

        t3 = {r["label"]: r["values"] for r in fl_bill["t3"]["rows"]}
        md += [
            "Coverage change, millions of people, calendar years. Fiscal Lab's figures are average enrollment; "
            "PolicyEngine's are annual statuses, each person counted for the full year. PolicyEngine's subsidized "
            "Marketplace count is people in tax units with the dataset's take-up flag whose used credit is positive."
            + (" Fiscal Lab's likely includes immigrants whose credits PolicyEngine cannot reach (inferred), so close "
               "counts here are not agreement." if reform == "hr4849_coverage" else ""),
            "",
            "| Coverage | Source | " + " | ".join(map(str, YEARS)) + " |",
            "|---|---|" + "---:|" * len(YEARS),
        ]
        for label, variables in spec["coverage"]:
            md.append(f"| {label} | Fiscal Lab | " + " | ".join(fmt(v, 2) for v in t3[label]) + " |")
            cy = change_by_cy(runs, reform, variables)
            md.append(f"| {label} | PolicyEngine | " + " | ".join(fmt(None if cy[t] is None else cy[t] / 1e6, 2) for t in YEARS) + " |")
            for t in YEARS:
                pe_coverage_rows.append(
                    {
                        "bill": spec["bill"],
                        "coverage": label,
                        "policyengine_variables": " + ".join(variables),
                        "calendar_year": t,
                        "policyengine_millions": None if cy[t] is None else round(cy[t] / 1e6, 4),
                    }
                )
        md.append("")

        md += [
            "PolicyEngine's budgetary impact, billions, calendar years, positive = government better off (the opposite "
            "sign from the line table above). The first four rows are policyengine's own partition, rebuilt from the "
            "recorded totals. Its total leaves out the premium tax credit and the Basic Health Program (they sit outside "
            "household benefits while `include_health_benefits_in_net_income` is false). Its federal row counts only "
            "income and employee payroll taxes and the federal shares of Medicaid, CHIP and the Medicare Savings Programs; SNAP, "
            "school meals, WIC and other benefits sit in the unattributed row. It also includes items outside Fiscal "
            "Lab's figures: state shares of Medicaid, CHIP and the Medicare Savings Programs, state taxes and benefits, "
            "and other programs keyed to the poverty line such as WIC, TANF and CSFP. The last row adds the changes in "
            "the premium tax credit used (`used_aca_ptc`) and the Basic Health Program back.",
            "",
            "| Part | " + " | ".join(map(str, YEARS)) + " |",
            "|---|" + "---:|" * len(YEARS),
        ]
        rows = {k: [] for k in ("total", "federal", "state", "unattributed", "total with PTC and BHP")}
        for t in YEARS:
            run = runs.get(t)
            if t < FIRST_YEAR[reform]:
                for k in rows:
                    rows[k].append("0.0")
            elif run is None or reform not in run["reforms"]:
                for k in rows:
                    rows[k].append("—")
            else:
                b, r = run["baseline"], run["reforms"][reform]
                part = partition(b, r, run["include_health"])
                for k in ("total", "federal", "state", "unattributed"):
                    rows[k].append(fmt(part[k] / 1e9))
                health = (r["used_aca_ptc"] - b["used_aca_ptc"]) + (r["basic_health_program"] - b["basic_health_program"])
                rows["total with PTC and BHP"].append(fmt((part["total"] - health) / 1e9))
        md += [f"| {k} | " + " | ".join(v) + " |" for k, v in rows.items()]
        md.append("")

    write_csv(args.results / "comparison.csv", csv_rows)
    (args.results / "comparison.md").write_text("\n".join(md) + "\n")
    write_csv(args.tables / "policyengine_by_fiscal_year.csv", pe_fy_rows)
    write_csv(args.tables / "policyengine_coverage_by_calendar_year.csv", pe_coverage_rows)
    print("\n".join(md))


if __name__ == "__main__":
    main()
