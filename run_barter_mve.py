#!/usr/bin/env python3
"""Minimum viable bounded-barter experiment.

This script tests whether shared symbols plus behavioral consistency pressure
help bounded agents discover compact, quantity-like trade representations.
It intentionally avoids explicit predicates, theorem proving, graph worlds,
multi-resource bundles, and hard-coded symbol meanings.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Sequence, Tuple


CONDITIONS = {
    "C1": {"bounded": True, "communication": True, "consistency": True, "shuffle": False},
    "C2": {"bounded": True, "communication": True, "consistency": False, "shuffle": False},
    "C3": {"bounded": True, "communication": False, "consistency": False, "shuffle": True},
    "C4": {"bounded": False, "communication": True, "consistency": True, "shuffle": False},
}

CSV_FIELDS = [
    "episode",
    "condition",
    "seed",
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

Record = Tuple[int, int, int, int, int, int, float, float]
MetricEvent = Tuple[int, int, int, int, int, int, int, int, int]
RANDOM_CANDIDATE = 1
SYMBOL_CANDIDATE = 2
NO_CANDIDATE_TOTAL = -10**9


def utility(q: int, need: int) -> int:
    """Peaked one-resource utility."""
    return -abs(q - need)


def trade_delta(q_a: int, q_b: int, n_a: int, n_b: int, k: int) -> Tuple[int, int, int]:
    """Return (delta_a, delta_b, total_delta) for transferring k from A to B."""
    before_a = utility(q_a, n_a)
    before_b = utility(q_b, n_b)
    after_a = utility(q_a - k, n_a)
    after_b = utility(q_b + k, n_b)
    delta_a = after_a - before_a
    delta_b = after_b - before_b
    return delta_a, delta_b, delta_a + delta_b


def entropy_from_counts(counts: Iterable[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    result = 0.0
    for count in counts:
        if count:
            p = count / total
            result -= p * math.log2(p)
    return result


def mutual_information(pairs: Sequence[Tuple[int, int]]) -> float:
    """Discrete mutual information in bits for a sequence of (x, y) pairs."""
    if not pairs:
        return 0.0
    joint = Counter(pairs)
    x_counts = Counter(x for x, _ in pairs)
    y_counts = Counter(y for _, y in pairs)
    total = len(pairs)
    mi = 0.0
    for (x, y), count in joint.items():
        p_xy = count / total
        p_x = x_counts[x] / total
        p_y = y_counts[y] / total
        mi += p_xy * math.log2(p_xy / (p_x * p_y))
    return mi


def variance(values: Sequence[float]) -> float:
    """Population variance for tiny bounded memories."""
    if not values:
        return 0.0
    mu = sum(values) / len(values)
    return sum((value - mu) ** 2 for value in values) / len(values)


def rank_order(values: Sequence[float]) -> List[float]:
    """Average ranks for Spearman correlation, with ties handled deterministically."""
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(indexed):
        end = cursor + 1
        while end < len(indexed) and indexed[end][1] == indexed[cursor][1]:
            end += 1
        avg_rank = (cursor + end - 1) / 2
        for index, _ in indexed[cursor:end]:
            ranks[index] = avg_rank
        cursor = end
    return ranks


def spearman_correlation(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman rank correlation for post-hoc quantity-axis stability."""
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    x_ranks = rank_order(xs)
    y_ranks = rank_order(ys)
    x_var = variance(x_ranks)
    y_var = variance(y_ranks)
    if x_var == 0 or y_var == 0:
        return 0.0
    x_mean = sum(x_ranks) / len(x_ranks)
    y_mean = sum(y_ranks) / len(y_ranks)
    covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_ranks, y_ranks)) / len(x_ranks)
    return covariance / math.sqrt(x_var * y_var)


