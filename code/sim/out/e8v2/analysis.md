# e8v2: analysis (design/ms7/feasibility/sens.md §2 A-D (C56))

Exploratory, after the MS5b freeze (design/ms7/plan.md D6).

Analysis sha256 6d9772304fe3; design/ms7/registration.md records 6d9772304fe3; matches True; registered full inputs True.

## Rankings over the alignments (counts) and Sublet's median E

| tier | window | n | same order | Sublet first (fluid) | Sublet first (replay) | E Sublet |
|---|---|---|---|---|---|---|
| S | 60 | 4 | 1 | 0 | 1 | 0.5521 |
| S | 15 | 4 | 3 | 3 | 3 | 0.4228 |
| S | 5 | 4 | 0 | 4 | 0 | 0.3199 |
| M | 60 | 4 | 2 | 0 | 0 | 0.5159 |
| M | 15 | 4 | 2 | 3 | 4 | 0.3697 |
| M | 5 | 4 | 0 | 4 | 0 | 0.2582 |
| L | 60 | 4 | 3 | 1 | 1 | 0.4283 |
| L | 15 | 4 | 3 | 1 | 0 | 0.2976 |
| L | 5 | 4 | 4 | 0 | 0 | 0.2136 |


## Mooncake hour

| window | prefix | same order | Sublet rank (fluid) | Sublet rank (replay) | E Sublet |
|---|---|---|---|---|---|
| 5 | off | True | 2 | 2 | 0.3197 |
| 5 | on | True | 2 | 2 | -0.09607 |
| 15 | off | True | 3 | 3 | 0.2595 |
| 15 | on | True | 3 | 3 | -0.08752 |
| 60 | off | True | 2 | 2 | 0.2141 |
| 60 | on | True | 2 | 2 | -0.04135 |


## Headline

```json
{
 "E_median_range": {
  "A6": {
   "hi": 0.3108866420337717,
   "hi_cell": "S:60",
   "lo": 0.08908017604520024,
   "lo_cell": "L:5",
   "n_cells": 9
  },
  "A9": {
   "hi": 0.5533479584502579,
   "hi_cell": "S:60",
   "lo": 0.2112370131359136,
   "lo_cell": "L:5",
   "n_cells": 9
  },
  "BL1-BO": {
   "hi": 0.5358499494357094,
   "hi_cell": "S:60",
   "lo": 0.08781906424286726,
   "lo_cell": "L:5",
   "n_cells": 9
  },
  "BL5-cur": {
   "hi": 0.5456555065155952,
   "hi_cell": "S:60",
   "lo": 0.2425548813478572,
   "lo_cell": "L:5",
   "n_cells": 9
  },
  "Sublet": {
   "hi": 0.5521207254303229,
   "hi_cell": "S:60",
   "lo": 0.21364432991616417,
   "lo_cell": "L:5",
   "n_cells": 9
  }
 },
 "cells": {
  "n": 36,
  "n_alignments": 36,
  "same_order": 18,
  "sublet_beats_pair_fluid": 29,
  "sublet_beats_pair_replay": 23,
  "sublet_first_fluid": 16,
  "sublet_first_replay": 9
 },
 "cells_reordered": [
  "L:15:1",
  "L:60:3",
  "M:15:1",
  "M:15:3",
  "M:5:1",
  "M:5:2",
  "M:5:3",
  "M:5:4",
  "M:60:3",
  "M:60:4",
  "S:15:3",
  "S:5:1",
  "S:5:2",
  "S:5:3",
  "S:5:4",
  "S:60:1",
  "S:60:2",
  "S:60:3"
 ],
 "mooncake": {
  "off": {
   "E_sublet": {
    "15": 0.2595444714853352,
    "5": 0.31966034260401277,
    "60": 0.21409141490960845
   },
   "n": 3,
   "same_order": 3,
   "sublet_first_replay": 0
  },
  "on": {
   "E_sublet": {
    "15": -0.08751803393512328,
    "5": -0.09607081178587618,
    "60": -0.041345111701554194
   },
   "n": 3,
   "same_order": 3,
   "sublet_first_replay": 0
  }
 }
}
```

