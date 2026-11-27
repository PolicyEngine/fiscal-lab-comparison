"""PolicyEngine encodings of the two Fiscal Lab bills compared here.

Each function returns a reform dict in the ``{parameter: {"start.stop": value}}``
shape that ``policyengine`` accepts for ``Simulation(policy=...)`` and
``calculate_household(reform=...)``.

Each reform encodes the bill's provisions that policyengine-us 2.2.2
represents as parameters; the README lists what each leaves out.
"""

from __future__ import annotations

from functools import lru_cache

OPEN_END = "2100-12-31"


def _open(start: str, value):
    return {f"{start}.{OPEN_END}": value}


# ---------------------------------------------------------------------------
# H.R. 4849, Protecting Health Care and Lowering Costs Act of 2025:
# the coverage provisions (Fiscal Lab's FLASH part of the score).
# ---------------------------------------------------------------------------

# American Rescue Plan Act / Inflation Reduction Act applicable-percentage
# schedule, as policyengine-us stores it for 2021-2025
# (parameters/gov/aca/required_contribution_percentage/*.yaml, 2021-01-01).
ENHANCED_PTC_THRESHOLD = [0, 1.50, 2.00, 2.50, 3.00, 4.00]
ENHANCED_PTC_INITIAL = [0, 0, 0.02, 0.04, 0.06]
ENHANCED_PTC_FINAL = [0, 0.02, 0.04, 0.06, 0.085]

# Pre-OBBBA Medicaid eligible statuses
# (parameters/gov/hhs/medicaid/eligibility/eligible_immigration_statuses.yaml, 2018-01-01).
PRE_OBBBA_MEDICAID_STATUSES = [
    "CITIZEN",
    "LEGAL_PERMANENT_RESIDENT",
    "REFUGEE",
    "ASYLEE",
    "DEPORTATION_WITHHELD",
    "CUBAN_HAITIAN_ENTRANT",
    "CONDITIONAL_ENTRANT",
    "PAROLED_ONE_YEAR",
]

# Pre-OBBBA PTC-ineligible statuses (parameters/gov/aca/ineligible_immigration_statuses.yaml,
# the 2025-08-25 entry, before the OBBBA Sec. 71301 entry of 2027-01-01).
PRE_OBBBA_PTC_INELIGIBLE_STATUSES = ["DACA", "UNDOCUMENTED"]

HR4849_START = "2027-01-01"
LAST_YEAR = 2036


@lru_cache(maxsize=1)
def _baseline_parameters():
    from policyengine_us import CountryTaxBenefitSystem

    return CountryTaxBenefitSystem().parameters



HOME_EQUITY_FIRST_YEAR = 2028  # OBBBA Sec. 71108's flat $1,000,000 limit starts here


def hr4849_coverage() -> dict:
    """Sec. 3 (enhanced PTC made permanent) and the Sec. 2 repeals of OBBBA
    rules that policyengine-us 2.2.2 represents as parameters: the Medicaid
    work requirement (Sec. 71119), the Medicaid immigrant limits (Sec. 71109),
    the PTC immigrant limits (Secs. 71301 and 71302) and the long-term care
    home equity limit (Sec. 71108). policyengine-us does not represent the CHIP
    immigrant limit of Sec. 71109(b), the six-month redeterminations or the
    other Sec. 2 repeals as parameters, so they are not encoded.

    The bill's own effective dates are earlier for some provisions. Fiscal
    Lab's coverage model starts the coverage effects in calendar 2027 (its
    fiscal 2027 lines are three quarters of a full year), so every change here
    starts on 2027-01-01, except the home equity limit, which OBBBA changes
    from 2028.
    """
    s = HR4849_START
    p = _baseline_parameters()
    equity = p.gov.hhs.medicaid.eligibility.long_term_care.home_equity
    # Before OBBBA the non-agricultural limit tracked the indexed maximum that
    # policyengine-us still carries as the agricultural limit (CPI-U uprated).
    home_equity = {}
    for year in range(HOME_EQUITY_FIRST_YEAR, LAST_YEAR + 1):
        stop = OPEN_END if year == LAST_YEAR else f"{year}-12-31"
        home_equity[f"{year}-01-01.{stop}"] = float(equity.agricultural_limit(f"{year}-01-01"))
    return {
        "gov.aca.required_contribution_percentage.threshold": _open(
            s, ENHANCED_PTC_THRESHOLD
        ),
        "gov.aca.required_contribution_percentage.initial": _open(
            s, ENHANCED_PTC_INITIAL
        ),
        "gov.aca.required_contribution_percentage.final": _open(s, ENHANCED_PTC_FINAL),
        # Bracket 2 starts at 400% FPL: eligibility above 400% FPL restored.
        "gov.aca.ptc_income_eligibility[2].amount": _open(s, True),
        "gov.hhs.medicaid.eligibility.work_requirements.applies": _open(s, False),
        "gov.hhs.medicaid.eligibility.eligible_immigration_statuses": _open(
            s, PRE_OBBBA_MEDICAID_STATUSES
        ),
        "gov.aca.ineligible_immigration_statuses": _open(
            s, PRE_OBBBA_PTC_INELIGIBLE_STATUSES
        ),
        "gov.aca.below_fpl_immigration_exception_in_effect": _open(s, True),
        "gov.hhs.medicaid.eligibility.long_term_care.home_equity.limit": home_equity,
    }


