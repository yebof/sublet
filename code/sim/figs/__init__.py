"""Figure scripts of the Sublet manuscript (design/figure_plan.md §1 and §5).

`figs.style` holds the figure style of §5: sizes, margins, fonts, the policy registry, line grammar and the
export checks. The figure scripts `fig<N>_<exp>.py` import it and read only result files in
code/analysis/out/, code/theory_checks/*/out/ or code/sim/out/, through `figs.inputs`; `figs.common` holds what
they share (the command line with --from-extract, the output folders, summary access, the E1 and E10 series and
layout helpers). Importing this package has no side effect; importing `figs.style` applies the style's rcParams.
"""
