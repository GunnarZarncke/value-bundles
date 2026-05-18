#!/usr/bin/env python3
"""Analyze CSV output from run_barter_mve.py.

The runner intentionally emits a minimal CSV with the requested experiment
metrics. This helper keeps evaluation separate: it aggregates train-final and
held-out rows across seeds, reports simple uncertainty estimates, and checks the
main predicted ordering C1 > C2 > C3 for welfare, trade success, and symbol
mutual-information metrics.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


METRICS = [
    "success_rate",
    "opportunity_rate",
    "success_given_opportunity",
    "welfare_gain",
    "welfare_capture",
    "chosen_symbol_candidate_rate",
    "chosen_random_candidate_rate",
    "symbol_candidate_win_rate",
    "random_candidate_win_rate",
    "candidate_comparison_rate",
    "mi_symbol_outcome",
    "mi_symbol_transfer",
    "symbol_entropy",
    "consistency_loss",
    "transfer_consistency_loss",
    "quantity_axis_stability",
    "quantity_axis_spread",
]
CONDITIONS = ("C1", "C2", "C3", "C4")
PHASES = ("train_final", "heldout")
LOWER_IS_BETTER = {"transfer_consistency_loss", "consistency_loss"}


@dataclass(frozen=True)
class EvaluationResult:
    """Aggregated value for one phase/condition/metric."""

    phase: str
    condition: str
    metric: str
    mean: float
    stderr: float
    n: int


def mean(values: Sequence[float]) -> float:
    if not values:
        return float("nan")
    return sum(values) / len(values)


def stderr(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = mean(values)
    variance = sum((value - mu) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance / len(values))


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def split_final_rows(rows: Sequence[Mapping[str, str]], train_episodes: int) -> Dict[str, List[Mapping[str, str]]]:
    """Select final training rows and held-out rows for each condition/seed.

    The experiment CSV deliberately preserves the minimal requested columns, so
    the analyzer uses the known training episode count to identify held-out rows.
    For each seed/condition, the final row with episode <= train_episodes is the
    train-final row; the final row with episode > train_episodes is held-out.
    """
    grouped: Dict[Tuple[str, str], List[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["condition"], row["seed"])].append(row)

    selected = {phase: [] for phase in PHASES}
    for condition_seed, group in grouped.items():
        sorted_group = sorted(group, key=lambda row: int(row["episode"]))
        train_rows = [row for row in sorted_group if int(row["episode"]) <= train_episodes]
        heldout_rows = [row for row in sorted_group if int(row["episode"]) > train_episodes]
        if train_rows:
            selected["train_final"].append(train_rows[-1])
        if heldout_rows:
            selected["heldout"].append(heldout_rows[-1])
    return selected


def aggregate(rows_by_phase: Mapping[str, Sequence[Mapping[str, str]]]) -> List[EvaluationResult]:
    results: List[EvaluationResult] = []
    for phase in PHASES:
        rows = rows_by_phase.get(phase, [])
        for condition in CONDITIONS:
            condition_rows = [row for row in rows if row["condition"] == condition]
            for metric in METRICS:
                values = [float(row[metric]) for row in condition_rows if metric in row]
                results.append(
                    EvaluationResult(
                        phase=phase,
                        condition=condition,
                        metric=metric,
                        mean=mean(values),
                        stderr=stderr(values),
                        n=len(values),
                    )
                )
    return results


def result_lookup(results: Iterable[EvaluationResult]) -> Dict[Tuple[str, str, str], EvaluationResult]:
    return {(result.phase, result.condition, result.metric): result for result in results}


def ordering_status(lookup: Mapping[Tuple[str, str, str], EvaluationResult], phase: str, metric: str) -> str:
    c1 = lookup[(phase, "C1", metric)].mean
    c2 = lookup[(phase, "C2", metric)].mean
    c3 = lookup[(phase, "C3", metric)].mean
    if math.isnan(c1) or math.isnan(c2) or math.isnan(c3):
        return "not available"
    if metric in LOWER_IS_BETTER:
        if c1 < c2 < c3:
            return "supports C1 < C2 < C3 (lower is better)"
        if c1 < c2 and c1 < c3:
            return "partially supports: C1 is best, but C2 < C3 fails"
        return "does not support C1 < C2 < C3 (lower is better)"
    if c1 > c2 > c3:
        return "supports C1 > C2 > C3"
    if c1 > c2 and c1 > c3:
        return "partially supports: C1 is best, but C2 > C3 fails"
    return "does not support C1 > C2 > C3"




def behavior_gate_status(
    lookup: Mapping[Tuple[str, str, str], EvaluationResult],
    *,
    success_margin: float,
    welfare_margin: float,
) -> Tuple[bool, str]:
    """Return whether symbolic metrics should count under a behavior-first gate."""
    c1_success = lookup[("heldout", "C1", "success_rate")].mean
    c2_success = lookup[("heldout", "C2", "success_rate")].mean
    c3_success = lookup[("heldout", "C3", "success_rate")].mean
    c1_welfare = lookup[("heldout", "C1", "welfare_gain")].mean
    c2_welfare = lookup[("heldout", "C2", "welfare_gain")].mean
    c3_welfare = lookup[("heldout", "C3", "welfare_gain")].mean
    success_pass = c1_success - max(c2_success, c3_success) >= success_margin
    welfare_pass = c1_welfare - max(c2_welfare, c3_welfare) >= welfare_margin
    status = (
        f"held-out success Δ={c1_success - max(c2_success, c3_success):.4f} "
        f"(threshold {success_margin:.4f}); held-out welfare Δ={c1_welfare - max(c2_welfare, c3_welfare):.4f} "
        f"(threshold {welfare_margin:.4f})"
    )
    return success_pass or welfare_pass, status


def format_markdown(
    results: Sequence[EvaluationResult],
    *,
    source: Path,
    train_episodes: int,
    success_margin: float,
    welfare_margin: float,
) -> str:
    lookup = result_lookup(results)
    lines = [
        "# Bounded Barter MVE Evaluation",
        "",
        f"Source CSV: `{source}`",
        f"Training episodes used to identify held-out rows: `{train_episodes}`",
        "",
        "## Aggregate metrics",
        "",
    ]
    for phase in PHASES:
        lines.extend(
            [
                f"### {phase}",
                "",
                "| condition | " + " | ".join(METRICS) + " | n |",
                "| --- | " + " | ".join(["---:"] * len(METRICS)) + " | ---: |",
            ]
        )
        for condition in CONDITIONS:
            row_results = [lookup[(phase, condition, metric)] for metric in METRICS]
            n = row_results[0].n
            formatted = [f"{result.mean:.4f} ± {result.stderr:.4f}" for result in row_results]
            lines.append(f"| {condition} | " + " | ".join(formatted) + f" | {n} |")
        lines.append("")

    lines.extend(
        [
            "## Predicted-ordering checks",
            "",
            "The primary falsifiable prediction is C1 > C2 > C3 under bounded compute.",
            "",
            "| phase | metric | result |",
            "| --- | --- | --- |",
        ]
    )
    for phase in PHASES:
        for metric in (
            "success_rate",
            "welfare_gain",
            "mi_symbol_outcome",
            "chosen_symbol_candidate_rate",
            "symbol_candidate_win_rate",
            "candidate_comparison_rate",
            "success_given_opportunity",
            "welfare_capture",
            "mi_symbol_transfer",
            "transfer_consistency_loss",
            "quantity_axis_stability",
            "quantity_axis_spread",
        ):
            lines.append(f"| {phase} | {metric} | {ordering_status(lookup, phase, metric)} |")
    lines.append("")

    gate_passed, gate_text = behavior_gate_status(
        lookup, success_margin=success_margin, welfare_margin=welfare_margin
    )
    gate_verdict = "PASS" if gate_passed else "FAIL"
    lines.extend(
        [
            "## Behavior-first gate",
            "",
            "Symbolic/quantity metrics count as evidence only if C1 also clears a held-out behavior margin over both C2 and C3.",
            f"- Gate: {gate_verdict}",
            f"- {gate_text}",
            "",
            "## Interpretation",
            "",
            "- Treat these checks as descriptive, not as formal hypothesis tests. The experiment is stochastic and intentionally minimal.",
            "- C4 is not expected to need symbols: when unbounded agents can scan all feasible transfers, high welfare can coexist with low symbol-transfer mutual information.",
            "- `opportunity_rate` estimates how often any beneficial one-way transfer existed; `success_given_opportunity` and `welfare_capture` normalize behavior against that oracle opportunity.",
            "- Candidate-source metrics track whether chosen bounded-search options came from symbol prototypes or random sampling, and whether the best available symbol-guided candidate beat the best random candidate when both existed.",
            "- Lower transfer consistency loss means each symbol maps to a tighter transfer-magnitude prototype; higher quantity-axis stability/spread indicate more math-like post-hoc structure.",
            "- Symbolic metrics should be treated as secondary diagnostics unless the behavior-first gate passes.",
            "- If C1 fails to exceed C2/C3, the minimum viable claim is not supported for that configuration; tune the environment pressure rather than adding formal machinery.",
            "",
        ]
    )
    return "\n".join(lines)


def write_summary_csv(results: Sequence[EvaluationResult], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["phase", "condition", "metric", "mean", "stderr", "n"])
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "phase": result.phase,
                    "condition": result.condition,
                    "metric": result.metric,
                    "mean": f"{result.mean:.8f}",
                    "stderr": f"{result.stderr:.8f}",
                    "n": result.n,
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="CSV produced by run_barter_mve.py")
    parser.add_argument("--episodes", type=int, default=10_000, help="training episodes used in the run")
    parser.add_argument("--success-margin", type=float, default=0.03, help="required held-out C1 success-rate margin over C2/C3 before symbolic metrics count")
    parser.add_argument("--welfare-margin", type=float, default=0.05, help="required held-out C1 welfare-gain margin over C2/C3 before symbolic metrics count")
    parser.add_argument("--markdown-output", type=Path, help="optional path for markdown report")
    parser.add_argument("--summary-csv", type=Path, help="optional path for aggregate CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_rows(args.csv)
    rows_by_phase = split_final_rows(rows, args.episodes)
    results = aggregate(rows_by_phase)
    markdown = format_markdown(
        results,
        source=args.csv,
        train_episodes=args.episodes,
        success_margin=args.success_margin,
        welfare_margin=args.welfare_margin,
    )
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown + "\n")
    if args.summary_csv:
        write_summary_csv(results, args.summary_csv)
    print(markdown)


if __name__ == "__main__":
    main()
