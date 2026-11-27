# Ablation Matrix

Status: planned; no ablation values have been produced yet.

Run order: dev subset first (40–100 forget), then full confirmation only for
methods that pass the dev gate.

| Method | Ablation | Values | Primary metric | Status |
|---|---|---|---|---|
| CSDA | step mask | on / off | Hy4 leak, retain ROUGE | pending |
| CSDA | patch layer | last / mid | Hy4 leak | pending |
| CSDA | lambda | 0.01 / 0.1 / 0.5 | leak–utility | pending |
| EAS | alpha | fixed 0.5 / dynamic | Hy4 leak | pending |
| EAS | budget | 0.25 / 0.5 / 1.0 | cost / leak | pending |
| RRBU | inner K | 0 / 1 / 3 | RR(5), Hy4 leak | pending |
| DISCO | policy set | 2 / 5 | MCS, Hy4 leak | pending |
| ORTHO | subspace k | 8 / 32 | Hy4 leak, drift | pending |
| ORTHO | drift | on / off | retain ROUGE | pending |
| SCOPE | scope mask | on / off | SCS, Hy4 leak | pending |
| SCOPE | equivalence variants | 1 / 3 / 5 | Hy4 leak | pending |
| SEQU | drift delta | 0.05 / 0.1 / 0.2 | repair count, leak | pending |
| CFA | beta | 0 / 0.1 / 0.3 | SCA, retain ROUGE | pending |
| RIPPLE | hops | 0 / 1 / 2 | Ripple, Recon | pending |
| BOUND | budgets | single / multi | censored width, leak | pending |

## Recording rule

Each ablation result must include:

- run id
- seed
- dev or full split
- max Hy4 leak + coverage
- retain ROUGE-L
- whether the method used a proxy fallback
- one-line conclusion, or `INCONCLUSIVE` if coverage < 0.80
