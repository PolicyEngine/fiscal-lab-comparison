"""Check that each reform changes the parameters and households it should.

Run: uv run python scripts/check_reforms.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import policyengine as pe
from policyengine_core.reforms import Reform
from policyengine_us import CountryTaxBenefitSystem

from fiscal_lab_comparison.reforms import (
    ENHANCED_PTC_FINAL,
    FPG_FACTOR,
    hr1428_poverty_line,
    hr4849_coverage,
)

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


def reformed_parameters(reform: dict):
    system = Reform.from_dict(reform, country_id="us")(CountryTaxBenefitSystem())
    return system.parameters


base = CountryTaxBenefitSystem().parameters

# --- H.R. 4849 parameters ---------------------------------------------------
r4849 = hr4849_coverage()
p = reformed_parameters(r4849)
for year in (2026, 2027, 2036):
    i = f"{year}-01-01"
    final = list(p.gov.aca.required_contribution_percentage.final(i))
    expected = list(base.gov.aca.required_contribution_percentage.final(i)) if year == 2026 else ENHANCED_PTC_FINAL
    check(f"4849 final schedule {year}", final == expected, str(final))
check("4849 >400% FPL eligible 2027", bool(p.gov.aca.ptc_income_eligibility.brackets[2].amount("2027-01-01")))
check("4849 >400% FPL baseline 2026 unchanged", not bool(p.gov.aca.ptc_income_eligibility.brackets[2].amount("2026-01-01")))
check("4849 work requirement off 2027", not p.gov.hhs.medicaid.eligibility.work_requirements.applies("2027-01-01"))
check("4849 work requirement baseline on 2027", bool(base.gov.hhs.medicaid.eligibility.work_requirements.applies("2027-01-01")))
check("4849 refugees Medicaid-eligible 2027", "REFUGEE" in list(p.gov.hhs.medicaid.eligibility.eligible_immigration_statuses("2027-01-01")))
check("4849 refugees PTC-eligible 2027", "REFUGEE" not in list(p.gov.aca.ineligible_immigration_statuses("2027-01-01")))
check("4849 below-FPL exception on 2027", bool(p.gov.aca.below_fpl_immigration_exception_in_effect("2027-01-01")))
equity_b = base.gov.hhs.medicaid.eligibility.long_term_care.home_equity
equity_r = p.gov.hhs.medicaid.eligibility.long_term_care.home_equity
check("4849 home equity limit 2027 unchanged", equity_r.limit("2027-01-01") == equity_b.limit("2027-01-01"), f"{equity_b.limit('2027-01-01'):.0f}")
for year in (2028, 2036):
    i = f"{year}-01-01"
    check(
        f"4849 home equity limit {year} = indexed limit",
        equity_r.limit(i) == equity_b.agricultural_limit(i) and equity_b.limit(i) != equity_r.limit(i),
        f"{equity_b.limit(i):.0f} -> {equity_r.limit(i):.0f}",
    )

# --- H.R. 1428 parameters ---------------------------------------------------
r1428 = hr1428_poverty_line()
p = reformed_parameters(r1428)
for year in (2029, 2030, 2033, 2036):
    i = f"{year}-01-01"
    b = base.gov.hhs.fpg.first_person.CONTIGUOUS_US(i)
    r = p.gov.hhs.fpg.first_person.CONTIGUOUS_US(i)
    want = b if year < 2030 else FPG_FACTOR * b
    check(f"1428 FPG first person {year}", abs(r - want) < 0.01, f"{b:.0f} -> {r:.0f}")
for instant in ("2030-01-01", "2030-10-01", "2035-10-01"):
    b = base.gov.usda.snap.income.deductions.standard.CONTIGUOUS_US.children["4"](instant)
    r = p.gov.usda.snap.income.deductions.standard.CONTIGUOUS_US.children["4"](instant)
    changed = instant >= "2030-10-01"
    check(f"1428 SNAP std deduction size 4 at {instant}", (r > b) if changed else (r == b), f"{b:.0f} -> {r:.0f}")
for region in ("GU", "VI"):
    for instant in ("2030-01-01", "2030-10-01"):
        b = base.gov.usda.snap.income.deductions.standard.children[region].children["4"](instant)
        r = p.gov.usda.snap.income.deductions.standard.children[region].children["4"](instant)
        changed = instant >= "2030-10-01"
        check(f"1428 SNAP std deduction {region} size 4 at {instant}", (r > b) if changed else (r == b), f"{b:.0f} -> {r:.0f}")

# --- Households ---------------------------------------------------------------


def hh(year, people, state, reform=None, extra=(), filing="SINGLE", county=None):
    kwargs = dict(
        people=people,
        tax_unit={"filing_status": filing},
        household={"state_code": state, **({"county_fips": county} if county else {})},
        year=year,
        extra_variables=list(extra),
    )
    if reform is not None:
        kwargs["reform"] = reform
    return pe.us.calculate_household(**kwargs)


# Single 45-year-old, $80,000 wages, Los Angeles County: above 400% FPL in 2027.
args = (2027, [{"age": 45, "employment_income": 80_000}], "CA")
b = hh(*args, extra=["aca_ptc"], county="06037")
r = hh(*args, reform=r4849, extra=["aca_ptc"], county="06037")
check("4849 household >400% FPL gets PTC", b.tax_unit.aca_ptc == 0 and r.tax_unit.aca_ptc > 0, f"{b.tax_unit.aca_ptc:.0f} -> {r.tax_unit.aca_ptc:.0f}")

# Single 30-year-old with no earnings or hours, California (expansion state).
args = (2027, [{"age": 30, "employment_income": 0}], "CA")
b = hh(*args, extra=["is_medicaid_eligible"], county="06037")
r = hh(*args, reform=r4849, extra=["is_medicaid_eligible"], county="06037")
check(
    "4849 non-working adult: work requirement removed",
    (not b.person[0].is_medicaid_eligible) and r.person[0].is_medicaid_eligible,
    f"{b.person[0].is_medicaid_eligible} -> {r.person[0].is_medicaid_eligible}",
)

# Refugee adult working 30 hours a week at $12,000 a year, California.
person = {"age": 35, "employment_income": 12_000, "immigration_status": "REFUGEE", "weekly_hours_worked": 30}
args = (2027, [person], "CA")
try:
    b = hh(*args, extra=["is_medicaid_eligible"], county="06037")
    r = hh(*args, reform=r4849, extra=["is_medicaid_eligible"], county="06037")
    check(
        "4849 refugee Medicaid restored",
        (not b.person[0].is_medicaid_eligible) and r.person[0].is_medicaid_eligible,
        f"{b.person[0].is_medicaid_eligible} -> {r.person[0].is_medicaid_eligible}",
    )
except Exception as exc:  # input names differ across releases; report, don't hide
    check("4849 refugee Medicaid restored", False, f"{type(exc).__name__}: {exc}")

# Family of four in Wyoming (no broad-based categorical eligibility) at about
# 160% of the baseline guideline: fails SNAP's 130% gross test in baseline,
# passes under the higher line.
fpg4 = base.gov.hhs.fpg.first_person.CONTIGUOUS_US("2030-01-01") + 3 * base.gov.hhs.fpg.additional_person.CONTIGUOUS_US("2030-01-01")
fam = [
    {"age": 40, "employment_income": 1.6 * fpg4},
    {"age": 38},
    {"age": 10},
    {"age": 7},
]
args = (2031, fam, "WY")
b = hh(*args, filing="JOINT", extra=["snap"], county="56021")
r = hh(*args, filing="JOINT", reform=r1428, extra=["snap"], county="56021")
check("1428 family at 160% FPG gains SNAP in 2031", b.spm_unit.snap == 0 and r.spm_unit.snap > 0, f"{b.spm_unit.snap:.0f} -> {r.spm_unit.snap:.0f}")

# Same family in 2029: the reform changes nothing before 2030.
b = hh(2029, fam, "WY", filing="JOINT", extra=["snap"], county="56021")
r = hh(2029, fam, "WY", filing="JOINT", reform=r1428, extra=["snap"], county="56021")
check("1428 no change in 2029", b.household.household_net_income == r.household.household_net_income)

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
