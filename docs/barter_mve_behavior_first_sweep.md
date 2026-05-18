# Behavior-First Option-Set Sweep

This sweep responds to the main failure mode in the earlier runs: symbolic/quantity metrics are not persuasive unless C1 also produces a meaningful held-out success or welfare gain. The analyzer now reports oracle-normalized behavior metrics and a behavior-first gate.

## Added behavior-first diagnostics

| metric | meaning |
| --- | --- |
| `opportunity_rate` | fraction of episodes where any one-way transfer from A to B could improve total welfare |
| `success_given_opportunity` | trade success divided by oracle-positive opportunities, so low raw success is not confused with lack of available trades |
| `welfare_capture` | realized welfare gain divided by oracle-positive welfare gain |

The analyzer also applies a behavior-first gate: symbolic/quantity metrics count only if C1 beats both C2 and C3 on held-out `success_rate` by at least `0.03`, or on held-out `welfare_gain` by at least `0.05`.

## Variants

All variants kept compute budget at `3`; this avoids making `m=1` or `m=2` the first lever. Instead, the sweep changes option-set size and symbol-set size.

```bash
--episodes 10000 --agents 30 --compute-budget 3 --seeds 20 --prototype-candidates 3 --consistency-weight 0.75
```

| variant | purpose | extra knobs |
| --- | --- | --- |
| `options_all_symbols6` | receiver-heavy baseline with all feasible random options | `--symbols 6 --random-option-set-size 0` |
| `options4_symbols6` | constrain the random option set while keeping 6 symbols | `--symbols 6 --random-option-set-size 4` |
| `options4_symbols12` | test whether a larger symbol set helps consistency pressure separate useful symbols | `--symbols 12 --random-option-set-size 4` |
| `options2_symbols6` | stronger option-set constraint, included as a stress check | `--symbols 6 --random-option-set-size 2` |

## Held-out behavior results

| variant | condition | success_rate | opportunity_rate | success_given_opportunity | welfare_gain | welfare_capture | mi_symbol_outcome | mi_symbol_transfer |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| options_all_symbols6 | C1 | 0.1688 | 0.2026 | 0.8323 | 0.6602 | 0.6567 | 0.0346 | 0.1203 |
| options_all_symbols6 | C2 | 0.1678 | 0.2015 | 0.8315 | 0.6116 | 0.6223 | 0.0137 | 0.1581 |
| options_all_symbols6 | C3 | 0.1415 | 0.2039 | 0.6941 | 0.6265 | 0.6243 | 0.0030 | 0.0428 |
| options4_symbols6 | C1 | 0.1714 | 0.2028 | 0.8445 | 0.6226 | 0.6294 | 0.0256 | 0.1203 |
| options4_symbols6 | C2 | 0.1593 | 0.2036 | 0.7820 | 0.6034 | 0.6112 | 0.0117 | 0.1423 |
| options4_symbols6 | C3 | 0.1369 | 0.1999 | 0.6842 | 0.6058 | 0.6246 | 0.0040 | 0.0441 |
| options4_symbols12 | C1 | 0.1664 | 0.2027 | 0.8212 | 0.6297 | 0.6400 | 0.0431 | 0.2099 |
| options4_symbols12 | C2 | 0.1659 | 0.2008 | 0.8259 | 0.6240 | 0.6355 | 0.0152 | 0.2029 |
| options4_symbols12 | C3 | 0.1424 | 0.2043 | 0.6968 | 0.6281 | 0.6292 | 0.0088 | 0.0923 |
| options2_symbols6 | C1 | 0.1413 | 0.1993 | 0.7092 | 0.4498 | 0.4684 | 0.0308 | 0.1348 |
| options2_symbols6 | C2 | 0.1304 | 0.2078 | 0.6305 | 0.4471 | 0.4436 | 0.0252 | 0.1612 |
| options2_symbols6 | C3 | 0.1105 | 0.2018 | 0.5468 | 0.4743 | 0.4901 | 0.0031 | 0.0428 |

## Interpretation

### 1. The low raw success rate is partly an opportunity ceiling

The opportunity rate is about `0.20` across held-out runs. C4 succeeds almost exactly at that rate because it can scan all feasible transfers. So raw success around `0.17` means bounded agents are capturing a large fraction of the available one-way opportunities, not merely failing 83% of all meaningful trades.

This helps interpret the low absolute success values, but it does not solve the central problem: C1 still needs a meaningful margin over C2/C3.

### 2. Constraining option sets helps a little, but not enough

`options4_symbols6` is the best behavior-first variant in this sweep:

| comparison | success_rate Δ | welfare_gain Δ |
| --- | ---: | ---: |
| C1 - C2 | +0.0121 | +0.0192 |
| C1 - C3 | +0.0345 | +0.0168 |

C1 beats both baselines on held-out success in this setting, but it does **not** clear the predeclared behavior gate: it misses the `+0.03` margin over C2 and the `+0.05` welfare margin over both baselines. Symbolic metrics should therefore remain secondary diagnostics.

### 3. Larger symbol sets do not create a robust behavior gap

With `--symbols 12`, symbolic MI increases, but C1 and C2 are behaviorally almost tied:

| comparison | success_rate Δ | welfare_gain Δ |
| --- | ---: | ---: |
| C1 - C2 | +0.0005 | +0.0057 |
| C1 - C3 | +0.0240 | +0.0016 |

This is exactly the kind of result that should **not** be used as evidence for the main claim: representation metrics move, but behavior does not.

### 4. Over-constraining random options is not the answer

`options2_symbols6` reduces success and welfare for all bounded conditions. C1 still beats C2 on success by only about `+0.011`, while C3 has higher welfare. This suggests that shrinking the random option set too far just starves the task rather than revealing a stronger consistency advantage.

### 5. Current conclusion

The behavior-first gate fails for all variants in this sweep. The strongest honest conclusion is negative/diagnostic:

> Option-set and symbol-set changes produce small C1 advantages in some settings, but not a robust held-out success/welfare gap. Until C1 clears a behavior-first margin, MI/stability/axis metrics should not be treated as evidence for the main claim.

## Next direction

Do not add more compression or quantity metrics. The next change should make symbol use more directly and measurably causal for trade outcomes while preserving the same compute budget. A good next test would compare:

1. random bounded candidate only,
2. symbol-prototype candidate only,
3. one random candidate plus one symbol-prototype candidate,
4. the same with shuffled symbols.

The primary metric should be held-out success/welfare and paired C1-C2/C1-C3 deltas. Symbol metrics should only be interpreted if the behavior gate passes.
