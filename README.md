# Thequarterbackk CFB Rankings

GitHub Pages dashboard with hourly final-score refreshes via CFBD + GitHub Actions.
The API key stays in the repository secret `CFBD_API_KEY`.

## Ranking model v8

Only current-season completed scores and home/neutral status enter the model.
No polls, preseason seeds, prior seasons, conference bonuses, budgets, recruiting or market lines.
Conference metadata groups charts only.

Final Rating = 1000 × Colley résumé + 10 × robust scoring power − frozen game-time loss penalties.

- Résumé: solve the Colley equations, `(2+n_i)r_i − sum(r_opponent) = 1+(wins−losses)/2`. Equal 0.5 priors; opponent strength is solved through the game network. No raw cumulative win-point banking. Source: https://www.colleyrankings.com/matrate.pdf
- Scoring: regularized least squares with identical ridge 2 for all teams; transform margins with `35*tanh(margin/35)` to bound blowout influence. Jointly estimate home advantage, shrunk toward zero (100-game prior) and bounded to ±5. Source principles: https://masseyratings.com/theory/ls.htm
- Loss penalty: `50 + 2*max(0, opponent rank − team rank) + 2*losing margin`. Ranks are the model’s ratings entering the game week, frozen before all games that week. Tied ratings receive shared entering ranks. No gap term when prior evidence is missing. Non-FBS opponents use FBS count+1.
- The season is replayed under one version. Historical ranks may differ from older published versions. Loss Details exposes every frozen rank and deduction.
- Only FBS teams are public. Non-FBS opponents are hidden and measured through direct FBS matchups, consistent with the previous model; FCS-vs-FCS games do not enter the résumé model.
- `Base Rating` is now the Colley component. `Margin Adjustment` is the scoring component; `Dynamic Validation` is its compatibility alias. The old 60/40 and raw scoring formula are retired.
- Weights 1000/10 and penalty coefficients are declared policy choices, not statistically fitted probabilities or proof of a correct résumé order.

## Forecast validation

Forecasting is separate from résumé rankings. `modelBacktest` reports a retrospective walk-forward comparison against the exact v7 forecast engine. Each test week trains on earlier weeks only. Grid: ridge [1,2,4] × margin bound [21,35,49]. Settings for a test week are selected from earlier validation weeks only, with a 30-game selection minimum.

Promote a candidate only after ≥100 held-out FBS games, ≥1% relative reduction in margin MAE, and a positive lower bound on the approximate paired 95% improvement interval. The interval is a simple paired-error approximation, not a season-clustered uncertainty estimate. Otherwise retain v7 forecasts. This one-season test does not establish national superiority. Rank-blend and loss-policy weights are not tuned using JMU’s position.

True pregame predictions remain frozen in `model_predictions.json`; retrospective backtests are labeled separately. Forecast-engine labels prevent mixing residuals from different engines when estimating uncertainty. Market data is display/evaluation only and never a ranking input.

## Visuals

- Conference Strength: Explore chart or Image (all conferences); open full SVG image or download a 2× PNG. Logos are inlined; unavailable logos use initials. Bars are exact arithmetic means of published Final Ratings.
- Heatmap Image: corrected column alignment, ranked order, signed margins, teal/orange intensity, team/opponent focus, conference filtering, mouse/pinch zoom/pan, cell inspection and PNG export. A conference-only filter shows within-conference games; team focus includes that team’s FBS opponents.
- Results table and all-team ladder table provide accessible exact values.
- Ownership transfers use actual final FBS results, independent of model rank.

## Verification and updates

Run `python -m unittest -v test_rankings.py test_model_core.py`.
GitHub Actions runs the same checks before updating. Pushes to `update_rankings.py`, `model_core.py`, tests, or the workflow trigger a rebuild. Scheduled refresh: minute 17 of every hour.
All 138 public rows, score accounting, penalty audits, name/label invariance, frozen history, margin saturation and no-lookahead selection are checked. No national-best claim is made.
