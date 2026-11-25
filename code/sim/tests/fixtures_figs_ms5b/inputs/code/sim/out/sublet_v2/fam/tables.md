# E7h part fam (design/sublet_v2.md §4, §5, §8.1)

Reduced run: reduced job list (MS3_E7H_REDUCED=1): development cells only; not a result

## Runs (r0 = cost over BL0a; families: ALG / OPT in ratio_opt of summary.json)

| tag | mode | cell | seed | r0 | status | projected | aborted |
|---|---|---|---|---|---|---|---|
| A9 | F-ad | F1_m2_r4:F-ad | 0 | – | ok | – | – |
| A9-noIns | F-ad | F1_m2_r4:F-ad | 0 | – | ok | – | – |
| Sublet | F-ad | F1_m2_r4:F-ad | 0 | – | ok | 0 | False |
| BL1-G | F-ad | F1_m2_r4:F-ad | 0 | – | ok | 0 | False |
| BL5-G | F-ad | F1_m2_r4:F-ad | 0 | – | ok | 0 | False |
| BL1-GP | F-ad | F1_m2_r4:F-ad | 0 | – | ok | 0 | False |
| RR_RENEW | F-ad | F1_m2_r4:F-ad | 0 | – | ok | – | – |
| MARKING | F-ad | F1_m2_r4:F-ad | 0 | – | ok | – | – |
| A9 | F-ss | F2_m2_r4:F-ss | 0 | – | ok | – | – |
| A9-noIns | F-ss | F2_m2_r4:F-ss | 0 | – | ok | – | – |
| Sublet | F-ss | F2_m2_r4:F-ss | 0 | – | ok | 0 | False |
| BL1-G | F-ss | F2_m2_r4:F-ss | 0 | – | ok | 0 | False |
| BL5-G | F-ss | F2_m2_r4:F-ss | 0 | – | ok | 0 | False |
| BL1-GP | F-ss | F2_m2_r4:F-ss | 0 | – | ok | 0 | False |
| RR_RENEW | F-ss | F2_m2_r4:F-ss | 0 | – | ok | – | – |
| MARKING | F-ss | F2_m2_r4:F-ss | 0 | – | ok | – | – |
| A9 | F-eg | F3_b2_T48:F-eg | 0 | – | ok | – | – |
| A9-noIns | F-eg | F3_b2_T48:F-eg | 0 | – | ok | – | – |
| Sublet | F-eg | F3_b2_T48:F-eg | 0 | – | ok | 0 | True |
| BL1-G | F-eg | F3_b2_T48:F-eg | 0 | – | ok | 0 | False |
| BL5-G | F-eg | F3_b2_T48:F-eg | 0 | – | ok | 0 | True |
| BL1-GP | F-eg | F3_b2_T48:F-eg | 0 | – | ok | 0 | False |


## Missing runs (the missing-run rule, §4.5)

| job | tag | mode | cell | seed | why |
|---|---|---|---|---|---|


## Guarded runs

| runs | held | envelope violations | aborts | aborts with S on FB and T0g bound | projected slots | K0 |
|---|---|---|---|---|---|---|
| 12 | 12 | 0 | 2 | 0 | 0 | 0 |


