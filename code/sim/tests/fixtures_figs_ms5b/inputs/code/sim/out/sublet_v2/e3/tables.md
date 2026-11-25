# E7h part e3 (design/sublet_v2.md §4, §5, §8.1)

Reduced run: reduced job list (MS3_E7H_REDUCED=1): development cells only; not a result

## Runs (r0 = cost over BL0a; families: ALG / OPT in ratio_opt of summary.json)

| tag | mode | cell | seed | r0 | status | projected | aborted |
|---|---|---|---|---|---|---|---|
| Sublet | shared | b1:c101 | 0 | 0.8467 | ok | 8 | False |
| Sublet | siloed | b1:c101 | 0 | 0.8467 | ok | – | – |
| A9 | shared | b1:c101 | 0 | 0.6644 | ok | – | – |
| A9 | siloed | b1:c101 | 0 | 0.6644 | ok | – | – |
| BL1 | shared | b1:c101 | 0 | 0.7083 | ok | – | – |
| BL1 | siloed | b1:c101 | 0 | 0.7083 | ok | – | – |
| BL5-cur | shared | b1:c101 | 0 | 0.7296 | ok | – | – |
| BL5-cur | siloed | b1:c101 | 0 | 0.7296 | ok | – | – |
| Sublet-MS4 | shared | b1:c101 | 0 | 0.9461 | ok | 0 | True |
| Sublet-MS4 | siloed | b1:c101 | 0 | 0.9461 | ok | – | – |
| Sublet | shared | b8:c101 | 0 | 0.8434 | ok | 9 | False |
| Sublet | siloed | b8:c101 | 0 | 0.9894 | ok | – | – |
| A9 | shared | b8:c101 | 0 | 0.6609 | ok | – | – |
| A9 | siloed | b8:c101 | 0 | 0.966 | ok | – | – |
| BL1 | shared | b8:c101 | 0 | 0.7004 | ok | – | – |
| BL1 | siloed | b8:c101 | 0 | 1.047 | ok | – | – |
| BL5-cur | shared | b8:c101 | 0 | 0.7221 | ok | – | – |
| BL5-cur | siloed | b8:c101 | 0 | 0.993 | ok | – | – |
| Sublet-MS4 | shared | b8:c101 | 0 | 0.9071 | ok | 0 | True |
| Sublet-MS4 | siloed | b8:c101 | 0 | 0.9539 | ok | – | – |


## Missing runs (the missing-run rule, §4.5)

| job | tag | mode | cell | seed | why |
|---|---|---|---|---|---|


## Guarded runs

| runs | held | envelope violations | aborts | aborts with S on FB and T0g bound | projected slots | K0 |
|---|---|---|---|---|---|---|
| 20 | 20 | 0 | 10 | 0 | 69 | 0 |


