# Delayed Quantity-Pressure Follow-up

This follow-up continues the math-like consistency direction. The previous math-consistency sweep found that direct `Var(K|S)` pressure was harmful when applied immediately. Here we test whether gating and annealing that pressure avoids early collapse while still sharpening transfer prototypes.

## New runner knobs

The runner now supports delayed/annealed transfer-consistency pressure:

| knob | meaning |
| --- | --- |
| `--transfer-consistency-min-records` | do not apply the transfer-variance penalty to a symbol until its memory has at least this many records |
| `--transfer-consistency-warmup` | do not apply the transfer-variance penalty until this many episodes have elapsed |
| `--transfer-consistency-anneal` | ramp the transfer-variance penalty from zero to its requested weight over this many episodes after warmup |

These knobs keep the experiment behavioral and minimal: they change when an existing pressure activates, but add no explicit number labels, predicates, rules, theorem proving, or graph/world structure.

## Variants

All variants used:

```bash
--episodes 10000 --agents 30 --symbols 6 --compute-budget 3 --seeds 20 --prototype-candidates 3 --prototype-memory 5 --consistency-weight 0.75
```

| variant | purpose | extra knobs |
| --- | --- | --- |
| `outcome_only` | best prior receiver-heavy baseline | `--transfer-consistency-weight 0.0` |
| `immediate_quantity` | known bad direct transfer-variance pressure | `--transfer-consistency-weight 1.0` |
| `delayed_quantity` | delayed and annealed transfer-variance pressure | `--transfer-consistency-weight 1.0 --transfer-consistency-min-records 5 --transfer-consistency-warmup 3000 --transfer-consistency-anneal 4000` |

## Held-out bounded-condition results

| variant | condition | success_rate | welfare_gain | mi_symbol_outcome | mi_symbol_transfer | transfer_consistency_loss | quantity_axis_stability | quantity_axis_spread |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| outcome_only | C1 | 0.1688 | 0.6602 | 0.0346 | 0.1203 | 0.0149 | 0.6747 | 0.0665 |
| outcome_only | C2 | 0.1678 | 0.6116 | 0.0137 | 0.1581 | 0.0273 | 0.5934 | 0.0920 |
| outcome_only | C3 | 0.1415 | 0.6265 | 0.0030 | 0.0428 | 0.0261 | 0.4727 | 0.0940 |
| immediate_quantity | C1 | 0.1512 | 0.5723 | 0.0118 | 0.0914 | 0.0597 | 0.5326 | 0.0950 |
| immediate_quantity | C2 | 0.1678 | 0.6116 | 0.0137 | 0.1581 | 0.0273 | 0.5934 | 0.0920 |
| immediate_quantity | C3 | 0.1415 | 0.6265 | 0.0030 | 0.0428 | 0.0261 | 0.4727 | 0.0940 |
| delayed_quantity | C1 | 0.1631 | 0.6127 | 0.0141 | 0.1037 | 0.0522 | 0.5239 | 0.0960 |
| delayed_quantity | C2 | 0.1678 | 0.6116 | 0.0137 | 0.1581 | 0.0273 | 0.5934 | 0.0920 |
| delayed_quantity | C3 | 0.1415 | 0.6265 | 0.0030 | 0.0428 | 0.0261 | 0.4727 | 0.0940 |

## Interpretation

### 1. Delaying and annealing helps relative to immediate pressure

Compared with `immediate_quantity`, the delayed/annealed C1 run improved:

| metric | immediate | delayed/annealed |
| --- | ---: | ---: |
| success_rate | 0.1512 | 0.1631 |
| welfare_gain | 0.5723 | 0.6127 |
| mi_symbol_outcome | 0.0118 | 0.0141 |
| mi_symbol_transfer | 0.0914 | 0.1037 |
| transfer_consistency_loss | 0.0597 | 0.0522 |

So the previous diagnosis was partly right: applying transfer-magnitude consistency too early is harmful, and gating the pressure reduces the damage.

### 2. But outcome-only receiver-heavy is still best for math-like stability

The delayed/annealed run still did not beat `outcome_only` on the most math-like C1 metrics:

| metric | outcome_only | delayed/annealed |
| --- | ---: | ---: |
| welfare_gain | 0.6602 | 0.6127 |
| mi_symbol_outcome | 0.0346 | 0.0141 |
| mi_symbol_transfer | 0.1203 | 0.1037 |
| transfer_consistency_loss | 0.0149 | 0.0522 |
| quantity_axis_stability | 0.6747 | 0.5239 |

Thus, even delayed transfer-variance pressure is still too blunt in this form. It improves over immediate transfer pressure, but not over simply letting receiver-heavy outcome consistency shape symbol use.

### 3. What this says about factors that scale toward math-like structure

The best factor remains **action relevance under bounded compute**: symbols must steer receiver search. The second useful factor is **outcome-sign consistency**, which indirectly finds stable transfer prototypes when the symbols matter to decisions. Direct transfer-variance pressure needs a more careful mechanism; merely adding it to sender scoring harms the emergent quantity axis.

### 4. Next implementation direction

Do not keep increasing the transfer-variance weight. The next change should make the quantity pressure conditional and local:

1. Learn an outcome-useful symbol code first.
2. Identify active symbols with stable positive welfare.
3. Apply weak transfer-variance sharpening only to those active successful symbols.
4. Report explicit rank recovery: `symbol, train_E[K|S], heldout_E[K|S], rank_train, rank_heldout, rank_flip`.

That targets math-like consistency more directly than the current global variance penalty.
