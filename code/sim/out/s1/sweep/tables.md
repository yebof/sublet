# S1: sensitivity of Sublet's saving across the register (design/sim_spec_ms5.md §3)

## Saving over BL0a per point (%, overflow accounting; median [95% CI] over the runs)

| point | row | value | runs | median | ci lo | ci hi | total acc. | abort share |
|---|---|---|---|---|---|---|---|---|
| default | – | default | 12 | 28.41 | 21.37 | 30.97 | 3.82 | 0 |
| alpha02 | alpha | 0.2 | 12 | 51.75 | 43.89 | 53.59 | 6.816 | 0 |
| alpha03 | alpha | 0.3 | 12 | 39.38 | 31.65 | 41.94 | 5.257 | 0 |
| alpha05 | alpha | 0.5 | 12 | 19.34 | 13.04 | 21.98 | 2.621 | 0 |
| alpha06 | alpha | 0.6 | 12 | 10.22 | 5.273 | 12.58 | 1.383 | 0 |
| alphap06 | alpha_p | 0.6 | 12 | 28.41 | 21.37 | 30.97 | 5.057 | 0 |
| alphap10 | alpha_p | 1.0 | 12 | 28.41 | 21.37 | 30.97 | 3.26 | 0 |
| kv05 | mu_split | 0.5 | 12 | 23.16 | 14.72 | 26.95 | 3.014 | 0 |
| kv10 | mu_split | 1 | 12 | 17.2 | 8.061 | 23.24 | 2.212 | 0 |
| scen_warm_peer_rdma | load_scenario | warm peer | 12 | 40.72 | 36.49 | 41.09 | 5.244 | 0 |
| scen_ssd_optimized | load_scenario | SSD optimized | 12 | 40.12 | 35.66 | 40.35 | 5.149 | 0 |
| scen_ssd_stock_safetensors | load_scenario | SSD safetensors | 12 | 30.26 | 24.68 | 31.14 | 3.987 | 0 |
| scen_ssd_stock_pytorch | load_scenario | SSD PyTorch | 12 | 26.55 | 20.39 | 27.52 | 3.522 | 0 |
| scen_a5_10GBps | load_scenario | 10 GB/s | 12 | 33.75 | 27.52 | 34.31 | 4.367 | 0 |
| scen_a5_2GBps | load_scenario | 2 GB/s | 12 | 24.71 | 18.19 | 26.05 | 3.297 | 0 |
| scen_cold_wan_10gbps | load_scenario | WAN 10 Gb/s | 12 | 24.22 | 19.66 | 25.9 | 3.298 | 0 |
| scen_cold_wan_1gbps | load_scenario | WAN 1 Gb/s | 12 | -1.394 | -1.659 | -0.6743 | -0.1892 | 0 |
| phi05 | phi | 0.5 | 12 | 31.59 | 25.29 | 33.49 | 4.251 | 0 |
| kappaL05 | kappa_L | x0.5 | 12 | 27.72 | 21.11 | 30.29 | 3.517 | 0 |
| kappaL2 | kappa_L | x2 | 12 | 29.63 | 22.07 | 31.59 | 4.22 | 0 |
| a5 | catalog | a5 tiers | 12 | 23.48 | 18.82 | 27.24 | 3.529 | 0 |
| catM2 | catalog | M on 2 GPUs | 12 | 29.21 | 21.96 | 31.39 | 4.144 | 0 |
| catLg4 | catalog | L 235B | 12 | 31.62 | 25.32 | 33.68 | 4.502 | 0 |
| L16 | precision | 16 bit | 12 | 22.97 | 17.4 | 26.63 | 2.969 | 0 |
| tiermap | gpt4o_mini | L | 12 | 27.07 | 19.92 | 30.19 | 3.891 | 0 |
| sS0 | s_S | 0 | 12 | 28.42 | 21.41 | 30.96 | 3.783 | 0 |
| sS05 | s_S | 0.5 | 12 | 29.11 | 22.4 | 31.28 | 3.978 | 0 |
| xi1 | xi | one series | 12 | 39.03 | 36.83 | 41.5 | 1.593 | 0 |
| wcfull | wildchat | full | 12 | 27.77 | 21.34 | 31.49 | 3.607 | 0 |
| c0p50 | own_capacity | P50 | 12 | 35.71 | 29.83 | 36.99 | 9.28 | 0 |
| c0p90 | own_capacity | P90 | 12 | 18.26 | 12.06 | 24.12 | 0.7556 | 0 |
| smooth5 | smoothing | 5 min | 12 | 20.29 | 13.38 | 22.66 | 2.862 | 0 |
| smooth60 | smoothing | 60 min | 12 | 42.64 | 34.74 | 43.44 | 4.969 | 0 |
| lease10 | lease_quantile | P10 | 12 | 29.7 | 23.65 | 31.91 | 3.902 | 0 |
| lease50 | lease_quantile | P50 | 12 | 22.45 | 16.41 | 24.87 | 2.981 | 0 |
| layer16 | layer_width | 16 GPUs | 12 | 29.92 | 24.91 | 32.45 | 4.051 | 0 |
| nlayers4 | n_layers | 4 | 12 | 25.67 | 18.08 | 27.26 | 3.476 | 0 |
| nlayers16 | n_layers | 16 | 12 | 30 | 24.33 | 32.92 | 4.068 | 0 |
| prot1h | protected_term | 1 h | 12 | 28.41 | 21.37 | 30.97 | 3.82 | 0 |
| prot1d | protected_term | 1 day | 12 | 28.41 | 21.37 | 30.97 | 3.82 | 0 |
| prothorizon | protected_term | horizon | 12 | 28.41 | 21.37 | 30.97 | 3.82 | 0 |
| buf999 | buffer_quantile | 0.999 | 12 | 27.26 | 22.1 | 28.49 | 3.608 | 0 |
| tight025 | tightness | 0.25 | 12 | 26.8 | 17.79 | 29.11 | 3.555 | 0 |
| tight1 | tightness | 1 | 12 | 29.54 | 24.77 | 30.76 | 3.874 | 0 |
| tight2 | tightness | 2 | 12 | 28.42 | 24.83 | 29.96 | 3.728 | 0 |
| delta0 | delta1 | 0 | 12 | 29.48 | 29.1 | 30.79 | 3.937 | 0 |
| delta02 | delta1 | 0.2 | 12 | 27.44 | 20.19 | 30.03 | 3.721 | 0 |
| strict | slo_class | all strict | 12 | 25.08 | 17.72 | 27.79 | 3.404 | 0 |
| slotier | slo_class | S strict | 12 | 28.34 | 21.32 | 30.9 | 3.813 | 0 |
| fee4 | transfer_fee | rho = 4 | 12 | 23.06 | 14.12 | 25.54 | 3.052 | 0 |
| slow1 | slow_slot | 1 min | 12 | 30.91 | 24.47 | 33.5 | 4.193 | 0 |


