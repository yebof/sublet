# e9v2: analysis (design/ms7/feasibility/sens.md §2 A-D (C56))

Exploratory, after the MS5b freeze (design/ms7/plan.md D6).

Analysis sha256 6d9772304fe3; design/ms7/registration.md records 6d9772304fe3; matches True; registered full inputs True.

## The guard's per-slot overhead (Sublet - A9; medians over the alignments; split if identical)

| point | sites x LLMs | act s/slot | act ratio | slow step s/slot | split guard s |
|---|---|---|---|---|---|
| e7f_V1_SML | 84 | 0.01891 | 70.92 | 0.01892 | 0.01376 |
| e7f_V2_SML | 147 | 0.04059 | 107 | 0.04061 | 0.02657 |
| e7f_V4_SML | 267 | 0.09345 | 111.3 | 0.09349 | 0.05491 |
| e7f_V8_SML | 507 | 0.2392 | 61.29 | 0.2392 | 0.1313 |
| e7f_V16_SML | 987 | 0.6825 | 27.89 | 0.6826 | 0.3542 |
| e7f_V32_SML | 1947 | 2.236 | 13.2 | 2.236 | 1.04 |
| e7f_V64_SML | 3855 | 7.947 | 6.771 | 7.948 | 3.567 |
| e7f_V8_S | 169 | 0.3902 | 18.1 | 0.3902 | 0.1839 |
| e7f_V8_ML | 338 | 0.2131 | 61.03 | 0.2131 | 0.1161 |
| e7r_V1_SML | 84 | 0.01176 | 46.78 | 0.01177 | 0.008762 |
| e7r_V2_SML | 150 | 0.02166 | 63.58 | 0.02167 | 0.01481 |
| e7r_V4_SML | 276 | 0.04508 | 63.92 | 0.04509 | 0.02931 |
| e7r_V8_SML | 525 | 0.09275 | 34.42 | 0.09278 | 0.05675 |
| e7r_V16_SML | 1005 | 0.2222 | 15.39 | 0.2223 | 0.1172 |
| e7r_V32_SML | 1965 | 0.5322 | 6.296 | 0.5322 | 0.2645 |
| e7r_V64_SML | 3885 | 1.346 | 2.982 | 1.347 | 0.6158 |


## Headline

```json
{
 "act_overhead_s_per_slot_max": 7.9474491200154365,
 "act_overhead_s_per_slot_max_point": "e7f_V64_SML",
 "act_ratio_max": 111.27922212818407,
 "act_ratio_max_point": "e7f_V4_SML",
 "cap_mb": 3072.0,
 "e9v2_1_status": "pass",
 "largest_point_by_menu": {
  "full": {
   "act_overhead_s_per_slot_median": 7.9474491200154365,
   "act_ratio_median": 6.771294721094451,
   "point": "e7f_V64_SML",
   "policies": {
    "A9": {
     "loops_s_per_h": 14.135130229250839,
     "peak_rss_mb": 174.5859375,
     "real_time_over_loops": 254.68460082173576
    },
    "Sublet": {
     "loops_s_per_h": 109.16396525356686,
     "peak_rss_mb": 445.73046875,
     "real_time_over_loops": 32.97791530051051
    }
   },
   "sites_x_llms": 3855
  },
  "reduced": {
   "act_overhead_s_per_slot_median": 1.346436287198028,
   "act_ratio_median": 2.9823016206524513,
   "point": "e7r_V64_SML",
   "policies": {
    "A9": {
     "loops_s_per_h": 9.288059410134641,
     "peak_rss_mb": 168.708984375,
     "real_time_over_loops": 387.5944200003576
    },
    "Sublet": {
     "loops_s_per_h": 24.100810553092742,
     "peak_rss_mb": 249.84375,
     "real_time_over_loops": 149.3725695270456
    }
   },
   "sites_x_llms": 3885
  }
 },
 "n_over_cap": 0,
 "n_runs": 128,
 "peak_rss_mb_max": 452.5546875,
 "peak_rss_mb_max_at": "e7f_V64_SML:Sublet"
}
```

