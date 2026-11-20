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
