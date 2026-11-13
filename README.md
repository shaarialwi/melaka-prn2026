# Melaka Votes · PRN 2026

Responsive, buildless GitHub Pages election dashboard. Includes 28 real DUN boundary polygons and 79 candidates retrieved from BERNAMA on 14 November 2026 (Malaysia time). No vote totals were reported at initial preparation. Missing votes are null, not zero.

## Publish on GitHub

1. Create a **public** repository named `melaka-prn2026` in your GitHub account, with default branch `main`.
2. Extract this ZIP. Upload the **contents** of `melaka-prn2026`, not the ZIP or an enclosing directory. `index.html` must be at repository root.
3. Include the hidden `.github/workflows/results.yml` file. If your file picker hides it, create that exact path using GitHub **Add file → Create new file**, and paste the provided workflow. Without it, automatic source refresh will not run.
4. Open **Settings → Pages → Build and deployment → Source: GitHub Actions**.
5. Under **Settings → Actions → General → Workflow permissions**, allow read and write permissions for this repository, then Save. The workflow needs to commit refreshed public election data.
6. Open **Actions → Refresh results and deploy → Run workflow**. A successful run publishes the Pages URL shown in the deployment step and Settings → Pages.
7. After the election is final, disable this workflow from its Actions menu to stop recurring checks. Scheduled runs can be delayed by GitHub and public-repository schedules can be disabled after prolonged inactivity.

If using git locally, from this extracted folder:

```sh
git init -b main
git add .
git commit -m "Add Melaka 2026 election dashboard"
git remote add origin https://github.com/YOUR_USERNAME/melaka-prn2026.git
git push -u origin main
```

## What updates automatically

- `scripts/update_results.py` fetches BERNAMA's official and unofficial result pages separately.
- GitHub Actions attempts a source check every five minutes. This is polling, not instant push notification; scheduler and deployment latency apply.
- The open browser reads the published snapshot every 60 seconds, without resetting your selected DUN or filters.
- Both feeds must pass validation before a new snapshot is saved. Failures retain the previous snapshot and publish a warning. Candidate roster changes require manual review.
- Values can decrease when BERNAMA makes corrections. The dashboard uses whole source snapshots, never sums sequential updates or combines news counts.
- The source does not supply a count timestamp in the parsed fields. `checkedAt` is retrieval time; `changedAt` is the last detected snapshot change. Neither is claimed to be SPR's announcement time.
- Official counts are shown as official counts reported by BERNAMA. Seats are counted as **leading**, not declared won. A unique numerical lead can exist while other candidates remain unreported; it is provisional.

## News and Facebook limitation

This package does **not** monitor all news sites or Facebook. It has one functioning results adapter (BERNAMA), with links to SPR for verification. Arbitrary articles/posts cannot safely be interpreted as cumulative vote totals: they may contain old counts, projections, partial polling-station counts, duplicates or corrections.

To add a news outlet, create a source-specific adapter with election/seat/candidate identity matching, provenance, timestamp checks and conflict handling, then test it before enabling it. A Facebook Page integration requires suitable Meta API access and tokens held in server/GitHub secrets, never in browser JavaScript. No Meta credentials, permissions or feed are configured here. Unverified social claims must not overwrite this results snapshot.

## Local preview and verification

```sh
python -m http.server 8000
# Open http://localhost:8000
python -m unittest discover -s scripts -p 'test_*.py'
node --check app.js
python scripts/update_results.py
```

The site uses local SVG/GeoJSON, vanilla JavaScript and CSS. No map API key, chart CDN, npm install or paid service is needed. Opening `index.html` directly with `file://` will not load JSON in most browsers; use HTTP or GitHub Pages.

## Data and attribution

- Candidates and vote counts: https://election.bernama.com/prn/melaka/2026/keputusan/ (`?mode=official` and `?mode=unofficial`). Party labels follow the source's electoral party/coalition labels; they are not inferred component-party memberships.
- SPR election announcements: https://spr.gov.my/km-prudunmelaka16/
- Map: ElectionData.MY, 2018 Delimitation of Peninsular Malaysia (DUN), CC0. Melaka subset (28 features), https://electiondata.my/data-catalogue/peninsular-2018-dun/ . Data file: https://lake.electiondata.my/maps/delimitations/peninsular_2018_dun.geojson . Thevananthan & Chacko (2025), *The Malaysian Election Corpus (MECo): Electoral Maps and Cartograms from 1954 to 2025*.
- The map uses the published 2018 delimitation dataset. It is not a new legal certification of 2026 boundaries.
- `data/candidates.csv` contains the requested candidate list, DUN, party/coalition, and separate official/unofficial vote columns. Empty values mean unreported.

Independent project. Not affiliated with SPR, BERNAMA, or any political party. US election-night visual conventions are adapted to Melaka's multiparty, 28-seat assembly; no US electoral-college rules are used.
