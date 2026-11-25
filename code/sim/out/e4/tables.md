# E4: predictions (design/sim_spec_ms4.md §6)

## P-hat days (E4-4): methods and MILP statuses

| panel | c | mu | pred | milp | lp_round | none | columns | max gap | assembled |
|---|---|---|---|---|---|---|---|---|---|
| azure | 1 | 1 | prev | 5 | 0 | 1 | 386 | 0.00855 | True |
| azure | 1 | 1 | phase15 | 5 | 0 | 1 | 386 | 0.008369 | True |
| azure | 1 | 1 | phase30 | 5 | 0 | 1 | 386 | 0.009012 | True |
| azure | 1 | 1 | phase60 | 5 | 0 | 1 | 386 | 0.009037 | True |
| azure | 1 | 1 | phase120 | 5 | 0 | 1 | 386 | 0.00922 | True |
| azure | 1 | 1 | amp0.5 | 5 | 0 | 1 | 192 | 0.02441 | True |
| azure | 1 | 1 | amp0.75 | 5 | 0 | 1 | 289 | 0.01393 | True |
| azure | 1 | 1 | amp1.25 | 5 | 0 | 1 | 483 | 0.006913 | True |
| azure | 1 | 1 | amp1.5 | 5 | 0 | 1 | 577 | 0.00525 | True |
| azure | 1 | 1 | del_p90 | 5 | 0 | 1 | 325 | 0.01622 | True |
| azure | 1 | 1 | inj3x30 | 5 | 0 | 1 | 590 | 0.009531 | True |
| azure | 1 | 1 | empty | 0 | 0 | 6 | 0 | – | True |
| azure | 1 | 1 | exact | 5 | 0 | 1 | 386 | 0.00855 | True |
| azure | 1 | 0.2 | prev | 5 | 0 | 1 | 385 | 0.007864 | True |
| azure | 1 | 0.5 | prev | 5 | 0 | 1 | 385 | 0.007835 | True |
| azure | 1 | 2 | prev | 5 | 0 | 1 | 386 | 0.008722 | True |
| azure | 2 | 1 | prev | 5 | 0 | 1 | 389 | 0.005418 | True |
| azure | 2 | 1 | phase15 | 5 | 0 | 1 | 388 | 0.006773 | True |
| azure | 2 | 1 | phase30 | 5 | 0 | 1 | 389 | 0.00593 | True |
| azure | 2 | 1 | phase60 | 5 | 0 | 1 | 390 | 0.005418 | True |
| azure | 2 | 1 | phase120 | 5 | 0 | 1 | 388 | 0.006155 | True |
| azure | 2 | 1 | amp0.5 | 5 | 0 | 1 | 192 | 0.009725 | True |
| azure | 2 | 1 | amp0.75 | 5 | 0 | 1 | 293 | 0.009334 | True |
| azure | 2 | 1 | amp1.25 | 5 | 0 | 1 | 483 | 0.005251 | True |
| azure | 2 | 1 | amp1.5 | 5 | 0 | 1 | 577 | 0.004883 | True |
| azure | 2 | 1 | del_p90 | 5 | 0 | 1 | 324 | 0.01144 | True |
| azure | 2 | 1 | inj3x30 | 5 | 0 | 1 | 648 | 0.003052 | True |
| azure | 2 | 1 | empty | 0 | 0 | 6 | 0 | – | True |
| azure | 2 | 1 | exact | 5 | 0 | 1 | 389 | 0.005418 | True |
| azure | 2 | 0.2 | prev | 5 | 0 | 1 | 388 | 0.006149 | True |
| azure | 2 | 0.5 | prev | 5 | 0 | 1 | 388 | 0.005413 | True |
| azure | 2 | 2 | prev | 5 | 0 | 1 | 389 | 0.006065 | True |
| burstgpt | 1 | 1 | prev | 4 | 0 | 2 | 377 | 0.005345 | True |
| burstgpt | 1 | 1 | phase15 | 4 | 0 | 2 | 370 | 0.004808 | True |
| burstgpt | 1 | 1 | phase30 | 4 | 0 | 2 | 370 | 0.006812 | True |
| burstgpt | 1 | 1 | phase60 | 4 | 0 | 2 | 369 | 0.004929 | True |
| burstgpt | 1 | 1 | phase120 | 4 | 0 | 2 | 343 | 0.005739 | True |
| burstgpt | 1 | 1 | amp0.5 | 4 | 0 | 2 | 185 | 0.009494 | True |
| burstgpt | 1 | 1 | amp0.75 | 4 | 0 | 2 | 283 | 0.005413 | True |
| burstgpt | 1 | 1 | amp1.25 | 4 | 0 | 2 | 467 | 0.003996 | True |
| burstgpt | 1 | 1 | amp1.5 | 4 | 0 | 2 | 562 | 0.002344 | True |
| burstgpt | 1 | 1 | del_p90 | 4 | 0 | 2 | 332 | 0.02449 | True |
| burstgpt | 1 | 1 | inj3x30 | 4 | 0 | 2 | 561 | 0.004845 | True |
| burstgpt | 1 | 1 | empty | 0 | 0 | 6 | 0 | – | True |
| burstgpt | 1 | 1 | exact | 4 | 0 | 2 | 351 | 0.005345 | True |
| burstgpt | 1 | 0.2 | prev | 4 | 0 | 2 | 377 | 0.004333 | True |
| burstgpt | 1 | 0.5 | prev | 4 | 0 | 2 | 377 | 0.004785 | True |
| burstgpt | 1 | 2 | prev | 4 | 0 | 2 | 378 | 0.006265 | True |
| burstgpt | 2 | 1 | prev | 4 | 0 | 2 | 380 | 0.001767 | True |
| burstgpt | 2 | 1 | phase15 | 4 | 0 | 2 | 373 | 0.002153 | True |
| burstgpt | 2 | 1 | phase30 | 4 | 0 | 2 | 372 | 0.001355 | True |
| burstgpt | 2 | 1 | phase60 | 4 | 0 | 2 | 370 | 0.00202 | True |
| burstgpt | 2 | 1 | phase120 | 4 | 0 | 2 | 343 | 0.001942 | True |
| burstgpt | 2 | 1 | amp0.5 | 4 | 0 | 2 | 188 | 0.005894 | True |
| burstgpt | 2 | 1 | amp0.75 | 4 | 0 | 2 | 284 | 0.00336 | True |
| burstgpt | 2 | 1 | amp1.25 | 4 | 0 | 2 | 470 | 0.001857 | True |
| burstgpt | 2 | 1 | amp1.5 | 4 | 0 | 2 | 564 | 0.0007781 | True |
| burstgpt | 2 | 1 | del_p90 | 4 | 0 | 2 | 333 | 0.01767 | True |
| burstgpt | 2 | 1 | inj3x30 | 4 | 0 | 2 | 513 | 0.002832 | True |
| burstgpt | 2 | 1 | empty | 0 | 0 | 6 | 0 | – | True |
| burstgpt | 2 | 1 | exact | 4 | 0 | 2 | 353 | 0.001764 | True |
| burstgpt | 2 | 0.2 | prev | 4 | 0 | 2 | 380 | 0.001557 | True |
| burstgpt | 2 | 0.5 | prev | 4 | 0 | 2 | 379 | 0.001583 | True |
| burstgpt | 2 | 2 | prev | 4 | 0 | 2 | 380 | 0.002372 | True |

