# s1v2: analysis (design/ms7/feasibility/sens.md §2 A-D (C56))

Exploratory, after the MS5b freeze (design/ms7/plan.md D6).

Analysis sha256 6d9772304fe3; design/ms7/registration.md records 6d9772304fe3; matches True; registered full inputs True.

## Points (median saving %, Delta = Sublet - best of BL1-BO and BL5-cur in r0 terms)

| point | row | Sublet | A9 | BL1-BO | BL5-cur | Delta median | weeks hold |
|---|---|---|---|---|---|---|---|
| default | – | 45.78 | 45.78 | 35.92 | 37.75 | 0.05013 | 4/4 |
| alpha02 | alpha | 67.39 | 67.45 | 66.5 | 59.94 | 0.01597 | 3/4 |
| alpha03 | alpha | 57.31 | 57.32 | 51.1 | 48.2 | 0.03527 | 4/4 |
| alpha05 | alpha | 34.25 | 34.26 | 20.33 | 27.48 | 0.0617 | 4/4 |
| alpha06 | alpha | 0.2974 | 0.7396 | 4.897 | 17.36 | -0.1753 | 0/4 |
| alphap06 | alpha_p | 23.48 | 23.47 | 35.92 | 37.75 | -0.1758 | 0/4 |
| alphap10 | alpha_p | 45.87 | 45.87 | 35.92 | 37.75 | 0.05103 | 4/4 |
| kv05 | mu_split | 41.05 | 41.49 | 26.75 | 34.63 | 0.05321 | 4/4 |
| kv10 | mu_split | 35.86 | 38.28 | 19.17 | 32.21 | 0.01367 | 3/4 |
| scen_warm_peer_rdma | load_scenario | 50.43 | 50.43 | 37.46 | 49.44 | 0.008512 | 4/4 |
| scen_ssd_optimized | load_scenario | 50.1 | 50.1 | 37.4 | 48.62 | 0.0131 | 4/4 |
| scen_ssd_stock_safetensors | load_scenario | 46.15 | 46.16 | 36.09 | 39.18 | 0.05524 | 4/4 |
| scen_ssd_stock_pytorch | load_scenario | 43.84 | 43.93 | 34.93 | 34.56 | 0.06015 | 4/4 |
| scen_a5_10GBps | load_scenario | 47.48 | 47.48 | 36.52 | 42.83 | 0.04522 | 4/4 |
| scen_a5_2GBps | load_scenario | 43.15 | 43.24 | 34.6 | 33.06 | 0.05976 | 4/4 |
| scen_cold_wan_10gbps | load_scenario | 42.31 | 42.31 | 34.22 | 31.99 | 0.06094 | 4/4 |
| scen_cold_wan_1gbps | load_scenario | -10.87 | -11.65 | -15.9 | 2.89 | -0.1555 | 0/4 |
| phi05 | phi | 46.38 | 46.38 | 36.09 | 40.23 | 0.05319 | 4/4 |
| kappaL05 | kappa_L | 45.81 | 45.81 | 36.08 | 36.97 | 0.05342 | 4/4 |
| kappaL2 | kappa_L | 45.79 | 45.79 | 35.33 | 39.06 | 0.05335 | 4/4 |
| a5 | catalog | 43.21 | 43.25 | 28.44 | 34.81 | 0.07118 | 4/4 |
| catM2 | catalog | 45.48 | 45.48 | 33.41 | 38.69 | 0.06128 | 4/4 |
| catLg4 | catalog | 47.34 | 47.45 | 42.31 | 41.37 | 0.02966 | 4/4 |
| L16 | precision | 42.55 | 42.58 | 36.04 | 31.41 | 0.04631 | 4/4 |
| tiermap | gpt4o_mini | 45.58 | 45.58 | 34.9 | 37.26 | 0.05827 | 4/4 |
| sS0 | s_S | 45.99 | 45.99 | 37.81 | 37.73 | 0.0462 | 4/4 |
| sS05 | s_S | 45.74 | 45.73 | 36.07 | 38.3 | 0.05011 | 4/4 |
| xi1 | xi | 51.36 | 51.36 | 51.15 | 43.86 | 0.002595 | 3/4 |
| wcfull | wildchat | 45.91 | 45.92 | 37.52 | 37.23 | 0.0532 | 4/4 |
| c0p50 | own_capacity | 48.77 | 48.77 | 36.7 | 43.09 | 0.04869 | 4/4 |
| c0p90 | own_capacity | 43.57 | 43.57 | 35.03 | 34.37 | 0.04561 | 4/4 |
| smooth5 | smoothing | 38.45 | 38.45 | 24.85 | 31.82 | 0.06501 | 4/4 |
| smooth60 | smoothing | 51.92 | 51.92 | 48.28 | 47.67 | 0.03456 | 4/4 |
| lease10 | lease_quantile | 46.61 | 46.66 | 36.44 | 39.95 | 0.05085 | 4/4 |
| lease50 | lease_quantile | 43.78 | 43.78 | 34 | 31.59 | 0.08045 | 4/4 |
| layer16 | layer_width | 48 | 48 | 44.43 | 40.63 | 0.02633 | 4/4 |
| nlayers4 | n_layers | 42.16 | 42.14 | 18.15 | 34.84 | 0.0782 | 4/4 |
| nlayers16 | n_layers | 47.74 | 47.75 | 44.39 | 40.96 | 0.02947 | 4/4 |
| prot1h | protected_term | 45.78 | 45.78 | 35.92 | 37.75 | 0.05013 | 4/4 |
| prot1d | protected_term | 45.78 | 45.78 | 35.92 | 37.75 | 0.05013 | 4/4 |
| prothorizon | protected_term | 45.78 | 45.78 | 35.92 | 37.75 | 0.05013 | 4/4 |
| tight025 | tightness | 43.62 | 43.61 | 18.14 | 36.69 | 0.0776 | 4/4 |
| tight1 | tightness | 44.89 | 44.9 | 40.37 | 36.52 | 0.04153 | 4/4 |
| tight2 | tightness | 39.67 | 39.68 | 37.27 | 32.65 | 0.01796 | 4/4 |
| delta0 | delta1 | 47.09 | 47.09 | 36.01 | 36.86 | 0.07695 | 4/4 |
| delta02 | delta1 | 43.5 | 43.5 | 33.47 | 36.77 | 0.04605 | 4/4 |
| strict | slo_class | 43.13 | 43.13 | 31.76 | 34.39 | 0.0545 | 4/4 |
| slotier | slo_class | 45.75 | 45.75 | 35.91 | 37.66 | 0.04987 | 4/4 |
| fee4 | transfer_fee | 41.18 | 41.19 | 30.17 | 31.74 | 0.05984 | 4/4 |
| slow1 | slow_slot | 41.22 | 45.86 | 40.09 | 34.3 | 0.01822 | 2/4 |
| mu0.2 | mu | 46.91 | 46.91 | 36.3 | 39.33 | 0.05725 | 4/4 |
| mu0.5 | mu | 46.56 | 46.56 | 36.16 | 38.74 | 0.05538 | 4/4 |
| mu2 | mu | 45.24 | 45.26 | 35.45 | 35.84 | 0.04744 | 4/4 |
| kappaM05 | kappa_M | 45.79 | 45.79 | 35.26 | 38.96 | 0.05453 | 4/4 |
| kappaM2 | kappa_M | 45.83 | 45.83 | 36.24 | 36.92 | 0.05042 | 4/4 |
| fee8 | transfer_fee | 16.77 | 16.93 | -3.339 | 12.59 | 0.02864 | 3/4 |
| fee16 | transfer_fee | -8.393 | -29.02 | -70.37 | 1.167 | -0.0937 | 0/4 |
| buf999 | buffer_quantile | 46.08 | 46.08 | 35.33 | 37.4 | 0.05535 | 4/4 |
| q28_rf | q28_rf | 45.28 | 45.31 | 36.92 | 39.66 | 0.03384 | 4/4 |
| q28_vr | q28_vr | 45.78 | 45.78 | 35.92 | 37.75 | 0.05013 | 4/4 |


