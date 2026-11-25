# E7: stress block (design/sim_spec_ms4.md §3.7(d))

## r0 = week cost / BL0a (overflow accounting) per stress mode, alignment 1 (mean over the seeds)

| mode | tag | runs | r0 mean | announcements / site-day | abort share |
|---|---|---|---|---|---|
| L-eg | Sublet | 3 | 1.099 | 288 | 1 |
| L-eg | A7G | 3 | 1.098 | 288 | 1 |
| L-eg | A7 | 3 | 1.595 | 288 | – |
| L-eg | A6 | 3 | 1.092 | 288 | – |
| L-eg | BL5 | 3 | 1.213 | 288 | – |
| L-eg | BL1 | 3 | 2.028 | 288 | – |
| L-eg | BL2 | 3 | 1.974 | 288 | – |
| L-eg | BL4 | 3 | 1.047 | 288 | – |
| L-ss | Sublet | 3 | 1.1 | 286.2 | 1 |
| L-ss | A7G | 3 | 1.097 | 286.2 | 1 |
| L-ss | A7 | 3 | 1.585 | 286.2 | – |
| L-ss | A6 | 3 | 1.099 | 286.2 | – |
| L-ss | BL5 | 3 | 1.206 | 286.2 | – |
| L-ss | BL1 | 3 | 2.016 | 286.2 | – |
| L-ss | BL2 | 3 | 1.956 | 286.2 | – |
| L-ss | BL4 | 3 | 1.043 | 286.2 | – |
| L-iid-0.05 | Sublet | 3 | 0.7208 | 14.2 | 0 |
| L-iid-0.05 | A7G | 3 | 0.8123 | 14.2 | 0 |
| L-iid-0.05 | A7 | 3 | 0.8123 | 14.2 | – |
| L-iid-0.05 | A6 | 3 | 1.094 | 14.2 | – |
| L-iid-0.05 | BL5 | 3 | 0.7208 | 14.2 | – |
| L-iid-0.05 | BL1 | 3 | 0.7195 | 14.2 | – |
| L-iid-0.05 | BL2 | 3 | 0.7372 | 14.2 | – |
| L-iid-0.05 | BL4 | 3 | 0.901 | 14.2 | – |
| L-iid-0.2 | Sublet | 3 | 0.8466 | 57.22 | 0 |
| L-iid-0.2 | A7G | 3 | 1.079 | 57.22 | 0.3333 |
| L-iid-0.2 | A7 | 3 | 1.078 | 57.22 | – |
| L-iid-0.2 | A6 | 3 | 1.1 | 57.22 | – |
| L-iid-0.2 | BL5 | 3 | 0.8466 | 57.22 | – |
| L-iid-0.2 | BL1 | 3 | 0.8424 | 57.22 | – |
| L-iid-0.2 | BL2 | 3 | 0.8963 | 57.22 | – |
| L-iid-0.2 | BL4 | 3 | 0.9689 | 57.22 | – |
| L-co | Sublet | 3 | 1.099 | 275.9 | 1 |
| L-co | A7G | 3 | 1.096 | 275.9 | 1 |
| L-co | A7 | 3 | 1.541 | 275.9 | – |
| L-co | A6 | 3 | 1.097 | 275.9 | – |
| L-co | BL5 | 3 | 1.172 | 275.9 | – |
| L-co | BL1 | 3 | 1.884 | 275.9 | – |
| L-co | BL2 | 3 | 1.865 | 275.9 | – |
| L-co | BL4 | 3 | 1.036 | 275.9 | – |


## W0 (note §5.5): the largest 3-seed mean of r0 over the five stress modes

| tag | W0 | mode | criterion S (<= 1.05) |
|---|---|---|---|
| Sublet | 1.1 | L-ss | False |
| A7G | 1.098 | L-eg | False |
| A7 | 1.595 | L-eg | False |
| A6 | 1.1 | L-iid-0.2 | False |
| BL5 | 1.213 | L-eg | False |
| BL1 | 2.028 | L-eg | False |
| BL2 | 1.974 | L-eg | False |
| BL4 | 1.047 | L-eg | True |


## Checks (§3.11)

| check | status |
|---|---|
| E7-1 | pass |
| E7-2 | pass |
| E7-4 | pass |
| E7-6 | pass |
| E7-8 | informative |
| E7-11 | informative |