## Rows: lowest and highest median saving with the default included (M5)

| row | panel | lo | at | hi | at | span (pp) | complete |
|---|---|---|---|---|---|---|---|
| alpha | a | 10.22 | alpha06 | 51.75 | alpha02 | 41.53 | True |
| alpha_p | a | 28.41 | default | 28.41 | default | 0 | True |
| mu | a | 26.91 | mu2 | 29.62 | mu0.2 | 2.704 | True |
| mu_split | a | 17.2 | kv10 | 28.41 | default | 11.21 | True |
| load_scenario | a | -1.394 | scen_cold_wan_1gbps | 40.72 | scen_warm_peer_rdma | 42.12 | True |
| phi | a | 28.41 | default | 31.59 | phi05 | 3.175 | True |
| kappa_L | b | 27.72 | kappaL05 | 29.63 | kappaL2 | 1.914 | True |
| catalog | b | 23.48 | a5 | 31.62 | catLg4 | 8.137 | True |
| precision | b | 22.97 | L16 | 28.41 | default | 5.45 | True |
| gpt4o_mini | b | 27.07 | tiermap | 28.41 | default | 1.342 | True |
| s_S | b | 28.41 | default | 29.11 | sS05 | 0.6958 | True |
| xi | b | 28.41 | default | 39.03 | xi1 | 10.62 | True |
| wildchat | b | 27.77 | wcfull | 28.41 | default | 0.6416 | True |
| own_capacity | b | 18.26 | c0p90 | 35.71 | c0p50 | 17.45 | True |
| smoothing | b | 20.29 | smooth5 | 42.64 | smooth60 | 22.35 | True |
| lease_quantile | c | 22.45 | lease50 | 29.7 | lease10 | 7.244 | True |
| layer_width | c | 28.41 | default | 29.92 | layer16 | 1.51 | True |
| n_layers | c | 25.67 | nlayers4 | 30 | nlayers16 | 4.332 | True |
| protected_term | c | 28.41 | default | 28.41 | default | 0 | True |
| buffer_quantile | c | 27.26 | buf999 | 28.41 | default | 1.158 | True |
| tightness | b | 26.8 | tight025 | 29.54 | tight1 | 2.745 | True |
| delta1 | a | 27.44 | delta02 | 29.48 | delta0 | 2.042 | True |
| slo_class | c | 25.08 | strict | 28.41 | default | 3.335 | True |
| transfer_fee | a | 23.06 | fee4 | 28.41 | default | 5.357 | True |
| slow_slot | a | 28.41 | default | 30.91 | slow1 | 2.497 | True |


## Rows and points not run (§3.5)

| row | reason |
|---|---|
| warm-peer and SSD load models | no sweep in the register |
| client unit 1/u | no sweep in the register |
| pool width zeta | no sweep in the register |
| tier map | its sweep is its default |
| per-tier tokens-per-conversation factor | no traced source |
| clock alignment at local midnight | not built: no source for the regions' UTC offsets (MS1 spec §10 S12) |
| non-causal smoothing window | not built: the builder has a trailing mean only (instance._trailing_mean) |
| scenario assignment per region pair | not built |
| offered layers V_l as the whole block below the lease-size quantile | the dense arrays of A8's safe expert exceed the 3 GB cap at the week, and a one-day probe completed one slow slot in its window; the row sweeps 4 and 16 layers in its place (M37) |
| offered layers V_l as a share of the mean lendable capacity | not defined |
| a uniform kappa multiplier | identical to the default: a uniform multiplier cancels exactly through Gamma; the row varies L's kappa alone (M8) |


## Checks (§3.10)

| check | status |
|---|---|
| S1-0 | pass |
| S1-1 | pass |
| S1-2 | pass |
| S1-3 | pass |
| S1-4 | informative |


