# Math-Like Consistency Sweep

This sweep asks a narrower follow-up question than the basic welfare experiment:

> Which factors increase consistency in the proto-mathematical sense: stable symbols with tight transfer-magnitude prototypes and a reusable quantity axis?

The motivating distinction is that outcome consistency (`S` predicts good/bad trade) is not yet number-like. A more math-like symbol system should also make each symbol's associated transfer magnitude tighter and preserve an ordered quantity axis across held-out states.

## Added metrics

The runner now emits three extra diagnostics:

| metric | direction | meaning |
| --- | --- | --- |
| `transfer_consistency_loss` | lower is better | average normalized `Var(K | S)` across active symbol memories; this asks whether each symbol maps to a tight transfer prototype |
| `quantity_axis_stability` | higher is better | Spearman rank stability, mapped to `[0, 1]`, between prototype-memory `E[K|S]` and recent/evaluation `E[K|S]` |
| `quantity_axis_spread` | higher is better, if stability is also high | normalized range of symbol mean transfers; this asks whether symbols span a nontrivial quantity axis instead of collapsing |

These are still post-hoc behavioral metrics. They do not add explicit number labels, predicates, theorem proving, or symbolic rules.

## Variants

All runs used:

```bash
--episodes 10000 --agents 30 --symbols 6 --compute-budget 3 --seeds 20 --prototype-candidates 3
```

The three explored factors were:

| variant | purpose | additional knobs |
| --- | --- | --- |
| `receiver_outcome_only` | receiver-heavy baseline with only outcome-entropy consistency | `--prototype-memory 5 --consistency-weight 0.75 --transfer-consistency-weight 0.0` |
| `receiver_quantity_penalty` | test direct transfer-variance pressure | `--prototype-memory 5 --consistency-weight 0.75 --transfer-consistency-weight 1.0` |
| `quantity_penalty_memory10` | test whether longer prototype memory stabilizes transfer-variance pressure | `--prototype-memory 10 --consistency-weight 0.75 --transfer-consistency-weight 1.0` |

## Key held-out bounded-condition results

| variant | condition | success_rate | welfare_gain | mi_symbol_outcome | mi_symbol_transfer | transfer_consistency_loss | quantity_axis_stability | quantity_axis_spread |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| receiver_outcome_only | C1 | 0.1688 | 0.6602 | 0.0346 | 0.1203 | 0.0149 | 0.6747 | 0.0665 |
| receiver_outcome_only | C2 | 0.1678 | 0.6116 | 0.0137 | 0.1581 | 0.0273 | 0.5934 | 0.0920 |
| receiver_outcome_only | C3 | 0.1415 | 0.6265 | 0.0030 | 0.0428 | 0.0261 | 0.4727 | 0.0940 |
| receiver_quantity_penalty | C1 | 0.1512 | 0.5723 | 0.0118 | 0.0914 | 0.0597 | 0.5326 | 0.0950 |
| receiver_quantity_penalty | C2 | 0.1678 | 0.6116 | 0.0137 | 0.1581 | 0.0273 | 0.5934 | 0.0920 |
| receiver_quantity_penalty | C3 | 0.1415 | 0.6265 | 0.0030 | 0.0428 | 0.0261 | 0.4727 | 0.0940 |
| quantity_penalty_memory10 | C1 | 0.1662 | 0.5886 | 0.0131 | 0.1055 | 0.0406 | 0.5061 | 0.0560 |
| quantity_penalty_memory10 | C2 | 0.1719 | 0.6427 | 0.0105 | 0.1620 | 0.0235 | 0.5577 | 0.0620 |
| quantity_penalty_memory10 | C3 | 0.1415 | 0.6265 | 0.0030 | 0.0428 | 0.0277 | 0.4914 | 0.0598 |

## Interpretation

### 1. The best math-like consistency came from receiver-heavy outcome consistency, not the direct transfer penalty

The `receiver_outcome_only` C1 condition had the lowest held-out transfer-consistency loss (`0.0149`) and the highest quantity-axis stability (`0.6747`) among the bounded conditions in this sweep. That is the strongest proto-math signal observed here: symbols were relatively tight in transfer magnitude and their ordering generalized to held-out states.

This is surprising but useful. A direct `Var(K|S)` penalty did not improve math-like structure in this implementation. Instead, it made C1 worse on transfer-consistency loss, axis stability, outcome MI, transfer MI, success, and welfare.

### 2. Direct transfer-variance pressure was too blunt

Adding `--transfer-consistency-weight 1.0` increased C1 held-out `transfer_consistency_loss` from `0.0149` to `0.0597`, reduced `quantity_axis_stability` from `0.6747` to `0.5326`, and reduced welfare from `0.6602` to `0.5723`.

A likely mechanism is that the transfer penalty is applied during sender symbol choice using very small memories. With only five prototypes per symbol, penalizing variance can push premature symbol specialization or collapse before a useful quantity axis is reliably established. In other words, pressure for tight prototypes can fight the exploration needed to discover a stable ordering.

### 3. Larger memory softened but did not solve the transfer-penalty problem

Increasing prototype memory from `5` to `10` under transfer-variance pressure improved C1 relative to the short-memory transfer-penalty run:

| metric | memory 5 transfer penalty | memory 10 transfer penalty |
| --- | ---: | ---: |
| success_rate | 0.1512 | 0.1662 |
| welfare_gain | 0.5723 | 0.5886 |
| transfer_consistency_loss | 0.0597 | 0.0406 |
| mi_symbol_transfer | 0.0914 | 0.1055 |

So memory length helps stabilize the noisy penalty, but it still does not beat the no-transfer-penalty receiver-heavy baseline on math-like consistency.

### 4. C2 remains strong on transfer MI, but weaker on stability and tightness in the best run

In `receiver_outcome_only`, C2 has higher held-out `mi_symbol_transfer` (`0.1581`) and larger spread (`0.0920`) than C1, but it has worse transfer consistency loss (`0.0273` vs `0.0149`) and lower quantity-axis stability (`0.5934` vs `0.6747`).

That means C2 can associate symbols with transfer magnitudes, but C1's receiver-heavy outcome consistency gives a tighter and more stable post-hoc axis in the best setting. This is closer to the desired proto-mathematical structure than raw `I(S;K)` alone.

### 5. Current best answer to “which factors increase consistency?”

For consistency that could scale toward math-like structure, the ranking from this sweep is:

1. **Receiver-side symbol use under bounded compute**: strongest positive factor. It makes symbols action-relevant and produced the best stable/tight quantity axis.
2. **Outcome-sign consistency**: useful when paired with receiver-side use; it improves good/bad compression and, indirectly, produced the best transfer tightness in the receiver-heavy run.
3. **Longer prototype memory**: helpful only as a stabilizer when using noisy transfer penalties, but not sufficient by itself.
4. **Direct transfer-variance penalty as currently implemented**: negative factor. It worsened the metrics most related to math-like consistency.

## Next steps

1. Keep `--prototype-candidates 3` as the default pressure setting for math-like consistency tests.
2. Do **not** keep the current transfer-variance penalty as-is. Replace it with a delayed or annealed penalty, for example only after each symbol has at least `r` observations.
3. Split consistency into two phases: first learn outcome-useful symbols, then apply a weak transfer-variance pressure to sharpen quantity prototypes.
4. Add a direct rank-recovery report: list `E[K|S]` by symbol for train and held-out, then report rank flips. This will be easier to interpret than a single stability scalar.
5. Preserve the MVE boundary: no explicit number labels, no predicates, no theorem proving. The failure mode is still pressure design, not missing formal machinery.
