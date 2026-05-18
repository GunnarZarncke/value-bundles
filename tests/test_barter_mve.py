import argparse
import csv
import math
import tempfile
import unittest
from pathlib import Path

from analyze_barter_results import aggregate, split_final_rows
from run_barter_mve import (
    BarterRun,
    SymbolMemory,
    entropy_from_counts,
    mutual_information,
    spearman_correlation,
    run_experiment,
    trade_delta,
    utility,
    write_csv,
)


class BarterMveTests(unittest.TestCase):
    def test_utility_and_trade_delta(self):
        self.assertEqual(utility(5, 5), 0)
        self.assertEqual(utility(3, 5), -2)
        self.assertEqual(trade_delta(q_a=8, q_b=2, n_a=5, n_b=5, k=3), (3, 3, 6))
        self.assertEqual(trade_delta(q_a=4, q_b=6, n_a=5, n_b=5, k=1), (-1, -1, -2))

    def test_entropy_and_mutual_information(self):
        self.assertAlmostEqual(entropy_from_counts([1, 1]), 1.0)
        self.assertAlmostEqual(mutual_information([(0, 0), (0, 0), (1, 1), (1, 1)]), 1.0)
        self.assertAlmostEqual(mutual_information([(0, 0), (0, 1), (1, 0), (1, 1)]), 0.0)
        self.assertAlmostEqual(spearman_correlation([1, 2, 3], [10, 20, 30]), 1.0)
        self.assertAlmostEqual(spearman_correlation([1, 2, 3], [30, 20, 10]), -1.0)

    def test_symbol_memory_is_bounded_and_computes_entropy(self):
        memory = SymbolMemory(limit=2)
        memory.add((1, 1, 1, 1, 0, 1, 1.0, 0.0))
        memory.add((1, 1, 1, 1, 0, 2, -1.0, 0.0))
        memory.add((1, 1, 1, 1, 0, 3, 1.0, 0.0))
        self.assertEqual(len(memory.records), 2)
        self.assertAlmostEqual(memory.mean_k(), 2.5)
        self.assertAlmostEqual(memory.outcome_entropy(), 1.0)

    def test_heldout_steps_do_not_update_symbol_memories(self):
        run = BarterRun(
            condition="C1",
            seed=7,
            agents=6,
            symbols=4,
            compute_budget=2,
            prototype_memory=3,
            train_max=10,
            consistency_weight=0.75,
            transfer_consistency_weight=0.0,
            prototype_candidates=2,
        )
        for _ in range(20):
            run.step(held_out=False)
        before = [tuple(memory.records) for memory in run.memories]
        for _ in range(10):
            run.step(held_out=True)
        after = [tuple(memory.records) for memory in run.memories]
        self.assertEqual(before, after)

    def test_candidate_generation_handles_tiny_feasible_sets(self):
        run = BarterRun(
            condition="C1",
            seed=11,
            agents=6,
            symbols=4,
            compute_budget=3,
            prototype_memory=5,
            train_max=10,
            consistency_weight=0.75,
            transfer_consistency_weight=0.0,
            prototype_candidates=3,
        )
        self.assertEqual(run.candidate_transfers(q_a=0, received_symbol=0), [0])

    def test_receiver_can_reserve_symbol_guided_candidates(self):
        run = BarterRun(
            condition="C1",
            seed=3,
            agents=6,
            symbols=4,
            compute_budget=3,
            prototype_memory=5,
            train_max=10,
            consistency_weight=0.75,
            transfer_consistency_weight=0.0,
            prototype_candidates=3,
        )
        run.memories[0].add((8, 1, 4, 4, 0, 4, 1.0, 1.0))
        run.memories[0].add((8, 1, 4, 4, 0, 5, 1.0, 1.0))
        candidates = run.candidate_transfers(q_a=8, received_symbol=0)
        self.assertLessEqual(len(candidates), 3)
        self.assertTrue({4, 5}.issubset(candidates))

    def test_run_experiment_emits_all_conditions_and_csv_fields(self):
        args = argparse.Namespace(
            episodes=12,
            agents=8,
            symbols=4,
            compute_budget=2,
            seeds=2,
            prototype_memory=3,
            train_max=10,
            consistency_weight=0.75,
            transfer_consistency_weight=0.0,
            prototype_candidates=2,
            heldout_episodes=5,
            report_every=6,
            seed_offset=0,
        )
        rows = run_experiment(args)
        self.assertEqual(len(rows), 2 * 4 * 3)
        self.assertEqual({row["condition"] for row in rows}, {"C1", "C2", "C3", "C4"})
        required = {
            "episode",
            "condition",
            "seed",
            "success_rate",
            "welfare_gain",
            "mi_symbol_outcome",
            "mi_symbol_transfer",
            "symbol_entropy",
            "consistency_loss",
            "transfer_consistency_loss",
            "quantity_axis_stability",
            "quantity_axis_spread",
        }
        self.assertEqual(set(rows[0]), required)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "results.csv"
            write_csv(rows, output)
            with output.open(newline="") as handle:
                written_rows = list(csv.DictReader(handle))
            self.assertEqual(len(written_rows), len(rows))

    def test_analyzer_splits_train_and_heldout_rows(self):
        rows = [
            {"episode": "5", "condition": "C1", "seed": "0", "success_rate": "0.1", "welfare_gain": "1", "mi_symbol_outcome": "0", "mi_symbol_transfer": "0", "symbol_entropy": "1", "consistency_loss": "0", "transfer_consistency_loss": "0", "quantity_axis_stability": "0", "quantity_axis_spread": "0"},
            {"episode": "10", "condition": "C1", "seed": "0", "success_rate": "0.2", "welfare_gain": "2", "mi_symbol_outcome": "0", "mi_symbol_transfer": "0", "symbol_entropy": "1", "consistency_loss": "0", "transfer_consistency_loss": "0", "quantity_axis_stability": "0", "quantity_axis_spread": "0"},
            {"episode": "12", "condition": "C1", "seed": "0", "success_rate": "0.3", "welfare_gain": "3", "mi_symbol_outcome": "0", "mi_symbol_transfer": "0", "symbol_entropy": "1", "consistency_loss": "0", "transfer_consistency_loss": "0", "quantity_axis_stability": "0", "quantity_axis_spread": "0"},
        ]
        phases = split_final_rows(rows, train_episodes=10)
        self.assertEqual(phases["train_final"][0]["episode"], "10")
        self.assertEqual(phases["heldout"][0]["episode"], "12")
        results = aggregate(phases)
        c1_train_success = [
            result for result in results if result.phase == "train_final" and result.condition == "C1" and result.metric == "success_rate"
        ][0]
        self.assertTrue(math.isclose(c1_train_success.mean, 0.2))


if __name__ == "__main__":
    unittest.main()
