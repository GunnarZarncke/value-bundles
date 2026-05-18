# Bounded Barter MVE Evaluation

This records a reproducible baseline evaluation run for the minimum viable bounded-barter experiment. For the three-variant sweep, see `docs/barter_mve_parameter_sweep.md`.

## Commands

```bash
python run_barter_mve.py --episodes 10000 --agents 30 --symbols 6 --compute-budget 3 --seeds 20 --prototype-candidates 2 --consistency-weight 0.75 --output /tmp/barter_sweep/balanced.csv
python analyze_barter_results.py /tmp/barter_sweep/balanced.csv --episodes 10000 --markdown-output /tmp/barter_sweep/balanced.md --summary-csv /tmp/barter_sweep/balanced_summary.csv
```

## Aggregate metrics

### train_final

| condition | success_rate | welfare_gain | mi_symbol_outcome | mi_symbol_transfer | symbol_entropy | consistency_loss | n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C1 | 0.1955 ± 0.0029 | 0.8876 ± 0.0195 | 0.0074 ± 0.0010 | 0.0773 ± 0.0035 | 2.5093 ± 0.0079 | 0.5400 ± 0.0270 | 20 |
| C2 | 0.2002 ± 0.0042 | 0.9310 ± 0.0282 | 0.0087 ± 0.0011 | 0.0771 ± 0.0035 | 2.5780 ± 0.0007 | 0.5720 ± 0.0459 | 20 |
| C3 | 0.2013 ± 0.0032 | 0.9966 ± 0.0180 | 0.0083 ± 0.0015 | 0.0727 ± 0.0030 | 2.5763 ± 0.0009 | 0.5960 ± 0.0423 | 20 |
| C4 | 0.2101 ± 0.0040 | 1.1050 ± 0.0267 | 0.0043 ± 0.0009 | 0.0311 ± 0.0037 | 1.3037 ± 0.1022 | 0.7126 ± 0.0152 | 20 |

### heldout

| condition | success_rate | welfare_gain | mi_symbol_outcome | mi_symbol_transfer | symbol_entropy | consistency_loss | n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C1 | 0.1553 ± 0.0058 | 0.5636 ± 0.0160 | 0.0376 ± 0.0088 | 0.1149 ± 0.0138 | 1.8618 ± 0.0329 | 0.5400 ± 0.0270 | 20 |
| C2 | 0.1596 ± 0.0035 | 0.5884 ± 0.0147 | 0.0097 ± 0.0010 | 0.1186 ± 0.0072 | 2.5821 ± 0.0006 | 0.5720 ± 0.0459 | 20 |
| C3 | 0.1415 ± 0.0026 | 0.6265 ± 0.0127 | 0.0030 ± 0.0006 | 0.0428 ± 0.0020 | 2.5815 ± 0.0006 | 0.5960 ± 0.0423 | 20 |
| C4 | 0.2007 ± 0.0027 | 0.9902 ± 0.0165 | 0.0137 ± 0.0137 | 0.0137 ± 0.0137 | 0.0497 ± 0.0497 | 0.7126 ± 0.0152 | 20 |

## Predicted-ordering checks

The primary falsifiable prediction is C1 > C2 > C3 under bounded compute.

| phase | metric | result |
| --- | --- | --- |
| train_final | success_rate | does not support C1 > C2 > C3 |
| train_final | welfare_gain | does not support C1 > C2 > C3 |
| train_final | mi_symbol_outcome | does not support C1 > C2 > C3 |
| train_final | mi_symbol_transfer | supports C1 > C2 > C3 |
| heldout | success_rate | does not support C1 > C2 > C3 |
| heldout | welfare_gain | does not support C1 > C2 > C3 |
| heldout | mi_symbol_outcome | supports C1 > C2 > C3 |
| heldout | mi_symbol_transfer | does not support C1 > C2 > C3 |

## Interpretation

- The baseline run is weaker than the previous held-out result: C1 keeps a clear held-out symbol-outcome MI advantage, but C2 edges C1 on held-out success, welfare, and symbol-transfer MI.
- C1 has lower held-out symbol entropy than C2/C3, which still suggests a more compact code, but compactness alone is not enough to dominate trade outcomes.
- C4 remains the high-welfare compute-unbounded reference condition and has very low held-out symbol-transfer MI, consistent with symbols becoming less necessary when direct search is available.
- The parameter sweep in `docs/barter_mve_parameter_sweep.md` shows that stronger receiver-side use improves C1 held-out success and welfare more than simply increasing consistency pressure.
