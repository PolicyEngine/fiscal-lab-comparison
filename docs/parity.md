<!-- Copied from the private run notes on 2026-11-26. Aggregates only: totals, memory and counts. -->

# Denominator injection: parity with the unpatched runs

## baseline, 12000 households

- Commit 09a471c (dirty False); peak RSS 9.06 GB; simulation 849.7 s.
- Denominator record: `{"file": "baseline.medicaid_slcsp_state_denominator.npz", "persons": 34946, "distinct_values": 51}`
- Unpatched (commit 3d73379, dirty False): peak RSS 8.99 GB; simulation 630.4 s.
- Totals: 26 compared, 26 bit-identical, largest relative difference 0.

## hr1428_poverty_line, 12000 households

- Commit 09a471c (dirty False); peak RSS 9.59 GB; simulation 813.7 s.
- Denominator record: `{"file": "baseline.medicaid_slcsp_state_denominator.npz", "persons": 34946, "baseline_branch_requests": {"medicaid_slcsp_state_denominator": 1}}`
- Unpatched (commit 3d73379, dirty False): peak RSS 11.99 GB; simulation 736.7 s.
- Totals: 26 compared, 26 bit-identical, largest relative difference 0.

## hr4849_coverage, 12000 households

- Commit 09a471c (dirty False); peak RSS 9.71 GB; simulation 851.8 s.
- Denominator record: `{"file": "baseline.medicaid_slcsp_state_denominator.npz", "persons": 34946, "baseline_branch_requests": {"medicaid_slcsp_state_denominator": 1}}`
- Unpatched (commit 3d73379, dirty False): peak RSS 11.86 GB; simulation 737.3 s.
- Totals: 26 compared, 26 bit-identical, largest relative difference 0.

## baseline, 3000 households

- Commit 09a471c (dirty False); peak RSS 5.15 GB; simulation 362.6 s.
- Denominator record: `{"file": "baseline.medicaid_slcsp_state_denominator.npz", "persons": 8688, "distinct_values": 51}`
- Unpatched (commit 3d73379, dirty False): peak RSS 5.13 GB; simulation 248.4 s.
- Totals: 26 compared, 26 bit-identical, largest relative difference 0.

## hr1428_poverty_line, 3000 households

- Commit 09a471c (dirty False); peak RSS 5.73 GB; simulation 394.6 s.
- Denominator record: `{"file": "baseline.medicaid_slcsp_state_denominator.npz", "persons": 8688, "baseline_branch_requests": {"medicaid_slcsp_state_denominator": 1}}`
- No unpatched run at this size: fit point only.

## hr4849_coverage, 3000 households

- Commit 09a471c (dirty False); peak RSS 5.67 GB; simulation 384.9 s.
- Denominator record: `{"file": "baseline.medicaid_slcsp_state_denominator.npz", "persons": 8688, "baseline_branch_requests": {"medicaid_slcsp_state_denominator": 1}}`
- Unpatched (commit 3d73379, dirty False): peak RSS 6.99 GB; simulation 272.3 s.
- Totals: 26 compared, 26 bit-identical, largest relative difference 0.

## Largest absolute difference per total, across the pairs

| Total | Max abs difference |
|---|---:|
| aca_ptc | 0 |
| assigned_aca_ptc | 0 |
| basic_health_program | 0 |
| basic_health_program_enrolled | 0 |
| chip | 0 |
| chip_enrolled | 0 |
| chip_federal_cost | 0 |
| chip_state_cost | 0 |
| employee_payroll_tax | 0 |
| federal_benefit_cost | 0 |
| household_benefits | 0 |
| household_tax | 0 |
| income_tax | 0 |
| medicaid_cost | 0 |
| medicaid_enrolled | 0 |
| medicaid_federal_cost | 0 |
| medicaid_state_cost | 0 |
| msp_federal_cost | 0 |
| person_receives_aca | 0 |
| person_receives_aca_with_credit | 0 |
| school_meal_net_subsidy | 0 |
| snap | 0 |
| state_benefit_cost | 0 |
| state_income_tax | 0 |
| used_aca_ptc | 0 |
| wic | 0 |

## Injected memory fit (peak footprint in GiB at 57,240 households; pass limit 29 GiB for the reforms, whose unmodified code doubles the Medicaid work; the baseline was not held to it)

- baseline: 3,000: 4.77 GiB; 12,000: 9.08 GiB; slope 0.479 GiB per 1,000 households, intercept 3.33 GiB, full 30.8 GiB
- hr1428_poverty_line: 3,000: 5.31 GiB; 12,000: 8.91 GiB; slope 0.399 GiB per 1,000 households, intercept 4.11 GiB, full 27.0 GiB
- hr4849_coverage: 3,000: 5.26 GiB; 12,000: 9.02 GiB; slope 0.418 GiB per 1,000 households, intercept 4.00 GiB, full 27.9 GiB

This fit is a projection from the two sample sizes, made before the full runs. The full runs' measured peaks (`peak_rss_gb` in `outputs/year_*/*.json`, printed by `scripts/facts.py`) were about 11 GB in 2027 and 19.7 to 25.4 GB from 2028. Those are peak resident memory in decimal GB, a different measure from the footprint fit in GiB.

Verdict: PASS (5 pairs compared).


Each pair compared the patched run_year.py at commit 09a471c (the reform reads the baseline's saved denominator) with the unmodified code at commit 3d73379, on the same 2030 sample and year file. Commit 9f854e6 changes only scripts/compare.py and README.md relative to 09a471c (`git diff 09a471c 9f854e6 --stat`).
