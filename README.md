# Status Dashboard

A static GitHub Pages dashboard that aggregates vendor-published incident updates for:

- Salesforce
- GoFundMe Pro
- Asana
- Microsoft Azure

Incident updates are ordered newest first and link to the vendor source. Retrieval failures are
shown as **unavailable** and are never interpreted as healthy.

## Important scope notes

- The dashboard displays vendor-published information; it is not an independent service-health assessment.
- Pepper severity is a transparent keyword mapping of vendor impact wording, not an MSF or operational severity rating.
- Microsoft uses the public Azure status feed. Microsoft 365 service health normally requires authenticated access and is not represented as public health data.
- GoFundMe Pro status domains may change following product rebranding. The collector tries the public GoFundMe and legacy Classy Statuspage endpoints and clearly reports failure if neither works.
- Public endpoints can change without notice. A parser failure appears as unavailable.

## Publish on GitHub Pages

1. Create a GitHub repository and copy these files into its `main` branch.
2. In **Settings → Pages**, set **Source** to **GitHub Actions**.
3. Open **Actions** and manually run **Refresh status data and deploy Pages**, or wait for the schedule.
4. The workflow refreshes and deploys the static site every 15 minutes.

GitHub may delay scheduled workflows, especially in inactive repositories.

## Run locally

```bash
python scripts/fetch_status.py
python -m http.server 8000
```

Open `http://localhost:8000`.

Do not open `index.html` directly from the filesystem because browser security rules may block
loading `data/status.json`.

## Optional endpoint overrides

Repository or environment variables can replace defaults:

- `SALESFORCE_STATUS_API`
- `GOFUNDME_PRO_STATUS_API`
- `GOFUNDME_PRO_STATUS_PAGE`
- `ASANA_STATUS_API`
- `MICROSOFT_STATUS_FEED`

For example, add `env:` to the retrieval workflow step if a vendor changes its public feed:

```yaml
- name: Retrieve public status data
  env:
    GOFUNDME_PRO_STATUS_API: https://example.org/api/v2/incidents.json
  run: python scripts/fetch_status.py
```

Only use official public endpoints. Do not put credentials or private operational data into the repository.

## Data behavior

The generated `data/status.json` contains:

- `generated_at`: workflow retrieval time
- `sources`: per-source retrieval state and diagnostic message
- `incidents`: normalized update-level records, sorted newest first

A successful feed with zero incidents is distinct from a failed feed:

- **available + zero updates**: the feed was retrieved and returned no incident updates
- **unavailable/error**: health is unknown from this dashboard
- **pending**: no retrieval has run yet
