# E9 v2 (design/ms7/feasibility/sens.md §2 D, §3 item 4 (C56))

*exploratory: post-freeze runs on the confirmation weeks (design/ms7/plan.md D6), not a confirmation result*

## Runs (medians over the alignments)

| point | tag | sites x LLMs | runs | slow loop s/h | fast loop s/h | act s/slot | peak MB |
|---|---|---|---|---|---|---|---|
| e7f_V1_SML | Sublet | 84 | 4 | 0.2313 | 0.04488 | 0.01918 | 146.4 |
| e7f_V1_SML | A9 | 84 | 4 | 0.004202 | 0.04401 | 0.0002706 | 145.2 |
| e7f_V2_SML | Sublet | 147 | 4 | 0.4933 | 0.05749 | 0.04098 | 154 |
| e7f_V2_SML | A9 | 147 | 4 | 0.006035 | 0.0585 | 0.0003718 | 144.8 |
| e7f_V4_SML | Sublet | 267 | 4 | 1.134 | 0.07244 | 0.0943 | 161 |
| e7f_V4_SML | A9 | 267 | 4 | 0.01152 | 0.07341 | 0.000767 | 145.2 |
| e7f_V8_SML | Sublet | 507 | 4 | 2.922 | 0.09475 | 0.2432 | 180.1 |
| e7f_V8_SML | A9 | 507 | 4 | 0.0429 | 0.09298 | 0.003291 | 145.4 |
| e7f_V16_SML | Sublet | 987 | 4 | 8.504 | 0.1103 | 0.708 | 216.8 |
| e7f_V16_SML | A9 | 987 | 4 | 0.2542 | 0.1114 | 0.02069 | 145.4 |
| e7f_V32_SML | Sublet | 1947 | 4 | 29.06 | 0.1411 | 2.42 | 297.1 |
| e7f_V32_SML | A9 | 1947 | 4 | 1.829 | 0.1356 | 0.1514 | 152.2 |
| e7f_V64_SML | Sublet | 3855 | 4 | 109 | 0.1802 | 9.079 | 445.7 |
| e7f_V64_SML | A9 | 3855 | 4 | 13.99 | 0.1811 | 1.163 | 174.6 |
| e7f_V8_S | Sublet | 169 | 4 | 4.967 | 0.04977 | 0.4133 | 161.8 |
| e7f_V8_S | A9 | 169 | 4 | 0.2476 | 0.04728 | 0.01986 | 145.3 |
| e7f_V8_ML | Sublet | 338 | 4 | 2.604 | 0.07258 | 0.2167 | 167.5 |
| e7f_V8_ML | A9 | 338 | 4 | 0.03763 | 0.07264 | 0.002884 | 145.4 |
| e7r_V1_SML | Sublet | 84 | 4 | 0.1452 | 0.04402 | 0.01202 | 145.2 |
| e7r_V1_SML | A9 | 84 | 4 | 0.003992 | 0.04425 | 0.0002566 | 145 |
| e7r_V2_SML | Sublet | 150 | 4 | 0.2656 | 0.05529 | 0.022 | 145.2 |
| e7r_V2_SML | A9 | 150 | 4 | 0.005537 | 0.05667 | 0.0003532 | 145.5 |
| e7r_V4_SML | Sublet | 276 | 4 | 0.5519 | 0.07275 | 0.0458 | 146.8 |
| e7r_V4_SML | A9 | 276 | 4 | 0.009966 | 0.07233 | 0.0006682 | 145.2 |
| e7r_V8_SML | Sublet | 525 | 4 | 1.153 | 0.09219 | 0.09576 | 155.4 |
| e7r_V8_SML | A9 | 525 | 4 | 0.03453 | 0.08939 | 0.002623 | 145.3 |
| e7r_V16_SML | Sublet | 1005 | 4 | 2.885 | 0.107 | 0.2399 | 169 |
| e7r_V16_SML | A9 | 1005 | 4 | 0.1831 | 0.107 | 0.0148 | 145.6 |
| e7r_V32_SML | Sublet | 1965 | 4 | 7.831 | 0.1346 | 0.6515 | 196 |
| e7r_V32_SML | A9 | 1965 | 4 | 1.246 | 0.1352 | 0.1029 | 150.4 |
| e7r_V64_SML | Sublet | 3885 | 4 | 23.92 | 0.174 | 1.991 | 249.8 |
| e7r_V64_SML | A9 | 3885 | 4 | 9.142 | 0.1734 | 0.7599 | 168.7 |


## Split runs (guard s per slow slot, if identical)

| point | identical | guard s |
|---|---|---|
| e7f_V1_SML | True | 0.01376 |
| e7f_V2_SML | True | 0.02657 |
| e7f_V4_SML | True | 0.05491 |
| e7f_V8_SML | True | 0.1313 |
| e7f_V16_SML | True | 0.3542 |
| e7f_V32_SML | True | 1.04 |
| e7f_V64_SML | True | 3.567 |
| e7f_V8_S | True | 0.1839 |
| e7f_V8_ML | True | 0.1161 |
| e7r_V1_SML | True | 0.008762 |
| e7r_V2_SML | True | 0.01481 |
| e7r_V4_SML | True | 0.02931 |
| e7r_V8_SML | True | 0.05675 |
| e7r_V16_SML | True | 0.1172 |
| e7r_V32_SML | True | 0.2645 |
| e7r_V64_SML | True | 0.6158 |


## Checks

| check | status |
|---|---|
| E9v2-1 | pass |
| E9v2-2 | pass |
| E9v2-3 | pass |
| E9v2-4 | pass |
| E9v2-5 | pass |
| E9v2-6 | informative |