## OPT_eager of the ratio day, and LP_core (the PDs' covering program)

| panel | c | d* | LB | LB source | incumbent | gap | MILP status | LP_core |
|---|---|---|---|---|---|---|---|---|
| azure | 1 | 2 | 500.9 | milp_dual | 505.3 | 0.00855 | 1 | 49.29 |
| azure | 2 | 2 | 497 | milp_dual | 499.7 | 0.005418 | 1 | 48.35 |
| burstgpt | 1 | 1 | 527.7 | milp_dual | 527.8 | 0.0002351 | 1 | 61.61 |
| burstgpt | 2 | 1 | 520 | milp_dual | 520 | 6.858e-05 | 0 | 60.49 |

## Ratio day: x = q eta / LB_eager and ALG / LB (median over alignments x seeds)

| panel | pred | x | psi_01 | psi_03 | psi_05 | a2_frac | a5 |
|---|---|---|---|---|---|---|---|
| azure | prev | 1.048 | 0.4615 | 0.3792 | 0.3334 | 0.2639 | 1.474 |
| azure | phase15 | 1.013 | 0.4437 | 0.3647 | 0.318 | 0.2639 | 1.469 |
| azure | phase30 | 1.149 | 0.4332 | 0.3583 | 0.3184 | 0.2639 | 1.534 |
| azure | phase60 | 1.479 | 0.4829 | 0.3849 | 0.33 | 0.2639 | 1.656 |
| azure | phase120 | 2.048 | 0.5247 | 0.406 | 0.3419 | 0.2639 | 1.942 |
| azure | amp0.5 | 1.478 | 0.4539 | 0.3727 | 0.3244 | 0.2639 | 1.731 |
| azure | amp0.75 | 1.226 | 0.4494 | 0.3781 | 0.3338 | 0.2639 | 1.591 |
| azure | amp1.25 | 0.9848 | 0.4678 | 0.3842 | 0.336 | 0.2639 | 1.425 |
| azure | amp1.5 | 1.06 | 0.4663 | 0.3835 | 0.3352 | 0.2639 | 1.448 |
| azure | del_p90 | 1.179 | 0.4638 | 0.383 | 0.3353 | 0.2639 | 1.547 |
| azure | inj3x30 | 1.405 | 0.4326 | 0.3634 | 0.3237 | 0.2639 | 1.87 |
| azure | empty | 2.034 | 0.2459 | 0.2459 | 0.2459 | 0.2639 | 2.021 |
| azure | exact | 0 | 0.4058 | 0.3475 | 0.3095 | 0.2639 | 1.028 |
| burstgpt | prev | 1.892 | 0.634 | 0.4865 | 0.4067 | 0.307 | 1.761 |
| burstgpt | phase15 | 1.823 | 0.6132 | 0.4745 | 0.3973 | 0.307 | 1.705 |
| burstgpt | phase30 | 1.736 | 0.6012 | 0.4646 | 0.3909 | 0.307 | 1.681 |
| burstgpt | phase60 | 1.73 | 0.6073 | 0.4669 | 0.3926 | 0.307 | 1.68 |
| burstgpt | phase120 | 1.915 | 0.6627 | 0.4985 | 0.4124 | 0.307 | 1.771 |
| burstgpt | amp0.5 | 1.77 | 0.6406 | 0.4904 | 0.4091 | 0.307 | 1.716 |
| burstgpt | amp0.75 | 1.827 | 0.6404 | 0.4904 | 0.4091 | 0.307 | 1.741 |
| burstgpt | amp1.25 | 1.958 | 0.6347 | 0.4884 | 0.4082 | 0.307 | 1.785 |
| burstgpt | amp1.5 | 2.023 | 0.6345 | 0.487 | 0.4076 | 0.307 | 1.825 |
| burstgpt | del_p90 | 1.725 | 0.6382 | 0.4878 | 0.4077 | 0.307 | 1.707 |
| burstgpt | inj3x30 | 1.987 | 0.6061 | 0.4702 | 0.397 | 0.307 | 1.806 |
| burstgpt | empty | 1.693 | 0.2886 | 0.2886 | 0.2886 | 0.307 | 1.68 |
| burstgpt | exact | 0 | 0.2848 | 0.2816 | 0.2796 | 0.307 | 1.145 |

