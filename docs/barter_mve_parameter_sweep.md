# Bounded Barter MVE Parameter Sweep

This file records the requested next-step sweep: vary a small number of key parameters, run the MVE, and interpret whether the original claim becomes stronger.

## What changed before the sweep

The runner now exposes two knobs that target the previous analysis recommendations:

1. `--consistency-weight`: scales the entropy penalty in the C1/C4 symbol-selection score.
2. `--prototype-candidates`: reserves bounded receiver search slots for symbol-associated transfer prototypes before filling the remaining slots randomly.

The second knob is deliberately still minimal: it does not add predicates, bargaining, theorem proving, graph worlds, or explicit feasibility labels. It only changes how strongly the receiver's bounded search uses the already learned symbol prototypes.

## Shared run settings

All three variants used:

```bash
--episodes 10000 --agents 30 --symbols 6 --compute-budget 3 --seeds 20
```

Each run was analyzed with:

```bash
python analyze_barter_results.py <csv> --episodes 10000 --markdown-output <report.md> --summary-csv <summary.csv>
```

## Variants

| variant | purpose | command-specific knobs |
| --- | --- | --- |
| balanced | default consistency pressure with two symbol-guided receiver candidates | `--prototype-candidates 2 --consistency-weight 0.75` |
| strong_consistency | test whether a stronger consistency penalty helps | `--prototype-candidates 2 --consistency-weight 1.50` |
| receiver_heavy | test whether receiver-side symbol use is the missing pressure | `--prototype-candidates 3 --consistency-weight 0.75` |

## Key held-out bounded-condition results

The main hypothesis concerns bounded agents, so this table focuses on held-out C1/C2/C3 metrics.

| variant | condition | success_rate | welfare_gain | mi_symbol_outcome | mi_symbol_transfer | symbol_entropy |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| balanced | C1 | 0.1553 ± 0.0058 | 0.5636 ± 0.0160 | 0.0376 ± 0.0088 | 0.1149 ± 0.0138 | 1.8618 ± 0.0329 |
| balanced | C2 | 0.1596 ± 0.0035 | 0.5884 ± 0.0147 | 0.0097 ± 0.0010 | 0.1186 ± 0.0072 | 2.5821 ± 0.0006 |
| balanced | C3 | 0.1415 ± 0.0026 | 0.6265 ± 0.0127 | 0.0030 ± 0.0006 | 0.0428 ± 0.0020 | 2.5815 ± 0.0006 |
| strong_consistency | C1 | 0.1645 ± 0.0057 | 0.5967 ± 0.0239 | 0.0330 ± 0.0060 | 0.1141 ± 0.0111 | 1.7978 ± 0.0245 |
| strong_consistency | C2 | 0.1596 ± 0.0035 | 0.5884 ± 0.0147 | 0.0097 ± 0.0010 | 0.1186 ± 0.0072 | 2.5821 ± 0.0006 |
| strong_consistency | C3 | 0.1415 ± 0.0026 | 0.6265 ± 0.0127 | 0.0030 ± 0.0006 | 0.0428 ± 0.0020 | 2.5815 ± 0.0006 |
| receiver_heavy | C1 | 0.1688 ± 0.0055 | 0.6602 ± 0.0208 | 0.0346 ± 0.0093 | 0.1203 ± 0.0120 | 1.8769 ± 0.0374 |
| receiver_heavy | C2 | 0.1678 ± 0.0044 | 0.6116 ± 0.0170 | 0.0137 ± 0.0015 | 0.1581 ± 0.0101 | 2.5811 ± 0.0004 |
| receiver_heavy | C3 | 0.1415 ± 0.0026 | 0.6265 ± 0.0127 | 0.0030 ± 0.0006 | 0.0428 ± 0.0020 | 2.5815 ± 0.0006 |

## Ordering checks

| variant | held-out success | held-out welfare | held-out symbol-outcome MI | held-out symbol-transfer MI |
| --- | --- | --- | --- | --- |
| balanced | does not support C1 > C2 > C3 | does not support C1 > C2 > C3 | supports C1 > C2 > C3 | does not support C1 > C2 > C3 |
| strong_consistency | supports C1 > C2 > C3 | does not support C1 > C2 > C3 | supports C1 > C2 > C3 | does not support C1 > C2 > C3 |
| receiver_heavy | supports C1 > C2 > C3 | partially supports: C1 is best, but C2 > C3 fails | supports C1 > C2 > C3 | does not support C1 > C2 > C3 |

## Interpretation

### 1. Receiver-side symbol use matters more than simply increasing consistency pressure

The best C1 held-out welfare and success came from `receiver_heavy`, not from merely increasing consistency weight:

| variant | C1 held-out success | C1 held-out welfare |
| --- | ---: | ---: |
| balanced | 0.1553 | 0.5636 |
| strong_consistency | 0.1645 | 0.5967 |
| receiver_heavy | 0.1688 | 0.6602 |

This supports the earlier diagnosis that symbols need to affect bounded trade search more directly. Reserving all three bounded search slots for symbol prototypes made C1's held-out welfare exceed both bounded baselines, though C2 and C3 remained competitive on other metrics.

### 2. Stronger consistency helps held-out success, but does not fix transfer compression

Increasing `--consistency-weight` from `0.75` to `1.50` improved C1 held-out success from `0.1553` to `0.1645` and made held-out success satisfy `C1 > C2 > C3`. However, C2 still had slightly higher held-out symbol-transfer MI (`0.1186`) than C1 (`0.1141`). So stronger behavioral consistency improves good/bad outcome predictiveness but does not by itself create the strongest transfer-magnitude code.

### 3. C2 is a serious baseline when receiver prototype use is strong

In `receiver_heavy`, C2 achieved the highest held-out symbol-transfer MI (`0.1581`) even without consistency pressure. This means receiver-side prototype use alone can create transfer-magnitude associations. The consistency-specific advantage is more visible in symbol-outcome MI, where C1 stayed clearly above C2 and C3 in every variant.

### 4. C3 confirms that communication/prototypes are doing real work

C3 is unchanged across variants because shuffled/no communication prevents the prototype-reservation knob from helping. Its held-out success (`0.1415`) and symbol-transfer MI (`0.0428`) remain below the communication conditions. This supports the minimal claim that shared symbols matter under bounded compute, even if the unique contribution of consistency is narrower than hoped.

### 5. Current best read

The sweep strengthens a narrower claim:

> Under bounded compute, shared symbols that directly steer receiver search improve held-out trade outcomes. Consistency pressure reliably improves symbol-outcome compression, but it is not sufficient by itself to dominate non-consistency communication on every metric.

The clean `C1 > C2 > C3` pattern still does not hold across all metrics. The most promising next version should keep the receiver-heavy pressure, then make the consistency penalty act on transfer-magnitude variance as well as outcome-sign entropy. That would target the current failure mode: C2 can learn high `I(S;K)` without consistency, while C1 is better at `I(S;sign(ΔU))`.

## Follow-up

For a deeper look at consistency metrics that are closer to proto-mathematical structure, see `docs/barter_mve_math_consistency_sweep.md`. That follow-up separates outcome-sign consistency from transfer-magnitude tightness and quantity-axis stability.

## Behavior-first follow-up

A later option-set sweep adds oracle-normalized behavior metrics and a behavior-first gate. See `docs/barter_mve_behavior_first_sweep.md`. Its conclusion is intentionally stricter: option-set changes create only small C1 behavior advantages, so symbolic metrics remain secondary until C1 clears a held-out success/welfare margin.