# ---------------------------------------------------------------------------
# H.R. 1428, Poverty Line Act of 2025: a higher poverty guideline.
# ---------------------------------------------------------------------------

# Fiscal Lab: "The new line averages 1.97 times today's guideline nationally."
# Fiscal Lab applies a factor by state; policyengine-us stores one guideline
# for the 48 contiguous states and DC, one for Alaska and one for Hawaii, so
# this applies the national average factor to all three.
FPG_FACTOR = 1.97
FPG_REGIONS = ["CONTIGUOUS_US", "AK", "HI"]
# Fiscal Lab: the change takes effect in December 2029; its coverage lines start
# in calendar 2030 and its SNAP lines in fiscal 2031.
HR1428_FPG_FIRST_YEAR = 2030
# SNAP standard deduction: 7 U.S.C. 2014(e)(1)(A) sets it at 8.31 percent of the
# monthly net-income eligibility standard (100 percent of the poverty line) for
# household sizes 1-6, subject to a floor. Fiscal Lab's line: "standard deduction
# at 8.31 percent of the household's own line".
SNAP_STD_DEDUCTION_SHARE = 0.0831
SNAP_STD_FIRST_FY_START = "2030-10-01"  # fiscal 2031
# Guam and the Virgin Islands have their own standard deductions in
# policyengine-us, and fpg.yaml stores no guideline for them. By 7 U.S.C.
# 2014(c)(1) and (e)(1), Guam's income standard is twice the 48-state line and
# the Virgin Islands' is the 48-state line, so both deductions follow the
# 48-state guideline. Microcosm has no territory households, so this changes
# no number here; it keeps the encoding complete.
SNAP_TERRITORY_MULTIPLE = {"GU": 2.0, "VI": 1.0}


def hr1428_poverty_line(factor: float = FPG_FACTOR) -> dict:
    """Poverty guideline multiplied by ``factor`` from 2030, year by year, so
    each year keeps the baseline's own uprating; SNAP standard deduction set to
    the larger of its baseline value (which carries the statutory floor) and
    8.31 percent of the new monthly guideline, from fiscal 2031."""
    p = _baseline_parameters()
    reform: dict = {}
    for kind in ("first_person", "additional_person"):
        for region in FPG_REGIONS:
            node = p.gov.hhs.fpg.children[kind].children[region]
            periods = {}
            for year in range(HR1428_FPG_FIRST_YEAR, LAST_YEAR + 1):
                stop = OPEN_END if year == LAST_YEAR else f"{year}-12-31"
                periods[f"{year}-01-01.{stop}"] = factor * float(node(f"{year}-01-01"))
            reform[f"gov.hhs.fpg.{kind}.{region}"] = periods

    std = p.gov.usda.snap.income.deductions.standard
    first_fy = int(SNAP_STD_FIRST_FY_START[:4])
    for region in FPG_REGIONS:
        fpg = p.gov.hhs.fpg
        for size in range(1, 7):
            node = std.children[region].children[str(size)]
            periods = {}
            for fy_start_year in range(first_fy, LAST_YEAR + 1):
                instant = f"{fy_start_year}-10-01"
                # SNAP reads the guideline in force on October 1 of the fiscal
                # year (variables/gov/usda/snap/income/snap_fpg.py).
                annual_fpg = float(fpg.first_person.children[region](instant)) + float(
                    fpg.additional_person.children[region](instant)
                ) * (size - 1)
                new_monthly_line = factor * annual_fpg / 12
                value = max(float(node(instant)), SNAP_STD_DEDUCTION_SHARE * new_monthly_line)
                stop = OPEN_END if fy_start_year == LAST_YEAR else f"{fy_start_year + 1}-09-30"
                periods[f"{instant}.{stop}"] = value
            reform[f"gov.usda.snap.income.deductions.standard.{region}.{size}"] = periods
    fpg = p.gov.hhs.fpg
    for region, multiple in SNAP_TERRITORY_MULTIPLE.items():
        for size in range(1, 7):
            node = std.children[region].children[str(size)]
            periods = {}
            for fy_start_year in range(first_fy, LAST_YEAR + 1):
                instant = f"{fy_start_year}-10-01"
                annual_48 = float(fpg.first_person.CONTIGUOUS_US(instant)) + float(
                    fpg.additional_person.CONTIGUOUS_US(instant)
                ) * (size - 1)
                value = max(float(node(instant)), SNAP_STD_DEDUCTION_SHARE * multiple * factor * annual_48 / 12)
                stop = OPEN_END if fy_start_year == LAST_YEAR else f"{fy_start_year + 1}-09-30"
                periods[f"{instant}.{stop}"] = value
            reform[f"gov.usda.snap.income.deductions.standard.{region}.{size}"] = periods
    return reform


REFORMS = {
    "hr4849_coverage": hr4849_coverage,
    "hr1428_poverty_line": hr1428_poverty_line,
}