@dataclass
class SymbolMemory:
    """Small prototype store for one initially meaningless symbol."""

    limit: int
    records: Deque[Record] = field(default_factory=deque)

    def add(self, record: Record) -> None:
        self.records.append(record)
        while len(self.records) > self.limit:
            self.records.popleft()

    def mean_k(self) -> float | None:
        if not self.records:
            return None
        return sum(record[5] for record in self.records) / len(self.records)

    def mean_gain(self) -> float:
        if not self.records:
            return 0.0
        return sum(record[6] + record[7] for record in self.records) / len(self.records)

    def outcome_entropy(self) -> float:
        signs = Counter(1 if record[6] + record[7] > 0 else 0 for record in self.records)
        return entropy_from_counts(signs.values())

    def transfer_variance(self) -> float:
        return variance([float(record[5]) for record in self.records])

    def normalized_transfer_variance(self) -> float:
        # With k in [0, 20], the maximum possible population variance is 100.
        return self.transfer_variance() / 100

    def prototype_ks(self) -> List[int]:
        return [record[5] for record in self.records]


class BarterRun:
    """One condition/seed run of the bounded barter world."""

    def __init__(
        self,
        *,
        condition: str,
        seed: int,
        agents: int,
        symbols: int,
        compute_budget: int,
        prototype_memory: int,
        train_max: int,
        consistency_weight: float = 0.75,
        transfer_consistency_weight: float = 0.0,
        transfer_consistency_min_records: int = 0,
        transfer_consistency_warmup: int = 0,
        transfer_consistency_anneal: int = 0,
        prototype_candidates: int = 2,
        random_option_set_size: int = 0,
        candidate_source_mode: str = "mixed_all",
    ) -> None:
        self.condition = condition
        self.config = CONDITIONS[condition]
        self.rng = random.Random(seed)
        self.agents = agents
        self.symbols = symbols
        self.compute_budget = compute_budget
        self.prototype_memory = prototype_memory
        self.train_max = train_max
        self.prototype_candidates = max(0, prototype_candidates)
        self.random_option_set_size = max(0, random_option_set_size)
        self.candidate_source_mode = candidate_source_mode
        self.memories = [SymbolMemory(prototype_memory) for _ in range(symbols)]
        self.events: List[MetricEvent] = []
        self.recent_events: List[MetricEvent] = []
        self.episode_count = 0
        self.consistency_weight = consistency_weight
        self.transfer_consistency_weight = transfer_consistency_weight
        self.transfer_consistency_min_records = max(0, transfer_consistency_min_records)
        self.transfer_consistency_warmup = max(0, transfer_consistency_warmup)
        self.transfer_consistency_anneal = max(0, transfer_consistency_anneal)

    def sample_state(self, held_out: bool = False) -> Tuple[int, int, int, int]:
        if held_out:
            lo, hi = self.train_max + 1, 20
        else:
            lo, hi = 0, self.train_max
        return tuple(self.rng.randint(lo, hi) for _ in range(4))  # type: ignore[return-value]

    def effective_transfer_consistency_weight(self, memory: SymbolMemory) -> float:
        if len(memory.records) < self.transfer_consistency_min_records:
            return 0.0
        if self.episode_count < self.transfer_consistency_warmup:
            return 0.0
        if self.transfer_consistency_anneal <= 0:
            return self.transfer_consistency_weight
        progress = (self.episode_count - self.transfer_consistency_warmup) / self.transfer_consistency_anneal
        return self.transfer_consistency_weight * max(0.0, min(1.0, progress))

    def choose_symbol(self, desired_k: int) -> int:
        candidates = list(range(self.symbols))
        if self.config["bounded"]:
            self.rng.shuffle(candidates)
            candidates = candidates[: max(1, min(self.compute_budget, self.symbols))]
        if not self.config["communication"] or self.config["shuffle"]:
            return self.rng.choice(candidates)
        if not self.config["consistency"]:
            # Communication without consistency pressure has no reason to keep a
            # compact, stable code; it explores symbols but still lets receiver
            # learn whatever accidental prototypes result.
            return self.rng.choice(candidates)

        def score(symbol: int) -> float:
            memory = self.memories[symbol]
            mean_k = memory.mean_k()
            if mean_k is None:
                return self.rng.uniform(-0.05, 0.05)
            scale = max(1, 20)
            distance_loss = abs(mean_k - desired_k) / scale
            return (
                memory.mean_gain()
                - distance_loss
                - self.consistency_weight * memory.outcome_entropy()
                - self.effective_transfer_consistency_weight(memory) * memory.normalized_transfer_variance()
            )

        return max(candidates, key=score)

    def receiver_symbol(self, sent_symbol: int) -> int:
        if self.config["shuffle"]:
            return self.rng.randrange(self.symbols)
        return sent_symbol

    def random_option_pool(self, feasible: Sequence[int]) -> List[int]:
        if not self.random_option_set_size or self.random_option_set_size >= len(feasible):
            return list(feasible)
        return self.rng.sample(list(feasible), self.random_option_set_size)

    def symbol_candidate_slots(self, candidate_limit: int) -> int:
        if self.candidate_source_mode == "random_only":
            return 0
        if self.candidate_source_mode == "symbol_only":
            return candidate_limit
        if self.candidate_source_mode == "mixed_1_symbol":
            return min(1, candidate_limit)
        if self.candidate_source_mode == "mixed_2_symbol":
            return min(2, candidate_limit)
        return min(self.prototype_candidates, candidate_limit)

    def symbol_option_pool(self, q_a: int, received_symbol: int, limit: int) -> List[int]:
        if not (self.config["communication"] and not self.config["shuffle"] and limit):
            return []
        memory = self.memories[received_symbol]
        candidates = []
        mean_k = memory.mean_k()
        if mean_k is not None:
            candidates.append(max(0, min(q_a, round(mean_k))))
        for prototype_k in reversed(memory.prototype_ks()):
            candidates.append(max(0, min(q_a, prototype_k)))
        unique = []
        for candidate in candidates:
            if candidate not in unique:
                unique.append(candidate)
            if len(unique) >= limit:
                break
        return unique

    def candidate_transfers_with_sources(self, q_a: int, received_symbol: int) -> Dict[int, int]:
        feasible = list(range(0, q_a + 1))
        if not self.config["bounded"]:
            return {k: RANDOM_CANDIDATE for k in feasible}

        option_pool = self.random_option_pool(feasible)
        candidate_limit = min(self.compute_budget, len(feasible))
        symbol_slots = self.symbol_candidate_slots(candidate_limit)
        candidate_sources: Dict[int, int] = {}

        for k in self.symbol_option_pool(q_a, received_symbol, symbol_slots):
            candidate_sources[k] = candidate_sources.get(k, 0) | SYMBOL_CANDIDATE

        random_target = 0 if self.candidate_source_mode == "symbol_only" else candidate_limit
        while len(candidate_sources) < random_target:
            random_options = [
                k for k in option_pool if not candidate_sources.get(k, 0) & RANDOM_CANDIDATE
            ]
            if not random_options:
                break
            k = self.rng.choice(random_options)
            candidate_sources[k] = candidate_sources.get(k, 0) | RANDOM_CANDIDATE

        while len(candidate_sources) > candidate_limit:
            k = self.rng.choice(tuple(candidate_sources))
            del candidate_sources[k]
        if not candidate_sources:
            candidate_sources[0] = RANDOM_CANDIDATE
        return candidate_sources

    def candidate_transfers(self, q_a: int, received_symbol: int) -> List[int]:
        return sorted(self.candidate_transfers_with_sources(q_a, received_symbol))

    def oracle_best_total(self, q_a: int, q_b: int, n_a: int, n_b: int) -> int:
        return max(trade_delta(q_a, q_b, n_a, n_b, k)[2] for k in range(0, q_a + 1))

    def choose_transfer(
        self, q_a: int, q_b: int, n_a: int, n_b: int, received_symbol: int
    ) -> Tuple[int, int, int, int, int, int, int]:
        candidate_sources = self.candidate_transfers_with_sources(q_a, received_symbol)
        scored = []
        best_symbol_total = NO_CANDIDATE_TOTAL
        best_random_total = NO_CANDIDATE_TOTAL
        for k, source in candidate_sources.items():
            delta_a, delta_b, total = trade_delta(q_a, q_b, n_a, n_b, k)
            scored.append((total, delta_a, delta_b, k, source))
            if source & SYMBOL_CANDIDATE:
                best_symbol_total = max(best_symbol_total, total)
            if source & RANDOM_CANDIDATE:
                best_random_total = max(best_random_total, total)
        total, delta_a, delta_b, k, source = max(scored)
        if total <= 0:
            return 0, 0, 0, 0, 0, best_symbol_total, best_random_total
        return k, delta_a, delta_b, total, source, best_symbol_total, best_random_total

    def step(self, held_out: bool = False) -> None:
        self.episode_count += 1
        # Agent identities are sampled to keep the interface faithful to the MVE,
        # but the intentionally tiny first experiment uses shared symbol memories.
        self.rng.sample(range(self.agents), 2)
        q_a, q_b, n_a, n_b = self.sample_state(held_out=held_out)
        desired_k = max(0, min(q_a, q_a - n_a))
        sent_symbol = self.choose_symbol(desired_k)
        received_symbol = self.receiver_symbol(sent_symbol)
        k, delta_a, delta_b, total, source, best_symbol_total, best_random_total = self.choose_transfer(
            q_a, q_b, n_a, n_b, received_symbol
        )
        oracle_total = self.oracle_best_total(q_a, q_b, n_a, n_b)

        record = (q_a, q_b, n_a, n_b, received_symbol, k, float(delta_a), float(delta_b))
        if not held_out:
            self.memories[received_symbol].add(record)
        event = (
            received_symbol,
            1 if total > 0 else 0,
            k,
            total,
            1 if oracle_total > 0 else 0,
            oracle_total,
            source,
            best_symbol_total,
            best_random_total,
        )
        self.events.append(event)
        self.recent_events.append(event)

    def consistency_loss(self) -> float:
        losses = [memory.outcome_entropy() for memory in self.memories if memory.records]
        if not losses:
            return 0.0
        return sum(losses) / len(losses)

    def transfer_consistency_loss(self) -> float:
        losses = [memory.normalized_transfer_variance() for memory in self.memories if memory.records]
        if not losses:
            return 0.0
        return sum(losses) / len(losses)

    def quantity_axis_spread(self) -> float:
        means = [memory.mean_k() for memory in self.memories if memory.mean_k() is not None]
        if len(means) < 2:
            return 0.0
        return (max(means) - min(means)) / 20

    def quantity_axis_stability(self, events: Sequence[MetricEvent]) -> float:
        recent_by_symbol: Dict[int, List[float]] = {}
        for symbol, _, k, _, _, _, _, _, _ in events:
            recent_by_symbol.setdefault(symbol, []).append(float(k))
        memory_means = []
        recent_means = []
        for symbol, recent_ks in recent_by_symbol.items():
            memory_mean = self.memories[symbol].mean_k()
            if memory_mean is not None:
                memory_means.append(memory_mean)
                recent_means.append(sum(recent_ks) / len(recent_ks))
        # Map Spearman [-1, 1] to [0, 1] so higher always means a more stable
        # post-hoc quantity axis across prototype memory and evaluation events.
        return (spearman_correlation(memory_means, recent_means) + 1) / 2

    def metrics(self, episode: int, seed: int, recent: bool = True) -> Dict[str, object]:
        events = self.recent_events if recent else self.events
        if not events:
            success_rate = opportunity_rate = success_given_opportunity = 0.0
            welfare_gain = welfare_capture = symbol_entropy = 0.0
            chosen_symbol_candidate_rate = chosen_random_candidate_rate = 0.0
            symbol_candidate_win_rate = random_candidate_win_rate = candidate_comparison_rate = 0.0
            mi_outcome = mi_transfer = quantity_axis_stability = 0.0
        else:
            successes = sum(outcome for _, outcome, _, _, _, _, _, _, _ in events)
            opportunities = sum(oracle_good for _, _, _, _, oracle_good, _, _, _, _ in events)
            welfare_gain = sum(total for _, _, _, total, _, _, _, _, _ in events) / len(events)
            oracle_welfare = (
                sum(max(0, oracle_total) for _, _, _, _, _, oracle_total, _, _, _ in events)
                / len(events)
            )
            success_rate = successes / len(events)
            opportunity_rate = opportunities / len(events)
            success_given_opportunity = successes / opportunities if opportunities else 0.0
            welfare_capture = welfare_gain / oracle_welfare if oracle_welfare else 0.0
            chosen_symbol_candidate_rate = (
                sum(1 for *_, source, __, ___ in events if source & SYMBOL_CANDIDATE) / len(events)
            )
            chosen_random_candidate_rate = (
                sum(1 for *_, source, __, ___ in events if source & RANDOM_CANDIDATE) / len(events)
            )
            comparable = [
                (best_symbol, best_random)
                for *_, best_symbol, best_random in events
                if best_symbol != NO_CANDIDATE_TOTAL and best_random != NO_CANDIDATE_TOTAL
            ]
            candidate_comparison_rate = len(comparable) / len(events)
            symbol_candidate_win_rate = (
                sum(1 for best_symbol, best_random in comparable if best_symbol > best_random) / len(comparable)
                if comparable
                else 0.0
            )
            random_candidate_win_rate = (
                sum(1 for best_symbol, best_random in comparable if best_random > best_symbol) / len(comparable)
                if comparable
                else 0.0
            )
            mi_outcome = mutual_information([(symbol, outcome) for symbol, outcome, _, _, _, _, _, _, _ in events])
            mi_transfer = mutual_information([(symbol, k) for symbol, _, k, _, _, _, _, _, _ in events])
            symbol_entropy = entropy_from_counts(
                Counter(symbol for symbol, _, _, _, _, _, _, _, _ in events).values()
            )
            quantity_axis_stability = self.quantity_axis_stability(events)
        return {
            "episode": episode,
            "condition": self.condition,
            "seed": seed,
            "success_rate": f"{success_rate:.6f}",
            "opportunity_rate": f"{opportunity_rate:.6f}",
            "success_given_opportunity": f"{success_given_opportunity:.6f}",
            "welfare_gain": f"{welfare_gain:.6f}",
            "welfare_capture": f"{welfare_capture:.6f}",
            "chosen_symbol_candidate_rate": f"{chosen_symbol_candidate_rate:.6f}",
            "chosen_random_candidate_rate": f"{chosen_random_candidate_rate:.6f}",
            "symbol_candidate_win_rate": f"{symbol_candidate_win_rate:.6f}",
            "random_candidate_win_rate": f"{random_candidate_win_rate:.6f}",
            "candidate_comparison_rate": f"{candidate_comparison_rate:.6f}",
            "mi_symbol_outcome": f"{mi_outcome:.6f}",
            "mi_symbol_transfer": f"{mi_transfer:.6f}",
            "symbol_entropy": f"{symbol_entropy:.6f}",
            "consistency_loss": f"{self.consistency_loss():.6f}",
            "transfer_consistency_loss": f"{self.transfer_consistency_loss():.6f}",
            "quantity_axis_stability": f"{quantity_axis_stability:.6f}",
            "quantity_axis_spread": f"{self.quantity_axis_spread():.6f}",
        }

    def clear_recent(self) -> None:
        self.recent_events.clear()


