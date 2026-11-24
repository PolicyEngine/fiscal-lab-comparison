# Fiscal Lab and PolicyEngine on the same bills

Work in progress. This repository runs PolicyEngine's US microsimulation on parts of two bills that Fiscal Lab on Capitol Hill scored in November 2026, and compares the results line by line with Fiscal Lab's published components:

- H.R. 4849, the Protecting Health Care and Lowering Costs Act of 2025: its coverage provisions (the permanent enhanced premium tax credit and the repeal of the One Big Beautiful Bill Act's Medicaid work requirement and immigrant limits).
- H.R. 1428, the Poverty Line Act of 2025: a higher federal poverty guideline from 2030.

Results will appear here after independent review.

## What is compared

[`fiscal_lab_comparison/reforms.py`](fiscal_lab_comparison/reforms.py) encodes each bill as a PolicyEngine reform, and [`scripts/check_reforms.py`](scripts/check_reforms.py) checks the parameter values and a few households. The encoding covers only provisions that policyengine-us 2.2.2 represents as parameters.

**H.R. 4849, from January 2027.**
- Encoded:
  - the enhanced premium tax credit schedule, made permanent, with eligibility above 400 percent of the poverty line;
  - repeal of the Medicaid work requirement (OBBBA Sec. 71119);
  - the immigration-status lists for Medicaid and the premium tax credit as they stood before OBBBA (Secs. 71109, 71301), and the below-poverty-line exception for lawfully present immigrants (Sec. 71302);
  - from 2028, the indexed long-term care home equity limit in place of OBBBA's flat $1,000,000 (Sec. 71108).
- Not encoded:
  - the provider-tax, directed-payment, emergency Medicaid and rural health sections, which Fiscal Lab prices with separate models;
  - the six-month redetermination repeal and OBBBA's CHIP immigrant limit (Sec. 71109(b)), which policyengine-us does not represent.
- The bill's own effective dates are earlier for some provisions. Every change here starts in January 2027, the first calendar year of Fiscal Lab's coverage lines.

**H.R. 1428.**
- Encoded:
  - the poverty guideline multiplied by 1.97 from 2030, keeping each year's baseline uprating;
  - from fiscal 2031, the SNAP standard deduction set to 8.31 percent of the new monthly line (or its current value, if that is higher). Guam's deduction is built on twice the contiguous-states line, as the Food and Nutrition Act sets it, and the Virgin Islands' on the contiguous-states line, which its standard tracks today. Microcosm has no territory households, so these change no number.
- Fiscal Lab's coverage model uses one factor for each state, averaging 1.97 nationally. Its Medicare part uses a line averaging about 1.63 times today's for a Medicare couple, and its SNAP and school meals lines use each household's own line. PolicyEngine stores one guideline for the contiguous states and DC, one for Alaska and one for Hawaii, and applies 1.97 to all three, so its Medicare Savings Programs, SNAP and school meals all run on 1.97.

## Method

- **Years:** [`scripts/run_year.py`](scripts/run_year.py) runs one simulation (the baseline or one reform) for one calendar year per process, on the certified Microcosm dataset. Each process records its totals, the versions, the repository commit and a fingerprint of the year's data, and [`scripts/compare.py`](scripts/compare.py) refuses to combine processes whose fingerprints differ. A reform's years before its first change are zero by construction.
- **Medicaid price in a reform:** policyengine-us prices a reform's Medicaid enrollees against the baseline's state enrollment, which it gets by building a second, baseline-policy simulation inside the reform. That doubles the Medicaid eligibility and income tax work in memory. Each year's baseline process saves those state values, and the reform reads them instead of computing them again. The values are the ones the second simulation would compute. A parity check on sample runs compares every total with the unmodified code, and each reform's JSON records which variables the second simulation was asked for.
- **Fiscal years:** compare.py counts each line by fiscal year with a rule that fits how the change is timed.
  - Coverage lines (Medicaid and CHIP, the premium tax credit, the Basic Health Program, Medicare Savings Programs) use Fiscal Lab's own rule for its coverage model: fiscal year *t* is a quarter of calendar year *t* − 1 plus three quarters of calendar year *t*.
  - SNAP follows the same rule, except that the first calendar year's change, which falls in October to December 2030, goes wholly to fiscal 2031.
  - School meals use the guideline from July 1, so PolicyEngine's calendar-year result is read as a school year, and fiscal year *t* takes five sixths of school year *t* − 1 and one sixth of school year *t*. The one sixth, August and September's share of school days, is an assumption.
- **Matching lines:** compare.py matches each Fiscal Lab component to the PolicyEngine variables that measure the same thing, and says on every line whether the two rest on the same policy input. It shows the two numbers side by side and computes no ratios.
- **Coverage:** compare.py sets enrollment changes beside Fiscal Lab's coverage table. Marketplace enrollment counts only people whose credit is above zero.
- **Budget partition:** compare.py also rebuilds policyengine's own budgetary impact from the recorded totals. That total leaves out the premium tax credit and the Basic Health Program, and includes state items and other federal programs keyed to the poverty line that Fiscal Lab doesn't score, so the table adds a row with the two health lines put back.

### Differences in inputs

- **Take-up:**
  - Medicaid: the dataset fixes take-up. People who reported Medicaid in the 2024 survey enroll whenever eligible, and anyone else eligible enrolls at a state fill rate (every eligible person in states where enrollment exceeds modeled eligibility).
  - CHIP and the Basic Health Program: every eligible person counts as enrolled.
  - Medicare Savings Programs: every eligible person counts as enrolled.
  - Premium tax credit: take-up and plan choice are the dataset's 2024 assignment.
  - Fiscal Lab's coverage model instead chooses each person's coverage, and moves people out of employer coverage.
- **Medicaid price:** PolicyEngine prices an enrollee at the state's 2023 total Medicaid spending divided by baseline enrollment. That price doesn't grow after 2023 or vary by eligibility group. Fiscal Lab prices the adults who regain coverage below the average enrollee.
- **Baseline premium tax credit:** PolicyEngine's baseline holds the 2026 applicable percentages for 2027 to 2036, while current law indexes them (2.15 to 10.22 percent in 2027). That understates H.R. 4849's gain below 400 percent of the line.
- **Immigration coding:** Microcosm has no refugee, asylee or parolee records; it codes documented non-citizens as permanent residents. So the immigrant repeals barely reach it, while Fiscal Lab's coverage model puts $132.2 billion on restoring immigrants' credits.
- **School meals:** PolicyEngine counts every K-12 child as eating breakfast and lunch every school day, and doesn't model community eligibility schools.
- **Not modeled:** PolicyEngine computes no cost-sharing reduction payments and models no move out of employer coverage, so those two Fiscal Lab lines have no PolicyEngine counterpart.

## Reproduce

```bash
uv sync
uv run python scripts/fetch_fiscal_lab.py                  # Fiscal Lab's dashboard data, kept out of git
uv run python scripts/check_reforms.py                     # parameter and household checks for each reform
uv run python scripts/run_year.py 2030 --sim baseline      # one simulation for one calendar year
uv run python scripts/run_year.py 2030 --sim hr4849_coverage
uv run python scripts/run_year.py 2030 --sim hr1428_poverty_line
uv run python scripts/compare.py                           # writes results/comparison.md and .csv
```

Repeat the simulations for 2027 to 2036 (H.R. 1428 from 2030), running each year's baseline before its reforms: a reform reads the baseline's saved Medicaid denominator (`outputs/year_<year>/baseline.medicaid_slcsp_state_denominator.npz`, person-level and kept out of git) and stops if it is missing or comes from another year file. A 2030 baseline with default outputs took about an hour and peaked at 23 GB of memory. `run_year.py --sim <name> --sample 300 --out outputs-smoke` runs the same steps on 300 households, as a quick check of the output path. PolicyEngine runs use the latest `policyengine` release (6.20.3, which pins policyengine-us 2.2.2) and its certified Microcosm dataset. Fiscal Lab's figures are fetched from its public dashboard and are not redistributed here.
