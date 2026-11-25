# E7: gap reruns (design/sim_spec_ms4.md §3.7(e), §3.8)

## Merged LP bounds (§3.8)

| c | status | objective | n_vars | nnz | solve s |
|---|---|---|---|---|---|
| 1 | 0 | 4601 | 865595 | 3662165 | 208.2 |
| 2 | 0 | 1916 | 943675 | 3989807 | 291.9 |
| 3 | 0 | 1594 | 877835 | 3621396 | 130.9 |
| 4 | 0 | 1892 | 650629 | 2816593 | 96.78 |


## ALG / LB of the gap reruns (an upper bound on the gap; merged bound)

| tag | runs | with LB | median | ci lo | ci hi | P1 flags |
|---|---|---|---|---|---|---|
| Sublet | 12 | 12 | 1.617 | 1.533 | 1.625 | 0 |
| A7G | 12 | 12 | 1.671 | 1.526 | 1.699 | 0 |
| A7 | 12 | 12 | 1.671 | 1.526 | 1.699 | 0 |
| A6 | 12 | 12 | 1.95 | 1.918 | 2.003 | 0 |
| BL5 | 12 | 12 | 1.617 | 1.533 | 1.625 | 0 |
| BL1 | 12 | 12 | 1.363 | 1.261 | 1.504 | 0 |
| BL2 | 12 | 12 | 1.466 | 1.307 | 1.597 | 0 |
| BL4 | 12 | 12 | 1.925 | 1.75 | 2.18 | 0 |
| BL0a | 4 | 4 | 2.217 | 2.199 | 2.223 | 0 |


## Checks (§3.11)

| check | status |
|---|---|
| E7-1 | pass |
| E7-2 | pass |
| E7-3 | pass |
| E7-4 | pass |
| E7-5 | pass |
| E7-6 | pass |
| E7-10 | informative |
| E7-11 | informative |