## Ratio day, fractional series over LP_core: x_core = q eta / LP_core and ALG / LP_core (median)

| panel | pred | x_core | psi_01 | psi_03 | psi_05 | a2_frac |
|---|---|---|---|---|---|---|
| azure | prev | 10.71 | 4.718 | 3.876 | 3.408 | 2.698 |
| azure | phase15 | 10.35 | 4.534 | 3.728 | 3.25 | 2.698 |
| azure | phase30 | 11.74 | 4.427 | 3.662 | 3.255 | 2.698 |
| azure | phase60 | 15.12 | 4.936 | 3.934 | 3.374 | 2.698 |
| azure | phase120 | 20.94 | 5.363 | 4.15 | 3.495 | 2.698 |
| azure | amp0.5 | 15.1 | 4.64 | 3.809 | 3.316 | 2.698 |
| azure | amp0.75 | 12.53 | 4.593 | 3.864 | 3.412 | 2.698 |
| azure | amp1.25 | 10.06 | 4.782 | 3.927 | 3.435 | 2.698 |
| azure | amp1.5 | 10.83 | 4.766 | 3.921 | 3.427 | 2.698 |
| azure | del_p90 | 12.05 | 4.741 | 3.915 | 3.427 | 2.698 |
| azure | inj3x30 | 14.36 | 4.419 | 3.713 | 3.308 | 2.698 |
| azure | empty | 20.78 | 2.514 | 2.514 | 2.514 | 2.698 |
| azure | exact | 0 | 4.149 | 3.552 | 3.164 | 2.698 |
| burstgpt | prev | 16.24 | 5.44 | 4.174 | 3.489 | 2.634 |
| burstgpt | phase15 | 15.64 | 5.262 | 4.072 | 3.41 | 2.634 |
| burstgpt | phase30 | 14.9 | 5.158 | 3.986 | 3.354 | 2.634 |
| burstgpt | phase60 | 14.85 | 5.211 | 4.006 | 3.369 | 2.634 |
| burstgpt | phase120 | 16.43 | 5.686 | 4.277 | 3.539 | 2.634 |
| burstgpt | amp0.5 | 15.19 | 5.496 | 4.208 | 3.51 | 2.634 |
| burstgpt | amp0.75 | 15.68 | 5.496 | 4.208 | 3.511 | 2.634 |
| burstgpt | amp1.25 | 16.8 | 5.446 | 4.191 | 3.503 | 2.634 |
| burstgpt | amp1.5 | 17.36 | 5.445 | 4.178 | 3.498 | 2.634 |
| burstgpt | del_p90 | 14.8 | 5.476 | 4.186 | 3.498 | 2.634 |
| burstgpt | inj3x30 | 17.04 | 5.201 | 4.035 | 3.407 | 2.634 |
| burstgpt | empty | 14.53 | 2.476 | 2.476 | 2.476 | 2.634 |
| burstgpt | exact | 0 | 2.444 | 2.416 | 2.399 | 2.634 |

