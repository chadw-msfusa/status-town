# Status Town

A static GitHub Pages dashboard that aggregates vendor-published incident updates for:

- Salesforce
- GoFundMe Pro
- Asana
- Microsoft Azure

Incident updates are displayed newest first and link to their original vendor sources. Retrieval failures are shown as **unavailable** or **error** and are never interpreted as evidence that a service is healthy.

## Important scope notes

- The dashboard displays vendor-published information. It is not an independent service-health or operational assessment.
- Severity is mapped from vendor-provided impact labels and wording.
- One dumpster-fire icon represents low severity and five represent critical severity.
- A 🤔 icon means that severity was unspecified or could not be mapped.
- Microsoft data comes from the public Azure status feed. Microsoft 365 service health normally requires authenticated access and is not represented as public health data.
- GoFundMe Pro status domains may change following product rebranding. The collector tries the configured public GoFundMe Pro and legacy Classy Statuspage endpoints.
- Public feeds, APIs, and response formats can change without notice. If a feed cannot be retrieved or parsed, the source is marked unavailable rather than healthy.
- Always consult the linked vendor status page before making operational decisions.

## Publish on GitHub Pages

1. Create a GitHub repository and copy the project files into its `main` branch.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.
4. Open **Actions → Refresh status data and deploy Pages**.
5. Select **Run workflow** for the initial retrieval and deployment.
6. After the workflow completes, open the GitHub Pages URL shown in the deployment result.

No credentials or API keys should be required when the configured public vendor endpoints are available.

## Automatic refresh schedule

The GitHub Actions workflow automatically retrieves status data and deploys the site four times per hour:

- `:07`
- `:22`
- `:37`
- `:52`

The schedule is defined in UTC:

```yaml
schedule:
  - cron: "7,22,37,52 * * * *"
```

GitHub may occasionally start scheduled workflows a few minutes late. Manual runs are only needed when:

- You want an immediate refresh.
- You are testing a code or configuration change.
- A scheduled workflow failed.
- GitHub disabled the schedule because the repository was inactive.

Do not add a second Pages deployment workflow, as multiple deployment workflows may conflict.

## Run locally

Python 3 is required to retrieve the data and run a local web server.

From the project directory, run:

```bash
python scripts/fetch_status.py
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

Do not open `index.html` directly from the filesystem. Browser security rules may prevent it from loading `data/status.json`.

Stop the local server with `Ctrl+C`.

## Project files

The principal project files are:

```text
.
├── .github/
│   └── workflows/
│       └── refresh-and-deploy.yml
├── data/
│   └── status.json
├── scripts/
│   └── fetch_status.py
├── TD.jpg
├── dumpster-fire.png
├── index.html
├── styles.css
├── app.js
└── README.md
```

### File purposes

- `index.html` contains the dashboard structure.
- `styles.css` contains the visual design and responsive layout.
- `app.js` loads and displays the generated status data.
- `TD.jpg` is the header image.
- `dumpster-fire.png` is used for mapped severity levels.
- `scripts/fetch_status.py` retrieves and normalizes public vendor status information.
- `data/status.json` contains the most recently generated dashboard data.
- `.github/workflows/refresh-and-deploy.yml` refreshes the data and deploys the site to GitHub Pages.

Keep `TD.jpg` and `dumpster-fire.png` in the repository root unless their paths are also updated in the HTML, CSS, or JavaScript.

## Optional endpoint overrides

Repository or workflow environment variables can replace the default public endpoints:

- `SALESFORCE_STATUS_API`
- `GOFUNDME_PRO_STATUS_API`
- `GOFUNDME_PRO_STATUS_PAGE`
- `ASANA_STATUS_API`
- `MICROSOFT_STATUS_FEED`

For example, add an `env` section to the retrieval step if a vendor changes its official public endpoint:

```yaml
- name: Retrieve public status data
  env:
    GOFUNDME_PRO_STATUS_API: https://example.org/api/v2/incidents.json
  run: python scripts/fetch_status.py
```

Only use official public endpoints. Do not put credentials, personal data, patient information, or private operational information in the repository or workflow.

## Data behavior

The generated `data/status.json` contains:

- `generated_at`: the workflow retrieval time
- `sources`: the retrieval state and diagnostic message for each source
- `incidents`: normalized vendor incident updates

The browser displays incidents newest first according to their publication timestamps.

A successfully retrieved feed with no incidents is treated differently from a failed feed:

- **available with zero updates:** The feed was successfully retrieved but returned no incident updates.
- **unavailable:** The source could not be retrieved, so its health is unknown from this dashboard.
- **error:** Retrieval or parsing failed, so the source’s health is unknown from this dashboard.
- **pending:** No retrieval result has been generated yet.

An unavailable, error, or pending source must never be presented as healthy.

## Severity display

Severity is a dashboard mapping, not an independent assessment:

- One dumpster fire: low
- Two dumpster fires: moderate
- Three dumpster fires: significant
- Four dumpster fires: high
- Five dumpster fires: critical
- 🤔: unspecified or unknown

The original vendor status and wording remain visible in each incident update where supplied.

## Troubleshooting

### The dashboard still shows an older version

1. Confirm the latest workflow completed successfully in the repository’s **Actions** tab.
2. Confirm the deployment step used the latest commit from `main`.
3. Perform a hard refresh:
   - Windows or Linux: `Ctrl+Shift+R` or `Ctrl+F5`
   - macOS Chrome or Firefox: `Cmd+Shift+R`
4. If necessary, clear the site data for the GitHub Pages domain and reload it.

### No `github-pages` artifact was found

Confirm the workflow contains these steps in this order:

```yaml
- name: Configure GitHub Pages
  uses: actions/configure-pages@v5

- name: Upload static site
  uses: actions/upload-pages-artifact@v3
  with:
    path: "."

- name: Deploy to GitHub Pages
  id: deployment
  uses: actions/deploy-pages@v4
```

Start a new workflow run after committing changes. Do not retry only the failed deployment step from an older run.

### A source is marked unavailable

Open the workflow run and inspect the **Retrieve public status data** log. Possible causes include:

- The vendor endpoint is temporarily unavailable.
- The endpoint URL has changed.
- The vendor changed its response format.
- GitHub Actions experienced a temporary network failure.
- The parser no longer recognizes the response.

Do not manually change the source to healthy. Correct the endpoint or parser and run the workflow again.

## Disclaimer

This dashboard is an informational display of public vendor status updates. It may be delayed, incomplete, or affected by changes to third-party feeds. Consult the original vendor sources for authoritative and current information.
