# E7r tune: the selected settings (rules T and W, e7r_select.py)

| family | rule | config | policy | params | median r0 L-tr | median W0 | eligible | configs |
|---|---|---|---|---|---|---|---|---|
| BL1 | T | BL1-g04 | BL1 | {'backoff_cap': 288} | 0.5853 | 1.099 | 12 | 12 |
| BL1 | W | BL1-g08 | A9 | {'target': 'ceil', 'release': 'now', 'site_rule': 'static', 'mbb': False, 'commit': False, 'insure': False} | 0.615 | 0.8589 | 12 | 12 |
| BL2 | T | BL2-g04 | BL2 | {'contract_rule': 'c2'} | 0.6645 | 0.9317 | 8 | 8 |
| BL2 | W | BL2-g04 | BL2 | {'contract_rule': 'c2'} | 0.6645 | 0.9317 | 8 | 8 |
| BL3 | T | BL3-g00 | BL3 | {'n_extra': 0} | 0.6487 | 1.912 | 16 | 16 |
| BL3 | W | BL3-g05 | BL3 | {'n_extra': 0, 'contract_rule': 'c2', 'react_at': 'death'} | 0.657 | 0.9139 | 16 | 16 |
| BL4 | T | BL4-g01 | BL4 | {'window_min': 30} | 0.8762 | 1.114 | 6 | 6 |
| BL4 | W | BL4-g05 | BL4 | {'window_min': 120, 'contract_rule': 'c2'} | 0.9205 | 1.014 | 6 | 6 |
| BL5 | T | BL5-g08 | BL5 | {'use_current_slot': True, 'contract_rule': 'c2'} | 0.6707 | 0.9264 | 14 | 18 |
| BL5 | W | BL5-g16 | BL5 | {'use_current_slot': True, 'tau_min': 60} | 0.7934 | 0.839 | 14 | 18 |
| MPC | T | MPC-g04 | MPC | {'contract_rule': 'c2'} | 0.609 | 0.7602 | 8 | 8 |
| MPC | W | MPC-g04 | MPC | {'contract_rule': 'c2'} | 0.609 | 0.7602 | 8 | 8 |


Aliases (W equal to T): BL2-W = BL2-T, MPC-W = MPC-T