## E4-2: P-hat's MILP over OPT_eager on the ratio day (bracket of §2.5; lo tested against 1 + x)

| panel | c | pred | point | lo | hi | 1 + x | refuted | confirmed |
|---|---|---|---|---|---|---|---|---|
| azure | 1 | amp0.5 | 0.2877 | 0.2865 | 0.2902 | 2.472 | False | True |
| azure | 1 | amp0.75 | 0.4311 | 0.429 | 0.4348 | 2.221 | False | True |
| azure | 1 | amp1.25 | 0.7222 | 0.7201 | 0.7285 | 1.981 | False | True |
| azure | 1 | amp1.5 | 0.869 | 0.8677 | 0.8765 | 2.055 | False | True |
| azure | 1 | del_p90 | 0.4735 | 0.4658 | 0.4776 | 2.174 | False | True |
| azure | 1 | empty | 0 | 0 | 0 | 3.025 | False | True |
| azure | 1 | exact | 1 | 0.9915 | 1.009 | 1 | False | False |
| azure | 1 | inj3x30 | 0.8946 | 0.892 | 0.9023 | 2.375 | False | True |
| azure | 1 | phase120 | 0.5767 | 0.5739 | 0.5817 | 3.04 | False | True |
| azure | 1 | phase15 | 0.5763 | 0.5739 | 0.5813 | 2.009 | False | True |
| azure | 1 | phase30 | 0.5765 | 0.5743 | 0.5815 | 2.144 | False | True |
| azure | 1 | phase60 | 0.5761 | 0.5741 | 0.5811 | 2.473 | False | True |
| azure | 1 | prev | 0.5767 | 0.574 | 0.5816 | 2.044 | False | True |
| azure | 2 | amp0.5 | 0.2855 | 0.2849 | 0.287 | 2.483 | False | True |
| azure | 2 | amp0.75 | 0.4289 | 0.428 | 0.4312 | 2.23 | False | True |
| azure | 2 | amp1.25 | 0.7267 | 0.7251 | 0.7306 | 1.989 | False | True |
| azure | 2 | amp1.5 | 0.8807 | 0.8793 | 0.8855 | 2.064 | False | True |
| azure | 2 | del_p90 | 0.47 | 0.4646 | 0.4726 | 2.183 | False | True |
| azure | 2 | empty | 0 | 0 | 0 | 3.042 | False | True |
| azure | 2 | exact | 1 | 0.9946 | 1.005 | 1 | False | False |
| azure | 2 | inj3x30 | 0.9952 | 0.9939 | 1.001 | 2.435 | False | True |
| azure | 2 | phase120 | 0.577 | 0.5757 | 0.5801 | 3.057 | False | True |
| azure | 2 | phase15 | 0.5773 | 0.5755 | 0.5805 | 2.017 | False | True |
| azure | 2 | phase30 | 0.5769 | 0.5757 | 0.5801 | 2.153 | False | True |
| azure | 2 | phase60 | 0.5773 | 0.5756 | 0.5805 | 2.485 | False | True |
| azure | 2 | prev | 0.5772 | 0.5758 | 0.5803 | 2.052 | False | True |
| burstgpt | 1 | amp0.5 | 0.1196 | 0.1196 | 0.1196 | 2.757 | False | True |
| burstgpt | 1 | amp0.75 | 0.1782 | 0.1782 | 0.1783 | 2.814 | False | True |
| burstgpt | 1 | amp1.25 | 0.2968 | 0.2968 | 0.2969 | 2.943 | False | True |
| burstgpt | 1 | amp1.5 | 0.3568 | 0.3567 | 0.3568 | 3.008 | False | True |
| burstgpt | 1 | del_p90 | 0.1085 | 0.1058 | 0.1085 | 2.713 | False | True |
| burstgpt | 1 | empty | 0 | 0 | 0 | 2.681 | False | True |
| burstgpt | 1 | exact | 1 | 0.9998 | 1 | 1 | False | False |
| burstgpt | 1 | inj3x30 | 0.4458 | 0.4458 | 0.4459 | 3.141 | False | True |
| burstgpt | 1 | phase120 | 0.162 | 0.162 | 0.1621 | 2.901 | False | True |
| burstgpt | 1 | phase15 | 0.2149 | 0.2149 | 0.2149 | 2.81 | False | True |
| burstgpt | 1 | phase30 | 0.1675 | 0.1675 | 0.1675 | 2.724 | False | True |
| burstgpt | 1 | phase60 | 0.1662 | 0.1662 | 0.1662 | 2.717 | False | True |
| burstgpt | 1 | prev | 0.2371 | 0.2371 | 0.2371 | 2.878 | False | True |
| burstgpt | 2 | amp0.5 | 0.1199 | 0.1199 | 0.1199 | 2.783 | False | True |
| burstgpt | 2 | amp0.75 | 0.1786 | 0.1786 | 0.1786 | 2.841 | False | True |
| burstgpt | 2 | amp1.25 | 0.2977 | 0.2977 | 0.2978 | 2.972 | False | True |
| burstgpt | 2 | amp1.5 | 0.3588 | 0.3588 | 0.3588 | 3.038 | False | True |
| burstgpt | 2 | del_p90 | 0.1084 | 0.1065 | 0.1085 | 2.738 | False | True |
| burstgpt | 2 | empty | 0 | 0 | 0 | 2.706 | False | True |
| burstgpt | 2 | exact | 1 | 0.9999 | 1 | 1 | False | False |
| burstgpt | 2 | inj3x30 | 0.3216 | 0.3216 | 0.3216 | 2.833 | False | True |
| burstgpt | 2 | phase120 | 0.1624 | 0.1623 | 0.1624 | 2.929 | False | True |
| burstgpt | 2 | phase15 | 0.2158 | 0.2157 | 0.2158 | 2.837 | False | True |
| burstgpt | 2 | phase30 | 0.1677 | 0.1677 | 0.1677 | 2.749 | False | True |
| burstgpt | 2 | phase60 | 0.1664 | 0.1664 | 0.1664 | 2.743 | False | True |
| burstgpt | 2 | prev | 0.2374 | 0.2374 | 0.2374 | 2.906 | False | True |