def run_experiment(args: argparse.Namespace) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    report_every = args.report_every or max(1, args.episodes // 20)
    for seed in range(args.seeds):
        for condition in CONDITIONS:
            run = BarterRun(
                condition=condition,
                seed=args.seed_offset + seed,
                agents=args.agents,
                symbols=args.symbols,
                compute_budget=args.compute_budget,
                prototype_memory=args.prototype_memory,
                train_max=args.train_max,
                consistency_weight=args.consistency_weight,
                transfer_consistency_weight=args.transfer_consistency_weight,
                transfer_consistency_min_records=args.transfer_consistency_min_records,
                transfer_consistency_warmup=args.transfer_consistency_warmup,
                transfer_consistency_anneal=args.transfer_consistency_anneal,
                prototype_candidates=args.prototype_candidates,
                random_option_set_size=args.random_option_set_size,
                candidate_source_mode=getattr(args, "candidate_source_mode", "mixed_all"),
            )
            for episode in range(1, args.episodes + 1):
                run.step(held_out=False)
                if episode % report_every == 0 or episode == args.episodes:
                    rows.append(run.metrics(episode=episode, seed=seed, recent=True))
                    run.clear_recent()
            # Held-out q,n in 11..20 is evaluated without updating prototypes.
            for _ in range(args.heldout_episodes):
                run.step(held_out=True)
            rows.append(run.metrics(episode=args.episodes + args.heldout_episodes, seed=seed, recent=True))
    return rows


def write_csv(rows: Sequence[Dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=10_000, help="training episodes per condition/seed")
    parser.add_argument("--agents", type=int, default=30, help="number of sampled agents")
    parser.add_argument("--symbols", type=int, default=6, help="active symbol vocabulary size")
    parser.add_argument("--compute-budget", type=int, default=3, help="candidate trades evaluated by bounded agents")
    parser.add_argument("--seeds", type=int, default=20, help="number of random seeds")
    parser.add_argument("--prototype-memory", type=int, default=5, help="recent prototypes remembered per symbol")
    parser.add_argument("--prototype-candidates", type=int, default=2, help="symbol-guided candidates reserved in bounded receiver search")
    parser.add_argument("--random-option-set-size", type=int, default=0, help="bounded random transfer-option pool size before symbol prototypes are added; 0 means all feasible transfers")
    parser.add_argument(
        "--candidate-source-mode",
        choices=("mixed_all", "random_only", "symbol_only", "mixed_1_symbol", "mixed_2_symbol"),
        default="mixed_all",
        help="how bounded candidate slots are allocated between random options and symbol prototypes",
    )
    parser.add_argument("--consistency-weight", type=float, default=0.75, help="entropy penalty weight for consistent-symbol scoring")
    parser.add_argument("--transfer-consistency-weight", type=float, default=0.0, help="normalized Var(K|symbol) penalty for quantity-like symbol scoring")
    parser.add_argument("--transfer-consistency-min-records", type=int, default=0, help="minimum symbol prototypes before applying Var(K|symbol) pressure")
    parser.add_argument("--transfer-consistency-warmup", type=int, default=0, help="episodes before enabling Var(K|symbol) pressure")
    parser.add_argument("--transfer-consistency-anneal", type=int, default=0, help="episodes over which to ramp Var(K|symbol) pressure after warmup")
    parser.add_argument("--train-max", type=int, default=10, help="inclusive max q,n value during training")
    parser.add_argument("--heldout-episodes", type=int, default=1_000, help="q,n in train_max+1..20 evaluation episodes")
    parser.add_argument("--report-every", type=int, default=0, help="training CSV interval; default is episodes/20")
    parser.add_argument("--seed-offset", type=int, default=0, help="offset added to each seed")
    parser.add_argument("--output", type=Path, default=Path("barter_mve_results.csv"), help="CSV output path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = run_experiment(args)
    write_csv(rows, args.output)
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
