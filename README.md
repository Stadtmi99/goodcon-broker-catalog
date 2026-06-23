# The Good Con — Broker Catalog

Public, non-personalized catalog of data brokers (names, opt-out emails, opt-out
URLs) consumed by The Good Con app. **No user data is here** — this is broker
reference data only.

The app fetches `brokers.json` anonymously over HTTPS and refreshes ~weekly
(see the app's `RemoteBrokerCatalogService`). A GitHub Action regenerates this
file from public sources on a schedule.

## Files
- `generate.py` — builds `brokers.json` (schema = the app's `BrokerCatalog`).
- `brokers.json` — generated catalog (the published artifact).
- `requirements.txt` — Python deps (pyyaml).
- `.github/workflows/refresh.yml` — weekly regeneration + commit.
- `ATTRIBUTION.md` — source attribution (justvanish, MIT).

## One-time setup (publish)
This directory is meant to be the **root of a public repo** so the app can fetch
it without authentication.

1. Create a **public** GitHub repo named `goodcon-broker-catalog`.
2. Copy the *contents* of this `catalog/` directory into the repo root and push to `main`.
3. The published URL is then:
   `https://raw.githubusercontent.com/Stadtmi99/goodcon-broker-catalog/main/brokers.json`
   (already set as `RemoteBrokerCatalogService.defaultCatalogURL` in the app).
4. GitHub Actions runs `refresh.yml` weekly to keep `brokers.json` current.

## Regenerate locally
```sh
pip install -r requirements.txt
git clone --depth 1 https://github.com/AnalogJ/justvanish.git /tmp/justvanish
python3 generate.py --justvanish /tmp/justvanish --out brokers.json
```

## Planned source additions
California (CPPA) and Vermont data broker registries for breadth/legitimacy
(public records), deduped by domain alongside the justvanish opt-out emails.
