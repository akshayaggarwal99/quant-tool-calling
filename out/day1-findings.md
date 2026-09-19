# Day 1 findings: Qwen3-1.7B, BFCL simple_python, controlled k-quant ladder

All rungs built from one FP16 source. 400 questions per cell. Deterministic AST scoring, no judge.

## Reproducibility control (the thing that makes the rest interpretable)

Same weights, re-run:

| rung | runs | range | per-question flips |
|---|---|---|---|
| Q8_0 | 91.75, 91.50, 91.50 | 0.25 pp | 1 of 400 |
| Q4_K_M | 92.00, 91.50, 92.00 | 0.50 pp | 4 of 400 |

The instrument is effectively deterministic. Any ladder difference above ~0.5 pp is not run noise.

## The ladder

| rung | accuracy | vs Q8_0 | McNemar exact p |
|---|---|---|---|
| Q8_0 | 91.75% | baseline | |
| Q6_K | 93.50% | +1.75 pp | 0.167 |
| Q5_K_M | 90.75% | -1.00 pp | 0.455 |
| Q4_K_M | 92.00% | +0.25 pp | 1.000 |
| Q3_K_M | 87.00% | **-4.75 pp** | **0.0043** |

## What this says

Tool calling is flat from 8-bit through 4-bit, then falls off a cliff at 3-bit. Q4_K_M is
statistically indistinguishable from Q8_0 despite being 60% of the size. Q3_K_M loses 30 questions
and gains 11 against Q8_0, a net 4.75 pp, roughly ten times the within-rung noise.

The wobble between Q8_0, Q6_K and Q5_K_M is not significant under paired testing, so the earlier
"non-monotonic" reading does not survive the control. Only the Q3_K_M drop is real.

## Consequence for H1

H1 predicted schema compliance breaks at a higher bit-width than free-form accuracy. For this
model the tool-calling floor sits between Q4_K_M and Q3_K_M, which is where the published
free-form floor also sits. H1 is not supported so far, though it is not yet properly tested
because the free-form control arm has not been run on these same weights. That arm is now the
highest-priority next step, since H1 is the paper's central claim.

## Caveats

One model, one category, one hardware platform. simple_python is the easiest BFCL category.
Multi-turn, parallel and irrelevance categories are untested, and H5 predicts multi-turn amplifies
degradation.
