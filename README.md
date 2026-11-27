# Fiscal Lab and PolicyEngine on the same bills

This repository runs PolicyEngine's US microsimulation on parts of two bills that Fiscal Lab on Capitol Hill scored in November 2026, and compares the results line by line with the components on [Fiscal Lab's dashboard](https://fiscallab.org/score/healthcare-working-group-memo-scores/dashboard.html):

- H.R. 4849, the Protecting Health Care and Lowering Costs Act of 2025: its coverage provisions (the permanent enhanced premium tax credit, the repeal of the One Big Beautiful Bill Act's Medicaid work requirement and immigrant limits, and the indexed long-term care home equity limit).
- H.R. 1428, the Poverty Line Act of 2025: its new poverty line, which the bill builds from state and county living costs, with today's line, adjusted for inflation, as a floor, taking effect three years after enactment; and through it the SNAP standard deduction, which current SNAP law ties to the line, from fiscal 2031. PolicyEngine sets the line at 1.97 times today's guideline from 2030, Fiscal Lab's estimate of its national average, and runs no other level. Fiscal Lab puts the range at about 1.54 to 2.54 times, depending on the Secretary's choices.

Every simulation for 2027 to 2036 (H.R. 1428 from 2030) ran at commit 9f854e6. An independent review recomputed every number and found none wrong. It corrected two mechanism statements in the line labels and added omitted mechanisms, which this README and the labels now carry, and a second review checked those edits. Later commits add the outputs, this documentation and two scripts that print the inputs to the figures cited here, and change `scripts/compare.py`'s labels, options and checks. The run code (`scripts/run_year.py` apart from its docstring and one comment, and `fiscal_lab_comparison/`) is unchanged, and `compare.py` gives the same numbers.

## Results

PolicyEngine's totals, billions of dollars over fiscal years 2027 to 2036, as effects on the deficit (a cost is positive). [`tables/policyengine_by_fiscal_year.csv`](tables/policyengine_by_fiscal_year.csv) has each year (`policyengine_cost_bn`, a cost positive).

| Line | H.R. 4849 | H.R. 1428 |
|---|---:|---:|
| Federal Medicaid and CHIP spending | 172.7 | 3,645.3 |
| Premium tax credits | 536.4 | 44.1 |
| Basic Health Program | 15.1 | -48.3 |
| Medicare Savings Programs (federal Medicaid share) | | 67.5 |
| SNAP | | 98.3 |
| School meals | | 85.4 |

PolicyEngine computes no cost-sharing reduction payments and moves no one out of employer coverage, so it has no counterpart to those Fiscal Lab lines. Fiscal Lab's provider-tax, directed-payment, emergency Medicaid, rural health and implementation-funds lines (H.R. 4849) and its Part D low-income subsidy, induced Medicare use, Summer EBT and CACFP lines (H.R. 1428) have none either. The compared lines therefore cover only part of each Fiscal Lab score.

Coverage changes, millions of people, by calendar year ([`tables/policyengine_coverage_by_calendar_year.csv`](tables/policyengine_coverage_by_calendar_year.csv)). PolicyEngine's enrollment variables are annual statuses, each person counted for the full year; Fiscal Lab reports average enrollment.

- H.R. 4849: Medicaid and CHIP +1.11 million (2027) to +1.05 million (2036); subsidized Marketplace +7.08 million to +9.88 million.
- H.R. 1428: Medicaid and CHIP +44.19 million (2030) to +45.18 million (2036); subsidized Marketplace -5.01 million (2030), +0.92 million (2031) and +2.51 million (2036).
- In the local side-by-side table, H.R. 4849's Marketplace gains look close to Fiscal Lab's, but that is not agreement: Fiscal Lab's likely include immigrants whose credits PolicyEngine cannot reach (inferred from its $132.2 billion credit for immigrants), and PolicyEngine's come only from tax units with the dataset's take-up flag whose used credit turns positive.

`scripts/compare.py` builds the full side-by-side table with Fiscal Lab's figures locally (`results/`, not committed). The headline gaps and what drives them follow. We read each PolicyEngine mechanism below from policyengine-us 2.2.2's source, each Fiscal Lab one from its published narrative and tables, and each legal or dataset claim from the cited law or the dataset; "inferred" marks what none of these states.

### H.R. 4849

- **Medicaid: 172.7 against Fiscal Lab's 565.9.** PolicyEngine's whole Medicaid change comes from repealing the work requirement. Its baseline requirement is a deterministic annual test: a person passes on survey hours, on an exemption, or on household MAGI of at least $6,960 a year, PolicyEngine's annual version of the $580-a-month income test in 42 CFR 435.552(f). It models no reporting or verification loss and applies in full from January 2027, so the repeal restores about 1.0 to 1.1 million people in every year, while Fiscal Lab's Medicaid and CHIP gain rises from about 2.6 million in 2027 to about 7 million in 2031 and 2032, then eases. Fiscal Lab's line also covers six-month redeterminations and immigrant limits, which PolicyEngine does not encode or does not reach (below). Price points the other way: PolicyEngine's cost per restored enrollee runs about a quarter to a third above its average enrollee ($16,400 against $13,200 in 2027), and at the 90 percent expansion match its federal cost per restored enrollee is about $14,800 against an $8,800 average. Fiscal Lab prices them below its average. PolicyEngine's CHIP change is zero.
- **Premium tax credit: 536.4 against Fiscal Lab's 507.7, which is not agreement.** Fiscal Lab's coverage model puts $132.2 billion on restoring immigrants' credits, which reach no one in PolicyEngine's data (below). If that sum sits inside Fiscal Lab's credit line, PolicyEngine is about 43 percent higher on the rest (inferred). PolicyEngine's baseline holds the 2026 applicable percentages fixed through 2036, while current law indexes them, which lowers PolicyEngine's gain for units below 400 percent of the line, so the source of the gap is not identified. PolicyEngine's line is the credit tax units use (`used_aca_ptc`): units that carry the dataset's premium tax credit take-up flag (6.7 percent of people in the 2024 file) and pay a premium.
- **Basic Health Program: 15.1 against Fiscal Lab's 4.2.** BHP enrollment is unchanged in every year, so the whole change is in payment per enrollee. The same frozen percentages apply, and the source of the gap is not identified either.
- **Immigrant limits (Secs. 71109, 71301, 71302) reach no one.** Microcosm codes people only as citizens, permanent residents, undocumented immigrants, Cuban/Haitian entrants or DACA recipients, with no refugee, asylee, parolee or TPS records, and it records no entry year (the default of five years clears the five-year bar). The pre-OBBBA lists add only statuses Microcosm lacks, and the below-poverty-line exception needs a lawfully present person barred from Medicaid by status, and Microcosm has no such person.
- **Home equity (Sec. 71108) moves no total.** PolicyEngine encodes it, but in policyengine-us 2.2.2 no eligibility or cost variable reads the long-term care eligibility test that uses it.

### H.R. 1428

- **Medicaid: 3,645.3 against Fiscal Lab's 1,077.6.** Three inputs likely push PolicyEngine up (inferred; their sizes were not computed), and the level of the line likely does not explain the gap (inferred: Fiscal Lab publishes no high-case Medicaid line).
  - Take-up: the dataset sets the Medicaid take-up flag for everyone it marks as currently having Medicaid, and for about 91 percent of everyone else (2024 weights; 51 to 100 percent by state, 100 percent in 20 states), including about 90 percent of those with employer coverage, who keep it when they enroll.
  - Price: PolicyEngine prices every new enrollee at the state's average for their benchmark-premium index, whether or not they keep employer coverage or Medicare, which pay before Medicaid (42 U.S.C. 1396a(a)(25)). Under policyengine-us's default age curve, an enrollee aged 64 or over carries about 3.9 times the index of a child under 15 (some states have their own curves, and New York and Vermont use family tiers). This comparison does not count how many new enrollees keep other coverage, or compute what that adds to cost.
  - Shape: PolicyEngine holds the 1.97 factor in every year, so its enrollment gain stays flat at 44 to 45 million through 2036. Fiscal Lab's falls by about a third, for reasons it does not publish. The bill builds its line from county-level costs, which a flat factor cannot track.
  - Level: PolicyEngine runs only Fiscal Lab's central 1.97. Fiscal Lab's high case, about 2.54 times today's line, puts its coverage part, which nets its Medicaid line against its credit, Basic Health Program, employer exclusion and cost-sharing lines, at $1,433.9 billion, still below PolicyEngine's Medicaid line alone.
  - Fiscal Lab's coverage model applies one factor by state, averaging 1.97; PolicyEngine applies 1.97 everywhere. Fiscal Lab applies a 120 percent limit to people 65 and older in every state; PolicyEngine applies each state's own aged and disabled limit times 1.97.
- **Premium tax credit: 44.1 against Fiscal Lab's -49.3, opposite signs.** The credit's own income test reads the prior year's guideline, so it changes only from 2031. In 2030 the credit falls because people become eligible for Medicaid, CHIP or (in Minnesota, New York, Oregon and DC) the Basic Health Program, whose tests read the current year's line. Eligibility alone ends the credit, so newly eligible people who do not take up Medicaid lose it too. From 2031 the new line lowers applicable percentages and moves the 400 percent limit to 7.9 times today's line. The credit summed over every eligible unit (`aca_ptc`) falls $37.4 billion in calendar 2031, but the credit used by units that carry the take-up flag rises $6.6 billion, so PolicyEngine's line rises while Fiscal Lab's falls.
- **Basic Health Program: -48.3 against Fiscal Lab's -5.3.** PolicyEngine models BHP in Minnesota, New York (the Essential Plan), Oregon and DC, at $9.4 billion (2027) to $17.7 billion (2036) a year for 1.1 to 1.4 million people. Every baseline enrollee's income falls under the new Medicaid limit, while BHP's own band moves up with the current year's line, so BHP enrollment falls on net, by 0.41 to 0.60 million a year. Fiscal Lab does not publish the size of its BHP base.
- **School meals: 85.4 against Fiscal Lab's 47.5.** In the nine states with universal free school meals (California, Colorado, Maine, Massachusetts, Michigan, Minnesota, New Mexico, New York and Vermont), home to about a quarter of people aged 5 to 17 (2024 weights), PolicyEngine puts every student on the free tier, so H.R. 1428 changes no school-meal dollar there. Two other differences likely push PolicyEngine up (inferred): it counts everyone aged 5 to 17 as a student eating breakfast and lunch on all 180 school days, and it does not model community eligibility schools. Fiscal Lab's school meals and SNAP lines use each household's own line.
- **SNAP: 98.3 against Fiscal Lab's 71.3.** PolicyEngine fixes take-up at the dataset's flags (about 93 percent of people, 2024 weights), with no ramp for the newly eligible. It counts the change mostly from October 2030 (from January to April 2030 for broad-based categorical eligibility in Maine, Massachusetts, Oregon and Washington; the split was not computed), which adds $3.8 billion in calendar 2030; Fiscal Lab's yearly figures appear to start in January 2031 (inferred).
- **Medicare Savings Programs: 67.5 against Fiscal Lab's 54.6.** PolicyEngine applies 1.97 to everyone and counts every eligible person as enrolled; Fiscal Lab's line for a Medicare couple averages about 1.63 times today's line. PolicyEngine's MSP cost is zero for anyone enrolled in full Medicaid, so people H.R. 1428 moves into Medicaid count in the Medicaid line, much as Fiscal Lab's line nets out people its coverage model already puts in Medicaid. PolicyEngine's fiscal-year rule puts three quarters of calendar 2030 in fiscal 2030, while Fiscal Lab's Medicare lines appear to start about April 2030 (inferred).

### Medicaid price in both bills

PolicyEngine holds each state's Medicaid spending at its 2023 total ($880.0 billion nationally) in every year and shares it among enrollees by a benchmark-premium index (age-rated, except in New York and Vermont, which use family tiers). So the price per enrollee has no medical-cost growth. It moves only against PolicyEngine's baseline enrollment: the average rises 16 percent, from about $13,200 in 2027 to $15,400 in 2036, as baseline enrollment falls from 66.5 to 57.2 million. An enrollee's price also scales with their index against the state's other enrollees, and it does not depend on eligibility group or other coverage.

## What this compares

[`fiscal_lab_comparison/reforms.py`](fiscal_lab_comparison/reforms.py) encodes each bill as a PolicyEngine reform, and [`scripts/check_reforms.py`](scripts/check_reforms.py) checks the parameter values and a few households. The encoding covers only provisions that policyengine-us 2.2.2 represents as parameters.

**H.R. 4849, from January 2027.**
- Encoded:
  - the enhanced premium tax credit schedule, made permanent, with eligibility above 400 percent of the poverty line;
  - repeal of the Medicaid work requirement (OBBBA Sec. 71119);
  - the immigration-status lists for Medicaid and the premium tax credit as they stood before OBBBA (Secs. 71109, 71301), and the below-poverty-line exception for lawfully present immigrants (Sec. 71302);
  - from 2028, the indexed long-term care home equity limit in place of OBBBA's flat $1,000,000 (Sec. 71108).
- Not encoded:
  - the provider-tax, directed-payment, emergency Medicaid and rural health sections, which Fiscal Lab prices outside its coverage model;
  - the six-month redetermination repeal and OBBBA's CHIP immigrant limit (Sec. 71109(b)), which policyengine-us does not represent;
  - the bill's other Subtitle B sections, which neither Fiscal Lab nor policyengine-us prices.
- The bill's own effective dates are earlier for some provisions. Every change here starts in January 2027, the first calendar year of Fiscal Lab's coverage lines.

**H.R. 1428.**
- Encoded:
  - the poverty guideline multiplied by 1.97 from 2030, Fiscal Lab's estimate of the new line's national average (the bill sets no multiple), keeping each year's baseline uprating;
  - from fiscal 2031, the SNAP standard deduction set to 8.31 percent of the new monthly line (or its current value, if that is higher), as current SNAP law ties it to the line; the bill has no SNAP section. Guam's deduction is built on twice the contiguous-states line, as the Food and Nutrition Act sets it, and the Virgin Islands' on the contiguous-states line, which its standard tracks today. Microcosm has no territory households, so these change no number.
- PolicyEngine stores one guideline for the contiguous states and DC, one for Alaska and one for Hawaii, and applies 1.97 to all three in every year.
- The bill builds its line from state and county cost components, with today's line, adjusted for inflation, as a floor, and takes effect three years after enactment. The 2030 start follows Fiscal Lab, which dates the change to December 2029 and scores nothing before 2030; PolicyEngine starts it in January 2030.

## Method

- **Years:** [`scripts/run_year.py`](scripts/run_year.py) runs one simulation (the baseline or one reform) for one calendar year per process, on the certified Microcosm dataset (build populace-us-2024-spm-20260915, uprated to each year, with population growth). Each process records its totals, the versions, the repository commit and a fingerprint (the year file's hash and weight sums). [`scripts/compare.py`](scripts/compare.py) refuses to combine processes whose fingerprints, versions, commit or year differ. A reform's years before its first change are zero by construction.
- **Medicaid price in a reform:** policyengine-us prices a reform's Medicaid enrollees against the baseline's index-weighted state enrollment, which it gets by building a second, baseline-policy simulation inside the reform. That doubles the Medicaid eligibility and income tax work in memory. Each year's baseline process saves those values (in 2030, one for each of 166,321 person records, 51 distinct), and the reform reads them instead of computing them again. In five pairs of 2030 samples (each simulation at 12,000 households; the baseline and H.R. 4849 also at 3,000), every total matched the unmodified code bit for bit ([`docs/parity.md`](docs/parity.md); patched code at commit 09a471c, whose run code is the same as 9f854e6's; unmodified code at commit 3d73379).
- **Fiscal years:** compare.py counts each line by fiscal year with a rule that fits how the change is timed. These rules are this comparison's choices, not policyengine-us's.
  - Coverage lines (Medicaid and CHIP, the premium tax credit, the Basic Health Program, Medicare Savings Programs) use Fiscal Lab's own rule for its coverage model: fiscal year *t* is a quarter of calendar year *t* − 1 plus three quarters of calendar year *t*.
  - SNAP follows the same rule, except that the first calendar year's change, mostly from October to December 2030 (inferred: the outputs hold calendar-year totals only), goes wholly to fiscal 2031.
  - School meals use the guideline from July 1, so compare.py reads PolicyEngine's calendar-year result as a school year, and fiscal year *t* takes five sixths of school year *t* − 1 and one sixth of school year *t*. The one sixth, August and September's share of school days, is an assumption.
  - The window ends in September 2036, so it leaves out a quarter of calendar 2036 for coverage lines and SNAP, and five sixths of school year 2036 for school meals, as Fiscal Lab's window does.
- **Matching lines:** compare.py matches each Fiscal Lab component to the PolicyEngine variables that measure the same thing, and says on every line whether the two rest on the same policy input. It sets the two numbers side by side and computes no ratios.
- **Coverage:** Marketplace enrollment counts only people whose used credit is above zero.
- **Budget partition:** compare.py also rebuilds policyengine's own budgetary impact from the recorded totals, by calendar year, with the government being better off as positive (the opposite sign from the line table). Its total leaves out the premium tax credit and the Basic Health Program, so the table adds a row with the used credit and BHP put back. Its federal row counts only income and employee payroll taxes and the federal shares of Medicaid, CHIP and the Medicare Savings Programs; SNAP, school meals, WIC and other benefits sit in the unattributed row. It also includes items outside Fiscal Lab's figures: state shares of Medicaid, CHIP and the Medicare Savings Programs, state taxes and benefits, and other programs keyed to the poverty line, such as WIC, TANF and CSFP.

### Take-up and other inputs

- Medicaid: the dataset's `takes_up_medicaid_if_eligible` flag is true for everyone whose `has_medicaid_health_coverage_at_interview` is true (25.7 million people on 2024 weights) and for about 91 percent of everyone else (2024 weights). Enrollment is eligibility times the flag.
- CHIP, the Basic Health Program and the Medicare Savings Programs: every eligible person counts as enrolled.
- Premium tax credit: the dataset fixes take-up (`takes_up_aca_if_eligible`) and each unit's premium-to-benchmark ratio. The dataset records no plan category, so policyengine-us treats every unit as choosing a silver plan.
- SNAP: take-up is the dataset's `takes_up_snap_if_eligible` flag.
- Fiscal Lab's coverage model instead chooses each person's coverage, and moves people out of employer coverage.

[`scripts/dataset_facts.py`](scripts/dataset_facts.py) prints these shares from the 2024 source file, and [`scripts/facts.py`](scripts/facts.py) prints the inputs to the other derived figures from `outputs/`, including each run's Medicaid denominator record. The age-curve, $6,960 and 400 percent figures come from policyengine-us parameters (the 7.9 is that 400 percent times 1.97), and the 43 percent from the results table.

### Provenance

- Versions: policyengine 6.20.3 (the latest release when checked on 2026-11-26), which pins policyengine-us 2.2.2 (released 2026-11-09; the latest policyengine-us was 2.154.1 on 2026-11-26) and policyengine-core 3.34.10.
- Baselines for 2027 to 2029, 2031 and 2033 to 2036 ran on year data built in memory; the 2030 and 2032 baselines and every reform loaded the saved year file. In every year, each total a reform leaves unchanged matches the baseline exactly (14 of 26 totals for H.R. 4849; payroll tax for H.R. 1428), which holds only if both processes computed the same population. `facts.py` prints these sets and exits with an error if a set differs across years or a total comes within one part in a billion of the baseline without matching it.
- We reran every interrupted run and kept none of the interrupted outputs.
- policyengine-us pins the pre-2018 federal child tax credit that New York's Empire State Child Credit uses only through 2035, so policyengine-us computes New York's 2036 credit from the current-law federal credit (inferred from the pin's end date). That changes New York income tax in the 2036 runs, but no compared line.
- The runs used x86_64 CPython 3.13.13 under Rosetta on an arm64 Mac, and the bit-for-bit checks hold on that platform only. The year file's hash identifies one build of the file: a rebuild gives a new hash with identical totals.
- Fiscal Lab's figures come from its dashboard built November 21, 2026 (fetched 2026-11-24; extract sha256 6c955a3a…). Fiscal Lab rebuilt the dashboard on November 25, adding H.R. 4849 rows outside this comparison and renaming one; a refetch changed no compared row. Fiscal Lab's terms allow links and short excerpts only, so this repository quotes each compared line's ten-year total and a few other Fiscal Lab figures, and no yearly series.

## Reproduce

```bash
uv sync
uv run python scripts/fetch_fiscal_lab.py                                # Fiscal Lab's dashboard data, kept out of git
uv run python scripts/check_reforms.py                                   # parameter and household checks for each reform
uv run python scripts/run_year.py 2030 --sim baseline --out outputs-new  # one simulation for one calendar year
uv run python scripts/run_year.py 2030 --sim hr4849_coverage --out outputs-new
uv run python scripts/run_year.py 2030 --sim hr1428_poverty_line --out outputs-new
uv run python scripts/compare.py --outputs outputs-new --results results-new --tables tables-new
uv run python scripts/facts.py --outputs outputs-new                     # skips and lists years not yet run
```

- Run into a new output folder: `run_year.py` skips a simulation whose JSON already exists, and `outputs/` holds the committed results.
- Repeat the simulations for 2027 to 2036 (H.R. 1428 from 2030), running each year's baseline before its reforms. A reform reads the baseline's saved Medicaid denominator (`<out>/year_<year>/baseline.medicaid_slcsp_state_denominator.npz`, person-level and kept out of git) and stops if it is missing or comes from another year file.
- A run needs about 27 GB of free memory per process. 2027 takes about 6 minutes at about 11 GB; later years take 42 to 61 minutes at 20 to 25 GB, because New York's child credit computes a second federal credit from 2028. The first run downloads the 827 MB certified dataset.
- `run_year.py --sim <name> --sample 300 --out outputs-smoke` runs the same steps on 300 households. It checks only the output path: sample totals are not meaningful.
- Fetching today gets Fiscal Lab's November 25 build, which changes no compared row.
- `scripts/dataset_facts.py` reads the downloaded 2024 source file.
