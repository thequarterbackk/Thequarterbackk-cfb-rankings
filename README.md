# Dynamic CFB Rankings — live update package

This is the GitHub Pages site plus automatic final-score updates and two new visual tabs.

## Existing tabs kept
- Rankings
- Upcoming Picks
- Results Heatmap
- How It Works

## New tabs
- **Heatmap Image** — full matrix rendered as a large zoomable canvas. Pinch/drag on mobile.
- **CFP Ownership Map** — county-level U.S. ownership map. FBS teams start with geographic territory. Counties with multiple FBS teams begin split. When a current landholder loses, the winner takes every territory unit owned by the loser.

## Live update design
The CFBD API key stays in the GitHub repository secret `CFBD_API_KEY`. It is never sent to the browser.

The GitHub Action checks for completed FBS games on a schedule. Saturday checks run every 30 minutes; Thu/Fri/Sun/Mon run hourly; Tue/Wed get a maintenance run. The updater also performs a full season refresh at least every 12 hours so non-FBS follow-up games are captured for Dynamic Win Validation and ownership transfers.

When new finals are found it rebuilds:
1. Rankings
2. Dynamic opponent validation
3. Upcoming picks
4. Results heatmap
5. Heatmap image data
6. CFP Ownership Map game history
7. Last-updated stamps

## Model
Base Rating = (Wins × 100) + Points For − (Points Allowed × 1.5)

Effective Opponent Strength = 60% × strength when played + 40% × later validated strength

Win quality = +0.75 × effective opponent strength

Loss quality = −0.75 × (100 − effective opponent strength)

No margin cap.

## Install on the existing repo
Replace the root website files with the files in this package:
- `index.html`
- `styles.css`
- `app.js`
- `data.json`
- `update_rankings.py`
- `README.md`

Then create this one workflow file in GitHub:
`.github/workflows/update-rankings.yml`

The exact workflow file is included inside this ZIP under `.github/workflows/`.

After uploading, open **Actions → Update rankings and maps → Run workflow**. The first run creates `team_meta.json` and `automation_state.json`, pulls the latest completed games, recalculates everything, and commits the results. GitHub Pages will then republish automatically.

### Important
GitHub Pages is still static hosting. The automatic behavior comes from GitHub Actions rebuilding `data.json` after final scores. The rankings do not swing during a game; they update after a game is marked completed by CFBD.