## Week cost over A6 without predictions (E4-6; median over alignments x seeds)

| panel | mu | pred | A5 | A6-pred | pairs |
|---|---|---|---|---|---|
| azure | 1 | prev | 1.046 | 1.039 | 6 |
| azure | 1 | phase15 | 1.059 | 1.062 | 6 |
| azure | 1 | phase30 | 1.089 | 1.079 | 6 |
| azure | 1 | phase60 | 1.158 | 1.162 | 6 |
| azure | 1 | phase120 | 1.343 | 1.252 | 6 |
| azure | 1 | amp0.5 | 0.9909 | 1.021 | 6 |
| azure | 1 | amp0.75 | 1.003 | 1.001 | 6 |
| azure | 1 | amp1.25 | 1.114 | 1.075 | 6 |
| azure | 1 | amp1.5 | 1.206 | 1.148 | 6 |
| azure | 1 | del_p90 | 1.029 | 1.039 | 6 |
| azure | 1 | inj3x30 | 1.311 | 1.326 | 6 |
| azure | 1 | empty | 1.127 | 1.127 | 6 |
| azure | 1 | exact | 0.5877 | 0.7992 | 6 |
| azure | 0.2 | prev | 1.044 | 1.045 | 6 |
| azure | 0.5 | prev | 1.049 | 1.031 | 6 |
| azure | 2 | prev | 1.045 | 1.042 | 6 |
| burstgpt | 1 | prev | 1.285 | 1.22 | 6 |
| burstgpt | 1 | phase15 | 1.255 | 1.176 | 6 |
| burstgpt | 1 | phase30 | 1.239 | 1.188 | 6 |
| burstgpt | 1 | phase60 | 1.248 | 1.19 | 6 |
| burstgpt | 1 | phase120 | 1.286 | 1.233 | 6 |
| burstgpt | 1 | amp0.5 | 1.123 | 1.084 | 6 |
| burstgpt | 1 | amp0.75 | 1.193 | 1.122 | 6 |
| burstgpt | 1 | amp1.25 | 1.372 | 1.308 | 6 |
| burstgpt | 1 | amp1.5 | 1.468 | 1.379 | 6 |
| burstgpt | 1 | del_p90 | 1.226 | 1.166 | 6 |
| burstgpt | 1 | inj3x30 | 1.424 | 1.378 | 6 |
| burstgpt | 1 | empty | 1.051 | 1.051 | 6 |
| burstgpt | 1 | exact | 0.6308 | 0.7532 | 6 |
| burstgpt | 0.2 | prev | 1.279 | 1.221 | 6 |
| burstgpt | 0.5 | prev | 1.283 | 1.216 | 6 |
| burstgpt | 2 | prev | 1.291 | 1.212 | 6 |

