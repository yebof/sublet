# e5v2: analysis (design/ms7/feasibility/sens.md §2 A-D (C56))

Exploratory, after the MS5b freeze (design/ms7/plan.md D6).

Analysis sha256 6d9772304fe3; design/ms7/registration.md records 6d9772304fe3; matches True; registered full inputs True.

## Cells (Sublet's median saving %; Delta against the pair and against every baseline)

| level | menu | mu | Sublet | Delta pair | hold | Delta all | hold |
|---|---|---|---|---|---|---|---|
| trace | short | 1 | 46.3 | 0.05022 | 4/4 | 0.05022 | 4/4 |
| trace | short | 0.2 | 47.29 | 0.05727 | 4/4 | 0.05727 | 4/4 |
| trace | short | 0.5 | 46.76 | 0.0534 | 4/4 | 0.0534 | 4/4 |
| trace | short | 2 | 44.52 | 0.04733 | 3/4 | 0.04733 | 3/4 |
| trace | long | 1 | 24.39 | -0.01527 | 1/4 | -0.01527 | 1/4 |
| sh0.25 | short | 1 | 46.06 | 0.05522 | 4/4 | 0.05522 | 4/4 |
| sh0.25 | long | 1 | 24.33 | -0.01333 | 1/4 | -0.01333 | 1/4 |
| sh0.5 | short | 1 | 45.94 | 0.05714 | 4/4 | 0.05714 | 4/4 |
| sh0.5 | long | 1 | 24.01 | -0.01511 | 1/4 | -0.01511 | 1/4 |
| sh1 | short | 1 | 45.69 | 0.06057 | 4/4 | 0.06057 | 4/4 |
| sh1 | long | 1 | 24.1 | -0.01394 | 1/4 | -0.01394 | 1/4 |
| all1 | short | 1 | 25.73 | 0.3288 | 4/4 | 0.3288 | 4/4 |
| all1 | long | 1 | 19.66 | -0.01189 | 1/4 | -0.01189 | 1/4 |


## Headline

```json
{
 "bl3_spares_r0_median": {
  "all1:long": 7.930147279132798,
  "all1:short": 1.627671850705239,
  "sh0.25:long": 1.6897890254221015,
  "sh0.25:short": 1.6000923608383324,
  "sh0.5:long": 1.6772252573688282,
  "sh0.5:short": 1.600411728437325,
  "sh1:long": 1.6915179480700457,
  "sh1:short": 1.5982782515213556,
  "trace:long": 1.6673659571151789,
  "trace:short": 1.6048563641226077
 },
 "n_cells": 13,
 "sublet_saving_hi": 46.30069433957158,
 "sublet_saving_hi_cell": "trace:short:1",
 "sublet_saving_lo": 19.660427325368552,
 "sublet_saving_lo_cell": "all1:long:1",
 "sublet_vs_best_baseline_median_delta": {
  "all1:long:1": -0.011894232423746376,
  "all1:short:1": 0.3287516652071348,
  "sh0.25:long:1": -0.013325122653253585,
  "sh0.25:short:1": 0.055221884139533994,
  "sh0.5:long:1": -0.015111065139283342,
  "sh0.5:short:1": 0.05714142082155377,
  "sh1:long:1": -0.01394158528271583,
  "sh1:short:1": 0.060571033663018636,
  "trace:long:1": -0.015267247251714078,
  "trace:short:0.2": 0.05726900498062487,
  "trace:short:0.5": 0.0533972921367849,
  "trace:short:1": 0.0502188217143833,
  "trace:short:2": 0.04733242103699392
 },
 "vs_baselines": {
  "cell_weeks": 52,
  "cell_weeks_hold": 36,
  "cells_all_weeks_hold": 7,
  "cells_with_failures": [
   "all1:long:1",
   "sh0.25:long:1",
   "sh0.5:long:1",
   "sh1:long:1",
   "trace:long:1",
   "trace:short:2"
  ]
 },
 "vs_pair": {
  "cell_weeks": 52,
  "cell_weeks_hold": 36,
  "cells_all_weeks_hold": 7,
  "cells_with_failures": [
   "all1:long:1",
   "sh0.25:long:1",
   "sh0.5:long:1",
   "sh1:long:1",
   "trace:long:1",
   "trace:short:2"
  ]
 }
}
```