## W0 (Sublet's median W0; weeks with Sublet's W0 < 1 and below BL1-BO, BL5-cur and BL4)

| point | Sublet W0 | weeks hold | source |
|---|---|---|---|
| scen_warm_peer_rdma | 0.5851 | 2/2 | s1v2 |
| scen_ssd_optimized | 0.5928 | 2/2 | s1v2 |
| scen_ssd_stock_safetensors | 0.8552 | 2/2 | s1v2 |
| scen_ssd_stock_pytorch | 0.7798 | 2/2 | s1v2 |
| scen_a5_10GBps | 0.6953 | 2/2 | s1v2 |
| scen_a5_2GBps | 0.81 | 2/2 | s1v2 |
| scen_cold_wan_10gbps | 0.7487 | 2/2 | s1v2 |
| scen_cold_wan_1gbps | 1.102 | 0/2 | s1v2 |
| fee4 | 1.011 | 0/2 | s1v2 |
| fee8 | 1.027 | 0/2 | s1v2 |
| fee16 | 1.06 | 0/2 | s1v2 |
| default | 0.7779 | 2/2 | main |


## Seed spread (largest |r0 at seed k - r0 at seed 0|; the confirmation's parts main and seeds)

| tag | max |diff| | at | pairs | missing |
|---|---|---|---|---|
| Sublet | 0 | L-tr:301:1 | 56 | 0 |
| BL1 | 0.009616 | L-ss:301:2 | 56 | 0 |
| BL5-cur | 0.007901 | L-co:302:1 | 56 | 0 |


