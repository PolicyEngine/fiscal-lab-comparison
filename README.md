# Fiscal Lab and PolicyEngine on the same bills

Work in progress. This repository runs PolicyEngine's US microsimulation on parts of two bills that Fiscal Lab on Capitol Hill scored in November 2026, and compares the results line by line with Fiscal Lab's published components:

- H.R. 4849, the Protecting Health Care and Lowering Costs Act of 2025: its coverage provisions (the permanent enhanced premium tax credit and the repeal of the One Big Beautiful Bill Act's Medicaid work requirement and immigrant limits).
- H.R. 1428, the Poverty Line Act of 2025: a higher federal poverty guideline from 2030.

Results will appear here after independent review.

## Reproduce

```bash
uv sync
uv run python scripts/fetch_fiscal_lab.py   # Fiscal Lab's dashboard data, kept out of git
uv run python scripts/check_reforms.py      # parameter and household checks for each reform
```

PolicyEngine runs use the latest `policyengine` release (6.20.3, which pins policyengine-us 2.2.2) and its certified Microcosm dataset.
