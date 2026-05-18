# Bounded Barter MVE Run Analysis

Date run: 2026-05-18.

This note records the requested run/analyze pass for the current bounded-barter
MVE implementation and turns the observed results into next-step recommendations.
The raw CSV and generated analyzer outputs were written under `/tmp` during the
run rather than committed as repository fixtures.

## Commands run

### Default configuration

```bash
python run_barter_mve.py --episodes 10000 --heldout-episodes 1000 --seeds 20 --output /tmp/barter_default.csv
python analyze_barter_results.py /tmp/barter_default.csv --episodes 10000 --markdown-output /tmp/barter_default_report.md --summary-csv /tmp/barter_default_summary.csv
```

### Candidate-source mode sweep

```bash
for mode in mixed_all random_only symbol_only mixed_1_symbol mixed_2_symbol; do
  python run_barter_mve.py \
    --episodes 5000 \
    --heldout-episodes 1000 \
    --seeds 10 \
    --candidate-source-mode "$mode" \
    --output "/tmp/barter_sweep/${mode}.csv"
  python analyze_barter_results.py \
    "/tmp/barter_sweep/${mode}.csv" \
    --episodes 5000 \
    --summary-csv "/tmp/barter_sweep/${mode}_summary.csv" \
    > "/tmp/barter_sweep/${mode}.md"
done
```

## Default-run result

The default 20-seed run does **not** clear the behavior-first gate. C1 has more
held-out symbol/outcome mutual information than C2/C3 and lower transfer
consistency loss than C2/C3, but it does not beat C2 on held-out success or
welfare.

| Phase | Metric | C1 | C2 | C3 | C1 minus max(C2, C3) | Readout |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| train-final | success_rate | 0.2020 | 0.1977 | 0.1974 | +0.0043 | weakly supports C1 |
| train-final | welfare_gain | 0.9228 | 0.8882 | 0.9838 | -0.0610 | C3 wins welfare |
| train-final | mi_symbol_outcome | 0.0091 | 0.0083 | 0.0070 | +0.0008 | tiny symbolic edge |
| train-final | transfer_consistency_loss | 0.0125 | 0.0252 | 0.0264 | -0.0127 | C1 has tighter transfers |
| held-out | success_rate | 0.1597 | 0.1762 | 0.1335 | -0.0165 | C2 wins success |
| held-out | welfare_gain | 0.5990 | 0.6139 | 0.5949 | -0.0149 | C2 wins welfare |
| held-out | success_given_opportunity | 0.7979 | 0.8781 | 0.6808 | -0.0802 | C2 converts opportunities better |
| held-out | welfare_capture | 0.6056 | 0.6276 | 0.6208 | -0.0220 | C2 captures more oracle welfare |
| held-out | mi_symbol_outcome | 0.0393 | 0.0079 | 0.0026 | +0.0314 | C1 has symbolic signal |
| held-out | mi_symbol_transfer | 0.1161 | 0.1378 | 0.0420 | -0.0217 | C2 has more transfer MI |
| held-out | transfer_consistency_loss | 0.0125 | 0.0252 | 0.0264 | -0.0127 | C1 has tighter transfers |
| held-out | quantity_axis_stability | 0.6869 | 0.4516 | 0.5360 | +0.1509 | C1 has stronger axis stability |

Behavior-first gate from the analyzer:

- Gate: **FAIL**.
- Held-out success delta: `-0.0165` against a `+0.0300` required margin.
- Held-out welfare delta: `-0.0149` against a `+0.0500` required margin.

## Candidate-source sweep result

The source-mode sweep was run at 5,000 training episodes and 10 seeds to provide
a quick diagnostic rather than a final estimate. The results reinforce the same
point: symbol-prototype metrics can improve, but the current setup does not
reliably convert that structure into held-out behavior.

| candidate_source_mode | held-out C1 success | C1 success delta vs max(C2,C3) | held-out C1 welfare | C1 welfare delta vs max(C2,C3) | C1 MI(symbol,outcome) delta | C1 quantity-axis stability delta | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| mixed_all | 0.1580 | -0.0051 | 0.5874 | -0.0512 | +0.0214 | +0.1298 | Same as mixed_2_symbol with default prototype slots. |
| random_only | 0.1454 | +0.0008 | 0.6498 | +0.0112 | +0.0102 | +0.2312 | Behavior is competitive without symbol-guided candidates. |
| symbol_only | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Cold-start failure: no prototypes means no useful search. |
| mixed_1_symbol | 0.1606 | +0.0016 | 0.6288 | -0.0098 | +0.0282 | +0.0013 | Best C1 success in sweep, but margin is far below gate. |
| mixed_2_symbol | 0.1580 | -0.0051 | 0.5874 | -0.0512 | +0.0214 | +0.1298 | More symbol slots improve structure but not behavior. |

## Interpretation

1. **The current minimum viable claim is not supported by behavior.** The
   default run produces symbolic/quantity diagnostics in C1, but the held-out
   behavior-first gate fails because C2 beats C1 on both success rate and welfare
   gain.
2. **The symbols are learning something, but not enough to help decisions.** C1
   has the best held-out MI(symbol,outcome), transfer consistency loss, and
   quantity-axis stability in the default run, which suggests structure is
   present. That structure is currently secondary evidence only because behavior
   is not better.
3. **Candidate generation is confounded with representation.** In the sweep,
   `random_only` performs competitively and even has the best C1 held-out welfare
   among the tested modes. This suggests part of the apparent benefit may come
   from search/exploration mechanics rather than from semantically useful
   symbols.
4. **`symbol_only` needs bootstrapping before it can be informative.** With no
   initial symbol prototypes and no random fallback, the receiver has no useful
   candidates to evaluate, so the condition collapses to zero behavior.
5. **C2 is a serious baseline, not a strawman.** Communication without
   consistency pressure can still accumulate useful prototypes, and in the
   default held-out run it outperforms C1 behaviorally.

## Recommended next steps

1. **Make behavior the primary gate before adding more symbolic metrics.** Keep
   the behavior-first rule and require C1 to beat both C2 and C3 on held-out
   success or welfare before interpreting MI/axis metrics as support.
2. **Use paired evaluation states across conditions.** Feed each condition the
   same held-out `(q_a, q_b, n_a, n_b)` sequence per seed so C1/C2/C3 deltas are
   less noisy and easier to attribute to communication/consistency rather than
   sampled opportunities.
3. **Separate exploration from symbol use.** Add explicit epsilon/fallback random
   candidates for `symbol_only`, then report performance by candidate source and
   by whether the final chosen transfer came from symbol memory, random search,
   or both.
4. **Tune for behavioral advantage before expanding the world.** The most useful
   next sweep is small and targeted: `mixed_1_symbol`, random fallback sizes, and
   transfer-consistency warmup/anneal values. Promote a configuration only if it
   clears the behavior gate on 20+ seeds.
5. **Add confidence intervals on deltas, not just per-condition means.** The
   analyzer currently reports per-condition standard errors. A paired bootstrap
   over seeds for `C1 - max(C2, C3)` would make the gate easier to judge.
6. **Consider a stronger receiver-learning update.** Right now all selected
   transfers update memory, including no-trade outcomes. Try weighting or
   filtering memory updates by positive total welfare and compare against the
   current unfiltered baseline.
7. **Document failure modes as first-class results.** The current default result
   is a useful negative result: symbolic structure emerges without behavioral
   advantage. Preserve it as the baseline that future changes must beat.