## Headline

```json
{
 "A9": {
  "default": 45.775376802088914,
  "hi": 67.45027717059438,
  "hi_point": "alpha02",
  "lo": -29.02360591261501,
  "lo_point": "fee16"
 },
 "BL1-BO": {
  "default": 35.92281626637086,
  "hi": 66.49808096264827,
  "hi_point": "alpha02",
  "lo": -70.36775718553258,
  "lo_point": "fee16"
 },
 "BL5-cur": {
  "default": 37.75385772928212,
  "hi": 59.94386545947119,
  "hi_point": "alpha02",
  "lo": 1.1665082162465257,
  "lo_point": "fee16"
 },
 "Sublet": {
  "default": 45.7768175277256,
  "hi": 67.38559552162013,
  "hi_point": "alpha02",
  "lo": -10.871544432202173,
  "lo_point": "scen_cold_wan_1gbps"
 },
 "max_span": 67.08817236132471,
 "max_span_row": "alpha",
 "n_points": 58,
 "point_weeks": 232,
 "point_weeks_hold": 210,
 "points_all_weeks_hold": 49,
 "points_with_flips": [
  "alpha02",
  "alpha06",
  "alphap06",
  "fee16",
  "fee8",
  "kv10",
  "scen_cold_wan_1gbps",
  "slow1",
  "xi1"
 ],
 "q28": {
  "q28_rf": {
   "by_tag": {
    "A9": 45.31236110029491,
    "BL1-BO": 36.91831083719576,
    "BL5-cur": 39.664644113136546,
    "Sublet": 45.282889747159466
   },
   "n_weeks": 4,
   "weeks_hold": 4
  },
  "q28_vr": {
   "by_tag": {
    "A9": 45.775376802088914,
    "BL1-BO": 35.92281626637086,
    "BL5-cur": 37.75385772928212,
    "Sublet": 45.7768175277256
   },
   "n_weeks": 4,
   "weeks_hold": 4
  }
 },
 "register_points": [
  "L16",
  "a5",
  "alpha02",
  "alpha03",
  "alpha05",
  "alpha06",
  "alphap06",
  "alphap10",
  "buf999",
  "c0p50",
  "c0p90",
  "catLg4",
  "catM2",
  "default",
  "delta0",
  "delta02",
  "fee16",
  "fee4",
  "fee8",
  "kappaL05",
  "kappaL2",
  "kappaM05",
  "kappaM2",
  "kv05",
  "kv10",
  "layer16",
  "lease10",
  "lease50",
  "mu0.2",
  "mu0.5",
  "mu2",
  "nlayers16",
  "nlayers4",
  "phi05",
  "prot1d",
  "prot1h",
  "prothorizon",
  "sS0",
  "sS05",
  "scen_a5_10GBps",
  "scen_a5_2GBps",
  "scen_cold_wan_10gbps",
  "scen_cold_wan_1gbps",
  "scen_ssd_optimized",
  "scen_ssd_stock_pytorch",
  "scen_ssd_stock_safetensors",
  "scen_warm_peer_rdma",
  "slotier",
  "slow1",
  "smooth5",
  "smooth60",
  "strict",
  "tiermap",
  "tight025",
  "tight1",
  "tight2",
  "wcfull",
  "xi1"
 ],
 "rows_span_above": [
  "alpha",
  "alpha_p",
  "load_scenario",
  "smoothing",
  "transfer_fee"
 ],
 "seed_spread_max": {
  "BL1": 0.00961577154224691,
  "BL5-cur": 0.007900596919719671,
  "Sublet": 0.0
 },
 "span_threshold_pp": 10.0,
 "sublet_minus_a9_r0_median": 0.0
}
```

## W0 headline

```json
{
 "n_points": 12,
 "n_sublet_W0": 24,
 "point_weeks": 24,
 "point_weeks_hold": 16,
 "points_all_weeks_hold": 8,
 "points_with_failures": [
  "fee16",
  "fee4",
  "fee8",
  "scen_cold_wan_1gbps"
 ],
 "sublet_W0_below_1": 16,
 "sublet_W0_max": 1.1061629901065522,
 "sublet_W0_max_at": "scen_cold_wan_1gbps:302"
}
```

