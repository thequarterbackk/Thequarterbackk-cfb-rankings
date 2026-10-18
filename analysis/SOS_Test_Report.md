# Strength-of-schedule experiment — October 18, 2026

Recommendation: retain the current 60% game-time / 40% later-validation blend and 0.75 quality coefficient. No tested alternative demonstrated a convincing improvement on the latest-week check. This is preliminary evidence, not proof that the current settings are optimal.

## Input and verification

510 completed current-season games through week 7: 388 FBS–FBS and 122 FBS–FCS games. The baseline reproduces the published records, points scored, points allowed, final ratings and ranks without mismatches. The locally rerun comparison also reproduces all 138 published ranks. The snapshot was last updated October 18, 2026 at 07:19:20 Eastern.

Every candidate uses the same full input. FCS opponents retain the production model's treatment: their strength is inferred from direct games against FBS teams; FCS–FCS games are excluded. There is no conference, division, poll, recruiting or market adjustment.

## Procedure

Recompute candidate rankings before each evaluation week using only games from earlier weeks. Evaluate whether the higher résumé rating selects the winner of each FBS–FBS matchup. All FBS–FCS results enter training and opponent valuation; the reported winner-accuracy denominators are FBS–FBS matchups only. This isolates the competitiveness of FBS rankings rather than letting predictable FBS–FCS results inflate accuracy.

Weeks 4–6 are the development comparison (172 games). Week 7 is the latest-week check (59 FBS–FBS games). Parameters were specified before retrieving complete FCS input, but the latest week's FBS-only preliminary results had already been inspected. Treat this as an exploratory chronological check, not a pristine prospective holdout. Each candidate recursively uses its own earlier ratings to establish game-time opponent values. Scoring, win credit and all other production ranking rules remain unchanged.

## Game-time / later-validation split

| Split | Weeks 4–6 correct | Accuracy | Week 7 correct | Accuracy |
|---|---:|---:|---:|---:|
| 0/100 | 113/172 | 65.7% | 34/59 | 57.6% |
| 25/75 | 114/172 | 66.3% | 34/59 | 57.6% |
| 40/60 | 113/172 | 65.7% | 34/59 | 57.6% |
| 50/50 | 114/172 | 66.3% | 34/59 | 57.6% |
| 60/40 | 112/172 | 65.1% | 34/59 | 57.6% |
| 75/25 | 111/172 | 64.5% | 32/59 | 54.2% |
| 100/0 | 110/172 | 64.0% | 32/59 | 54.2% |

25/75 and 50/50 gained two correct picks on development games, then tied 60/40 on week 7. The development-selected 25/75 candidate made exactly the same correct/incorrect winner decisions as 60/40 in week 7. There is no holdout winner-accuracy evidence for a switch.

## Overall SOS weight sensitivity at the current 60/40 split

| Quality coefficient | Relative weight | Weeks 4–6 correct | Week 7 correct |
|---|---:|---:|---:|
| 0 | 0× | 110/172 | 34/59 |
| 0.375 | 0.5× | 114/172 | 34/59 |
| 0.75 | 1× | 112/172 | 34/59 |
| 1.125 | 1.5× | 113/172 | 32/59 |
| 1.5 | 2× | 109/172 | 32/59 |

Increasing SOS weight by 50% or 100% yielded 32/59 versus the baseline's 34/59 in week 7. Halving the weight tied the baseline on winner accuracy; this does not establish that less SOS weight is better. Do not increase or decrease production weighting based on these small differences.

## Limits and interpretation

This is a test of résumé ratings' ability to order future opponents, not a test of the separate production spread/picks engine. The 57.6% latest-week figure is not the published picks engine's accuracy. Predicting future games and assigning deserved credit for a past win are different objectives: these results cannot determine whether credit for facing a healthy quarterback is fair.

No player or injury data is used, so the experiment cannot directly detect or validate the Pitt quarterback example. The game-time anchor can preserve context indirectly but can also preserve an early misestimate. Early opponents with no prior results initially receive a neutral value.

Probability Brier scores are included in the machine-readable results as secondary diagnostics. Logistic scales were chosen only from earlier predictions, with a fixed scale before sufficient history; these are experimental probabilities, not calibrated production predictions. The latest-week accuracy differences are small, and no superiority claim is justified. More genuinely unseen weeks are needed before adopting a change.

Only the separate analysis branch was changed. The live rankings and prediction model were not modified.
