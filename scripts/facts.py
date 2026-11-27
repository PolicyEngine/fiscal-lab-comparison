"""Print the inputs to the derived PolicyEngine figures the README cites, from outputs/.

Each figure is a reform-minus-baseline change, or a baseline level, read from
the per-simulation JSONs that run_year.py writes. Nothing here re-runs a
simulation. Dollar figures are calendar-year billions unless a line says
otherwise; people are millions. The folder must first pass compare.py's checks
(within each year, the same data, versions and clean commit). Years that lack
the baseline or a reform are skipped and listed.

Exits 1 when no year holds the baseline and every reform due; when a reform
leaves some total within one part in a billion of the baseline without matching
it exactly, which suggests two processes did not compute the same population;
or when the set of totals a reform leaves exactly unchanged differs across
years, which needs a look: either a policy effect that starts or stops, or two
processes that did not compute the same population.

Run: uv run python scripts/facts.py [--outputs DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare import FIRST_YEAR as REFORMS, YEARS, load_pe  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def load(outputs: Path) -> dict[int, dict[str, dict]]:
    """Full run records per year, for years holding the baseline and every reform due that year."""
    load_pe(outputs)  # compare.py's checks; exits on a failure
    runs: dict[int, dict[str, dict]] = {}
    for year in YEARS:
        sims = {}
        for path in sorted((outputs / f"year_{year}").glob("*.json")):
            if path.name.endswith((".defaults.json", ".partial.json")):
                continue
            run = json.loads(path.read_text())
            sims[run["simulation"]] = run
        wanted = {"baseline"} | {r for r, first in REFORMS.items() if year >= first}
        if wanted <= set(sims):
            runs[year] = sims
    return runs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outputs", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()
    runs = load(args.outputs)
    years = [y for y in YEARS if y in runs]
    skipped = [y for y in YEARS if y not in runs]
    print(f"Years with the baseline and every reform due: {', '.join(map(str, years)) or 'none'}")
    if skipped:
        print(f"Skipped (incomplete): {', '.join(map(str, skipped))}")
    if not years:
        raise SystemExit("no year has the baseline and every reform due")

    def tot(year: int, sim: str, var: str) -> float:
        return runs[year][sim]["totals"][var]

    def d(year: int, reform: str, var: str) -> float:
        return tot(year, reform, var) - tot(year, "baseline", var)

    def reform_years(reform: str) -> list[int]:
        return [y for y in years if y >= REFORMS[reform]]

    print("\nBaseline Medicaid: total cost ($B), enrollment (M), cost and federal cost per enrollee ($)")
    for y in years:
        cost, fed, n = (tot(y, "baseline", v) for v in ("medicaid_cost", "medicaid_federal_cost", "medicaid_enrolled"))
        print(f"  {y}: {cost / 1e9:,.2f}  {n / 1e6:.3f}  {cost / n:,.0f}  {fed / n:,.0f}")

    for reform in REFORMS:
        print(
            f"\n{reform}: change in Medicaid cost per added enrollee ($) and its ratio to the baseline average, "
            "federal share of the cost change, CHIP changes"
        )
        for y in reform_years(reform):
            dn = d(y, reform, "medicaid_enrolled")
            dc, df = d(y, reform, "medicaid_cost"), d(y, reform, "medicaid_federal_cost")
            avg = tot(y, "baseline", "medicaid_cost") / tot(y, "baseline", "medicaid_enrolled")
            chip = [d(y, reform, v) for v in ("chip", "chip_enrolled", "chip_federal_cost", "chip_state_cost")]
            print(
                f"  {y}: total {dc / dn:,.0f} ({dc / dn / avg:.3f} x average), federal {df / dn:,.0f}, "
                f"federal share {df / dc:.4f}; Medicaid enrolled {dn / 1e6:+.3f} M; chip ${chip[0] / 1e9:+.2f}B, "
                f"chip_enrolled {chip[1] / 1e6:+.3f} M, chip federal ${chip[2] / 1e9:+.2f}B, chip state ${chip[3] / 1e9:+.2f}B"
            )

    print("\nBasic Health Program: baseline $B and enrollment (M); reform changes")
    for y in years:
        line = (
            f"  {y}: baseline {tot(y, 'baseline', 'basic_health_program') / 1e9:.2f}, "
            f"{tot(y, 'baseline', 'basic_health_program_enrolled') / 1e6:.3f} M"
        )
        for reform in REFORMS:
            if y >= REFORMS[reform]:
                line += (
                    f"; {reform} {d(y, reform, 'basic_health_program') / 1e9:+.2f}, "
                    f"{d(y, reform, 'basic_health_program_enrolled') / 1e6:+.3f} M"
                )
        print(line)

    print("\nPremium tax credit changes, $B (used, assigned, aca_ptc), and subsidized Marketplace enrollment change (M)")
    for reform in REFORMS:
        for y in reform_years(reform):
            print(
                f"  {reform} {y}: used {d(y, reform, 'used_aca_ptc') / 1e9:+.2f}, "
                f"assigned {d(y, reform, 'assigned_aca_ptc') / 1e9:+.2f}, aca_ptc {d(y, reform, 'aca_ptc') / 1e9:+.2f}; "
                f"subsidized {d(y, reform, 'person_receives_aca_with_credit') / 1e6:+.2f} M"
            )

    print(
        "\nH.R. 1428 SNAP change by calendar year, $B (calendar 2030: mostly October to December, not computed; broad-based "
        "categorical eligibility moves earlier in ME, MA, OR and WA)"
    )
    for y in reform_years("hr1428_poverty_line"):
        print(f"  {y}: {d(y, 'hr1428_poverty_line', 'snap') / 1e9:+.2f}")

    print(
        "\nTotals each reform leaves exactly equal to the baseline (in-memory and file-loaded runs agree on them only if "
        "they computed the same population), and totals within one part in a billion of the baseline but not exactly equal (expect none)"
    )
    failures = []
    for reform in REFORMS:
        exact_by_year = {}
        for y in reform_years(reform):
            b, r = runs[y]["baseline"]["totals"], runs[y][reform]["totals"]
            exact_by_year[y] = tuple(sorted(v for v in b if r[v] == b[v]))
            near = sorted(v for v in b if r[v] != b[v] and abs(r[v] - b[v]) <= 1e-9 * max(abs(b[v]), 1.0))
            print(f"  {reform} {y}: {len(exact_by_year[y])} of {len(b)} exact; near but not exact: {near or 'none'}")
            if near:
                failures.append(f"{reform} {y}: within one part in a billion of the baseline but not equal: {', '.join(near)}")
        sets = set(exact_by_year.values())
        if len(sets) == 1:
            print(f"    exact in every year: {', '.join(next(iter(sets)))}")
        elif sets:
            for y, exact in exact_by_year.items():
                print(f"    exact in {y}: {', '.join(exact)}")
            failures.append(f"{reform}: the set of exactly unchanged totals differs across years")

    print(
        "\nRuns: dataset source (a UUID id loaded the saved year file; populace_us_2024_year_<Y> built it in memory), "
        "peak RSS GB, minutes, commit, Medicaid denominator record"
    )
    for y in years:
        for sim, run in sorted(runs[y].items()):
            source = "in memory" if run["dataset"]["id"].startswith("populace_us_2024_year_") else "saved file"
            if run.get("denominator_saved"):
                den = run["denominator_saved"]
                den_text = f"saved ({den['persons']:,} person records, {den['distinct_values']} distinct values)"
            elif run.get("denominator_injected"):
                den = run["denominator_injected"]
                den_text = f"injected ({den['persons']:,} person records, baseline-branch requests {den['baseline_branch_requests']})"
            else:
                den_text = "none"
            print(
                f"  {y} {sim}: {source}; {run['peak_rss_gb']} GB; {run['timing_seconds']['all'] / 60:.0f} min; "
                f"commit {run['repo']['commit'][:7]} dirty={run['repo']['dirty']}; denominator {den_text}"
            )

    if failures:
        print("\nFAIL\n  " + "\n  ".join(failures))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