## Combiner: real cost over min{C_FP, C_R} (E4-5; median, max)

| panel | pred | tag | runs | C_FP | C_R | median | max | > 5.83 |
|---|---|---|---|---|---|---|---|---|
| azure | prev | A5 | 6 | 1991 | 2635 | 1.22 | 1.22 | 0 |
| azure | prev | A6-pred | 6 | 1991 | 2635 | 1.17 | 1.297 | 0 |
| azure | prev | A5-day | 6 | 439.8 | 1007 | 1.672 | 1.673 | 0 |
| azure | phase15 | A5 | 6 | 1993 | 2635 | 1.233 | 1.238 | 0 |
| azure | phase15 | A6-pred | 6 | 1993 | 2635 | 1.187 | 1.333 | 0 |
| azure | phase15 | A5-day | 6 | 429 | 1007 | 1.709 | 1.735 | 0 |
| azure | phase30 | A5 | 6 | 2026 | 2635 | 1.247 | 1.25 | 0 |
| azure | phase30 | A6-pred | 6 | 2026 | 2635 | 1.196 | 1.347 | 0 |
| azure | phase30 | A5-day | 6 | 432.8 | 1007 | 1.769 | 1.781 | 0 |
| azure | phase60 | A5 | 6 | 2106 | 2635 | 1.276 | 1.279 | 0 |
| azure | phase60 | A6-pred | 6 | 2106 | 2635 | 1.225 | 1.35 | 0 |
| azure | phase60 | A5-day | 6 | 448.9 | 1007 | 1.841 | 1.843 | 0 |
| azure | phase120 | A5 | 6 | 2592 | 2635 | 1.203 | 1.203 | 0 |
| azure | phase120 | A6-pred | 6 | 2592 | 2635 | 1.083 | 1.193 | 0 |
| azure | phase120 | A5-day | 6 | 605.3 | 1007 | 1.6 | 1.603 | 0 |
| azure | amp0.5 | A5 | 6 | 1402 | 2635 | 1.64 | 1.645 | 0 |
| azure | amp0.5 | A6-pred | 6 | 1402 | 2635 | 1.666 | 1.788 | 0 |
| azure | amp0.5 | A5-day | 6 | 339.1 | 1007 | 2.547 | 2.564 | 0 |
| azure | amp0.75 | A5 | 6 | 1689 | 2635 | 1.378 | 1.383 | 0 |
| azure | amp0.75 | A6-pred | 6 | 1689 | 2635 | 1.35 | 1.464 | 0 |
| azure | amp0.75 | A5-day | 6 | 382.2 | 1007 | 2.077 | 2.102 | 0 |
| azure | amp1.25 | A5 | 6 | 2310 | 2635 | 1.119 | 1.121 | 0 |
| azure | amp1.25 | A6-pred | 6 | 2310 | 2635 | 1.034 | 1.198 | 0 |
| azure | amp1.25 | A5-day | 6 | 506.5 | 1007 | 1.404 | 1.415 | 0 |
| azure | amp1.5 | A5 | 6 | 2610 | 2635 | 1.072 | 1.079 | 0 |
| azure | amp1.5 | A6-pred | 6 | 2610 | 2635 | 0.9748 | 1.104 | 0 |
| azure | amp1.5 | A5-day | 6 | 565.9 | 1007 | 1.277 | 1.281 | 0 |
| azure | del_p90 | A5 | 6 | 1789 | 2635 | 1.335 | 1.335 | 0 |
| azure | del_p90 | A6-pred | 6 | 1789 | 2635 | 1.324 | 1.431 | 0 |
| azure | del_p90 | A5-day | 6 | 390.2 | 1007 | 1.978 | 1.991 | 0 |
| azure | inj3x30 | A5 | 6 | 2708 | 2635 | 1.157 | 1.179 | 0 |
| azure | inj3x30 | A6-pred | 6 | 2708 | 2635 | 1.15 | 1.3 | 0 |
| azure | inj3x30 | A5-day | 6 | 619.5 | 1007 | 1.507 | 1.613 | 0 |
| azure | empty | A5 | 6 | 2634 | 2635 | 0.9923 | 1.002 | 0 |
| azure | empty | A6-pred | 6 | 2634 | 2635 | 0.9923 | 1.002 | 0 |
| azure | empty | A5-day | 6 | 1015 | 1007 | 1.002 | 1.011 | 0 |
| azure | exact | A5 | 6 | 1282 | 2635 | 1.062 | 1.088 | 0 |
| azure | exact | A6-pred | 6 | 1282 | 2635 | 1.416 | 1.618 | 0 |
| azure | exact | A5-day | 6 | 484.2 | 1007 | 1.063 | 1.076 | 0 |
| burstgpt | prev | A5 | 6 | 2450 | 2527 | 1.206 | 1.206 | 0 |
| burstgpt | prev | A6-pred | 6 | 2450 | 2527 | 1.151 | 1.27 | 0 |
| burstgpt | prev | A5-day | 6 | 909.1 | 915.1 | 1.017 | 1.03 | 0 |
| burstgpt | phase15 | A5 | 6 | 2374 | 2527 | 1.215 | 1.225 | 0 |
| burstgpt | phase15 | A6-pred | 6 | 2374 | 2527 | 1.134 | 1.288 | 0 |
| burstgpt | phase15 | A5-day | 6 | 874.7 | 915.1 | 1.021 | 1.025 | 0 |
| burstgpt | phase30 | A5 | 6 | 2396 | 2527 | 1.189 | 1.192 | 0 |
| burstgpt | phase30 | A6-pred | 6 | 2396 | 2527 | 1.141 | 1.256 | 0 |
| burstgpt | phase30 | A5-day | 6 | 870.8 | 915.1 | 1.011 | 1.016 | 0 |
| burstgpt | phase60 | A5 | 6 | 2461 | 2527 | 1.166 | 1.168 | 0 |
| burstgpt | phase60 | A6-pred | 6 | 2461 | 2527 | 1.116 | 1.22 | 0 |
| burstgpt | phase60 | A5-day | 6 | 877.3 | 915.1 | 1.003 | 1.007 | 0 |
| burstgpt | phase120 | A5 | 6 | 2574 | 2527 | 1.172 | 1.191 | 0 |
| burstgpt | phase120 | A6-pred | 6 | 2574 | 2527 | 1.11 | 1.239 | 0 |
| burstgpt | phase120 | A5-day | 6 | 927.6 | 915.1 | 1.019 | 1.035 | 0 |
| burstgpt | amp0.5 | A5 | 6 | 1909 | 2527 | 1.352 | 1.365 | 0 |
| burstgpt | amp0.5 | A6-pred | 6 | 1909 | 2527 | 1.299 | 1.347 | 0 |
| burstgpt | amp0.5 | A5-day | 6 | 877.8 | 915.1 | 1.024 | 1.025 | 0 |
| burstgpt | amp0.75 | A5 | 6 | 2169 | 2527 | 1.264 | 1.271 | 0 |
| burstgpt | amp0.75 | A6-pred | 6 | 2169 | 2527 | 1.191 | 1.354 | 0 |
| burstgpt | amp0.75 | A5-day | 6 | 897.7 | 915.1 | 1.016 | 1.019 | 0 |
| burstgpt | amp1.25 | A5 | 6 | 2718 | 2527 | 1.251 | 1.271 | 0 |
| burstgpt | amp1.25 | A6-pred | 6 | 2718 | 2527 | 1.182 | 1.29 | 0 |
| burstgpt | amp1.25 | A5-day | 6 | 922.2 | 915.1 | 1.026 | 1.043 | 0 |
| burstgpt | amp1.5 | A5 | 6 | 3017 | 2527 | 1.338 | 1.364 | 0 |
| burstgpt | amp1.5 | A6-pred | 6 | 3017 | 2527 | 1.255 | 1.454 | 0 |
| burstgpt | amp1.5 | A5-day | 6 | 948.6 | 915.1 | 1.048 | 1.067 | 0 |
| burstgpt | del_p90 | A5 | 6 | 2295 | 2527 | 1.228 | 1.231 | 0 |
| burstgpt | del_p90 | A6-pred | 6 | 2295 | 2527 | 1.157 | 1.283 | 0 |
| burstgpt | del_p90 | A5-day | 6 | 874.9 | 915.1 | 1.022 | 1.023 | 0 |
| burstgpt | inj3x30 | A5 | 6 | 2824 | 2527 | 1.298 | 1.317 | 0 |
| burstgpt | inj3x30 | A6-pred | 6 | 2824 | 2527 | 1.253 | 1.563 | 0 |
| burstgpt | inj3x30 | A5-day | 6 | 915.7 | 915.1 | 1.055 | 1.103 | 0 |
| burstgpt | empty | A5 | 6 | 2438 | 2527 | 0.9916 | 0.9916 | 0 |
| burstgpt | empty | A6-pred | 6 | 2438 | 2527 | 0.9916 | 0.9916 | 0 |
| burstgpt | empty | A5-day | 6 | 886.8 | 915.1 | 0.9923 | 0.9923 | 0 |
| burstgpt | exact | A5 | 6 | 1341 | 2527 | 1.082 | 1.085 | 0 |
| burstgpt | exact | A6-pred | 6 | 1341 | 2527 | 1.28 | 1.532 | 0 |
| burstgpt | exact | A5-day | 6 | 469.9 | 915.1 | 1.277 | 1.292 | 0 |

## Checks (§6.9)

| check | status |
|---|---|
| E4-1 | pass |
| E4-2 | pass |
| E4-3 | pass |
| E4-4 | informative |
| E4-5 | informative |
| E4-6 | informative |

