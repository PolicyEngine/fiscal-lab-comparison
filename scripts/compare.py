"""Line up PolicyEngine's results with Fiscal Lab's published components.

Reads PolicyEngine totals from outputs/ (written by run_year.py) and Fiscal
Lab's figures from data/fiscal_lab/two_bills.json (written by
fetch_fiscal_lab.py). Writes results/comparison.md and results/comparison.csv;
results/ is kept out of git because it repeats Fiscal Lab's figures.

Counting by fiscal year. PolicyEngine runs calendar years. Each line's
calendar-year change is counted by fiscal year with the rule that fits how the
program's change is timed:

- coverage lines (Medicaid and CHIP, premium tax credit, Basic Health Program,
  Medicare Savings Programs): FY t = 0.25 CY(t-1) + 0.75 CY t, the rule Fiscal
  Lab uses for its coverage model;
- SNAP, which runs on an October 1 cycle (snap_fpg reads the October 1
  guideline and the standard-deduction change starts October 1, 2030): the same
  rule, except that the first calendar year's change, which falls in October to
  December, goes wholly to the next fiscal year;
- school meals, whose income guidelines apply to the school year from July 1
  (42 U.S.C. 1758(b)(1)(A)): PolicyEngine's calendar-year-t change, built on the
  year-t guideline, is read as school year t, and FY t = (1 - s) SY(t-1) + s SY
  t, where s = 1/6 is the share of school days in August and September (an
  assumption from a typical 180-day calendar).

A calendar year before a reform's first year is zero by construction (the
reform changes no parameter in force then).

Run: uv run python scripts/compare.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YEARS = list(range(2027, 2037))
FIRST_YEAR = {"hr4849_coverage": 2027, "hr1428_poverty_line": 2030}
AUG_SEP_SCHOOL_DAY_SHARE = 1 / 6

MEDICAID_PRICE = (
    "PolicyEngine prices an enrollee at the state's 2023 total Medicaid spending divided by baseline "
    "enrollment, with no growth after 2023 and no split by eligibility group"
)
CHIP_TAKEUP = "PolicyEngine counts every CHIP-eligible person as enrolled"
PTC_BASELINE = (
    "PolicyEngine's baseline holds the 2026 applicable percentages fixed for 2027-2036, while current law "
    "indexes them (2.15 to 10.22 percent in 2027), so it understates the gain below 400 percent of the line"
)
PTC_TAKEUP = "take-up and plan choice are fixed at the dataset's 2024 assignment"
FACTOR_1428 = (
    "Fiscal Lab uses each household's own line (a factor by state averaging 1.97); PolicyEngine applies 1.97 everywhere"
)

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
                "same_input": "no: " + MEDICAID_PRICE + "; Fiscal Lab prices the adults who regain coverage below the average enrollee. "
                "PolicyEngine omits six-month redeterminations and OBBBA's CHIP immigrant limit; Microcosm has no refugee, asylee "
                "or parolee records (it codes documented non-citizens as permanent residents), so the immigrant repeal barely "
                "reaches it; and " + CHIP_TAKEUP[len("PolicyEngine "):],
            },
            {
                "label": "Premium tax credits",
                "fiscal_lab": ["Premium tax credits for marketplace coverage"],
                "pe": ["used_aca_ptc"],
                "fy": "coverage",
                "same_input": "partly: " + PTC_BASELINE + "; Fiscal Lab's coverage model puts $132.2 billion on restoring "
                "immigrants' credits, which Microcosm's immigration coding largely cannot reach; " + PTC_TAKEUP,
            },
            {
                "label": "Basic Health Program",
                "fiscal_lab": ["Basic Health Program"],
                "pe": ["basic_health_program"],
                "fy": "coverage",
                "same_input": "partly: the same frozen baseline applicable percentages; Microcosm's immigration coding leaves BHP's path "
                "for immigrants barred from Medicaid empty in both runs, and PolicyEngine's BHP payment has no immigration "
                "test, so the immigrant repeal moves no BHP dollar; PolicyEngine counts every eligible person as enrolled",
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
                "same_input": "no: " + MEDICAID_PRICE + "; " + FACTOR_1428 + "; Fiscal Lab applies a 120 percent limit to people "
                "65 and older in every state, PolicyEngine each state's own aged and disabled limit times 1.97; "
                "people with employer coverage who become eligible enroll without leaving it; " + CHIP_TAKEUP,
            },
            {
                "label": "Premium tax credits",
                "fiscal_lab": ["Premium tax credits for marketplace coverage"],
                "pe": ["used_aca_ptc"],
                "fy": "coverage",
                "same_input": "partly: " + FACTOR_1428 + "; the credit reads the prior year's guideline, so its income test changes "
                "from 2031 and 2030 changes come only from people moving to Medicaid and CHIP; " + PTC_TAKEUP,
            },
            {
                "label": "Basic Health Program",
                "fiscal_lab": ["Basic Health Program"],
                "pe": ["basic_health_program"],
                "fy": "coverage",
                "same_input": "partly: " + FACTOR_1428 + "; PolicyEngine counts every eligible person as enrolled",
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
                "same_input": "no: Fiscal Lab's line for a Medicare couple averages 1.63 times today's line; PolicyEngine applies "
                "1.97 to everyone and counts every eligible person as enrolled (no take-up step)",
            },
            {
                "label": "SNAP",
                "fiscal_lab": [
                    "SNAP: current participants, standard deduction at 8.31 percent of the household’s own line (no ramp)",
                    "SNAP: newly eligible households, with take-up ramp",
                ],
                "pe": ["snap"],
                "fy": "october",
                "same_input": "partly: " + FACTOR_1428 + "; Fiscal Lab ramps take-up for newly eligible households, PolicyEngine's "
                "take-up is fixed",
            },
            {
                "label": "School meals",
                "fiscal_lab": [
                    "School meals, children outside community eligibility schools: category and meal-taking under the household’s line",
                    "School meals, CEP schools: free claim rises with the identified-student percentage",
                ],
                "pe": ["school_meal_net_subsidy"],
                "fy": "school_year",
                "same_input": "partly: " + FACTOR_1428 + "; PolicyEngine does not model community eligibility schools and counts "
                "every K-12 child as eating breakfast and lunch every school day (no meal-taking step)",
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


def load_pe() -> dict[int, dict]:
    """Per year: baseline totals, reform totals, and the health flag.

    run_year.py --sim writes outputs/year_<Y>/<simulation>.json, one simulation
    per process. A reform-minus-baseline sum across processes is valid only on
    the same records and weights, so every simulation's fingerprint must match
    the baseline's.
    """
    runs: dict[int, dict] = {}
    for ydir in sorted((ROOT / "outputs").glob("year_*")):
        if not ydir.is_dir():
            continue
        sims = {}
        for path in ydir.glob("*.json"):
            if path.name.endswith(".defaults.json"):
                continue  # memory measurements, default outputs only
            run = json.loads(path.read_text())
            sims[run["simulation"]] = run
        if "baseline" not in sims:
            continue
        year = sims["baseline"]["year"]
        ref = sims["baseline"]
        for name, run in sims.items():
            for key in FINGERPRINT_KEYS:
                if run["fingerprint"].get(key) != ref["fingerprint"].get(key):
                    raise SystemExit(f"{ydir}/{name}: {key} differs from the baseline's; not comparable")
            for key in ("versions", "bundle"):
                if run[key] != ref[key]:
                    raise SystemExit(f"{ydir}/{name}: {key} differs from the baseline's; not comparable")
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
            # The first calendar year's change falls in October-December: next fiscal year.
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


def main() -> None:
    fl = json.loads((ROOT / "data" / "fiscal_lab" / "two_bills.json").read_text())
    if fl["years"] != YEARS:
        raise SystemExit(f"Fiscal Lab years {fl['years']} != {YEARS}")
    runs = load_pe()
    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)

    csv_rows = []
    md = [
        "# Line-by-line comparison",
        "",
        f"PolicyEngine calendar years with results: {', '.join(map(str, sorted(runs))) or 'none'}. "
        "Dollar figures are billions over fiscal years 2027–2036, as effects on the deficit (a cost is positive). "
        f"Fiscal Lab's figures are from its dashboard (built {fl['built']}). PolicyEngine's are reform-minus-baseline "
        "changes, counted by fiscal year as `scripts/compare.py` describes. A dash means a year is not run yet.",
        "",
    ]
    for reform, spec in LINES.items():
        fl_bill = fl["bills"][spec["bill"]]
        md += [f"## {spec['bill']}: {fl_bill['title']}", ""]
        md += ["| Line | Fiscal Lab | PolicyEngine | Same policy input? |", "|---|---:|---:|---|"]
        for line in spec["lines"]:
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
            "PolicyEngine's count people enrolled in the year.",
            "",
            "| Coverage | Source | " + " | ".join(map(str, YEARS)) + " |",
            "|---|---|" + "---:|" * len(YEARS),
        ]
        for label, variables in spec["coverage"]:
            md.append(f"| {label} | Fiscal Lab | " + " | ".join(fmt(v, 2) for v in t3[label]) + " |")
            cy = change_by_cy(runs, reform, variables)
            md.append(f"| {label} | PolicyEngine | " + " | ".join(fmt(None if cy[t] is None else cy[t] / 1e6, 2) for t in YEARS) + " |")
        md.append("")

        md += [
            "PolicyEngine's budgetary impact, billions, calendar years, positive = government better off. "
            "The first four rows are policyengine's own partition, rebuilt from the recorded totals. Its total leaves out "
            "the premium tax credit and the Basic Health Program (they sit outside household benefits while "
            "`include_health_benefits_in_net_income` is false), and it includes items Fiscal Lab does not score: state "
            "shares of Medicaid, CHIP and the Medicare Savings Programs, state taxes and benefits, and federal programs "
            "keyed to the poverty line such as WIC, TANF and CSFP. The last row adds the premium tax credit and Basic "
            "Health Program changes back.",
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

    with open(results_dir / "comparison.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    (results_dir / "comparison.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
