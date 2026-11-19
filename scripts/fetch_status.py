#!/usr/bin/env python3
"""Fetch public vendor status data and write static JSON.

Retrieval errors remain explicit. The script never converts a failed request into
a healthy status. All parsers are intentionally defensive because public status
page schemas can change.
"""

from __future__ import annotations

import email.utils
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "status.json"
USER_AGENT = "github-pages-public-status-dashboard/1.0"
TIMEOUT = 30


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_time(value: Any) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(str(value))
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError):
            return None


def get_bytes(url: str, accept: str = "*/*") -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def get_json(url: str) -> Any:
    return json.loads(get_bytes(url, "application/json").decode("utf-8"))


def severity(impact: Any, title: str = "", body: str = "") -> tuple[int, str]:
    """Map vendor wording to 1–5 peppers without asserting independent severity."""
    value = " ".join([str(impact or ""), title, body]).lower()
    if any(word in value for word in ("critical", "catastrophic", "widespread outage")):
        return 5, "critical"
    if any(word in value for word in ("major", "severe", "outage", "service disruption")):
        return 4, "major"
    if any(word in value for word in ("degraded", "partial", "elevated", "intermittent")):
        return 3, "moderate"
    if any(word in value for word in ("minor", "limited", "small subset")):
        return 2, "minor"
    return 1, "low/unspecified"


def source_record(
    source_id: str,
    name: str,
    page_url: str,
    retrieval_status: str,
    message: str,
    retrieved_from: str | None = None,
) -> dict[str, Any]:
    return {
        "id": source_id,
        "name": name,
        "status_page_url": page_url,
        "retrieval_status": retrieval_status,
        "message": message,
        "retrieved_from": retrieved_from,
    }


def statuspage_events(
    source_id: str,
    source_name: str,
    page_url: str,
    api_urls: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors = []
    payload = None
    used_url = None
    for api_url in api_urls:
        try:
            payload = get_json(api_url)
            used_url = api_url
            break
        except Exception as exc:  # Preserve all candidate failures for diagnostics.
            errors.append(f"{api_url}: {type(exc).__name__}: {exc}")

    if payload is None:
        return (
            source_record(
                source_id, source_name, page_url, "unavailable",
                "Public incident feed could not be retrieved. " + " | ".join(errors)
            ),
            [],
        )

    incidents = payload.get("incidents", []) if isinstance(payload, dict) else []
    events: list[dict[str, Any]] = []
    for incident in incidents:
        title = clean_text(incident.get("name") or incident.get("title") or "Untitled incident")
        impact = incident.get("impact")
        vendor_status = clean_text(incident.get("status") or "unknown")
        incident_url = incident.get("shortlink") or incident.get("url") or page_url
        updates = incident.get("incident_updates") or []
        if not updates:
            updates = [{
                "body": incident.get("body") or incident.get("message") or "",
                "created_at": incident.get("updated_at") or incident.get("created_at"),
                "status": vendor_status,
            }]
        for update in updates:
            body = clean_text(update.get("body") or update.get("message"))
            level, label = severity(impact, title, body)
            events.append({
                "source_id": source_id,
                "source_name": source_name,
                "incident_id": str(incident.get("id") or ""),
                "title": title,
                "body": body,
                "published_at": parse_time(
                    update.get("created_at") or update.get("updated_at")
                    or incident.get("updated_at") or incident.get("created_at")
                ),
                "vendor_status": clean_text(update.get("status") or vendor_status),
                "vendor_impact": clean_text(impact or ""),
                "severity": level,
                "severity_label": label,
                "source_url": incident_url,
            })

    return (
        source_record(
            source_id, source_name, page_url, "available",
            f"Public incident API retrieved successfully; {len(events)} update(s) returned.",
            used_url,
        ),
        events,
    )


def salesforce_events() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_id = "salesforce"
    source_name = "Salesforce"
    page_url = "https://status.salesforce.com/"
    api_url = os.getenv(
        "SALESFORCE_STATUS_API",
        "https://api.status.salesforce.com/v1/incidents",
    )
    try:
        payload = get_json(api_url)
    except Exception as exc:
        return (
            source_record(
                source_id, source_name, page_url, "unavailable",
                f"Public incident API could not be retrieved: {type(exc).__name__}: {exc}",
            ),
            [],
        )

    if isinstance(payload, list):
        incidents = payload
    elif isinstance(payload, dict):
        incidents = (
            payload.get("incidents") or payload.get("data")
            or payload.get("result") or []
        )
    else:
        incidents = []

    events: list[dict[str, Any]] = []
    for incident in incidents:
        title = clean_text(
            incident.get("title") or incident.get("name")
            or incident.get("subject") or incident.get("message")
            or "Salesforce incident"
        )
        impact = (
            incident.get("impact") or incident.get("severity")
            or incident.get("level") or ""
        )
        vendor_status = clean_text(
            incident.get("status") or incident.get("state") or "unknown"
        )
        incident_id = str(
            incident.get("id") or incident.get("incidentId")
            or incident.get("externalId") or ""
        )
        incident_url = (
            incident.get("url") or incident.get("link")
            or (f"{page_url}incidents/{incident_id}" if incident_id else page_url)
        )
        updates = (
            incident.get("updates") or incident.get("incident_updates")
            or incident.get("events") or incident.get("IncidentEvents") or []
        )
        if not updates:
            updates = [{
                "body": (
                    incident.get("additionalInformation")
                    or incident.get("description") or incident.get("message") or ""
                ),
                "created_at": (
                    incident.get("updatedAt") or incident.get("updated_at")
                    or incident.get("createdAt") or incident.get("created_at")
                ),
                "status": vendor_status,
            }]
        for update in updates:
            body = clean_text(
                update.get("body") or update.get("message")
                or update.get("additionalInformation") or update.get("description")
            )
            level, label = severity(impact, title, body)
            events.append({
                "source_id": source_id,
                "source_name": source_name,
                "incident_id": incident_id,
                "title": title,
                "body": body,
                "published_at": parse_time(
                    update.get("createdAt") or update.get("created_at")
                    or update.get("updatedAt") or update.get("updated_at")
                ),
                "vendor_status": clean_text(
                    update.get("status") or update.get("state") or vendor_status
                ),
                "vendor_impact": clean_text(impact),
                "severity": level,
                "severity_label": label,
                "source_url": incident_url,
            })

    return (
        source_record(
            source_id, source_name, page_url, "available",
            f"Public incident API retrieved successfully; {len(events)} update(s) returned.",
            api_url,
        ),
        events,
    )


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1].lower()


def child_text(element: ET.Element, names: set[str]) -> str:
    for child in list(element):
        if local_name(child.tag) in names:
            return "".join(child.itertext()).strip()
    return ""


def microsoft_events() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_id = "microsoft"
    source_name = "Microsoft Azure"
    page_url = "https://azure.status.microsoft/en-us/status"
    feed_url = os.getenv(
        "MICROSOFT_STATUS_FEED",
        "https://azure.status.microsoft/en-us/status/feed/",
    )
    try:
        root = ET.fromstring(get_bytes(feed_url, "application/rss+xml, application/atom+xml, text/xml"))
    except Exception as exc:
        return (
            source_record(
                source_id, source_name, page_url, "unavailable",
                "Azure public feed could not be retrieved. Microsoft 365 service health "
                f"generally requires authenticated access. Error: {type(exc).__name__}: {exc}",
            ),
            [],
        )

    entries = [
        element for element in root.iter()
        if local_name(element.tag) in {"item", "entry"}
    ]
    events: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        title = clean_text(child_text(entry, {"title"}) or "Microsoft Azure status update")
        body = clean_text(child_text(entry, {"description", "summary", "content"}))
        published = parse_time(child_text(entry, {"pubdate", "published", "updated"}))
        link = child_text(entry, {"link"})
        if not link:
            for child in list(entry):
                if local_name(child.tag) == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        level, label = severity("", title, body)
        events.append({
            "source_id": source_id,
            "source_name": source_name,
            "incident_id": child_text(entry, {"guid", "id"}) or f"feed-{index}",
            "title": title,
            "body": body,
            "published_at": published,
            "vendor_status": "feed update",
            "vendor_impact": "",
            "severity": level,
            "severity_label": label,
            "source_url": link or page_url,
        })

    return (
        source_record(
            source_id, source_name, page_url, "available",
            f"Azure public feed retrieved successfully; {len(events)} update(s) returned. "
            "This does not represent authenticated Microsoft 365 service health.",
            feed_url,
        ),
        events,
    )


def gofundme_events() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    configured = os.getenv("GOFUNDME_PRO_STATUS_API")
    candidates = [configured] if configured else [
        "https://status.gofundme.com/api/v2/incidents.json",
        "https://status.classy.org/api/v2/incidents.json",
    ]
    return statuspage_events(
        "gofundme-pro",
        "GoFundMe Pro",
        os.getenv("GOFUNDME_PRO_STATUS_PAGE", "https://status.gofundme.com/"),
        candidates,
    )


def main() -> int:
    collectors: list[Callable[[], tuple[dict[str, Any], list[dict[str, Any]]]]] = [
        salesforce_events,
        gofundme_events,
        lambda: statuspage_events(
            "asana",
            "Asana",
            "https://status.asana.com/",
            [os.getenv("ASANA_STATUS_API", "https://status.asana.com/api/v2/incidents.json")],
        ),
        microsoft_events,
    ]

    sources: list[dict[str, Any]] = []
    incidents: list[dict[str, Any]] = []
    for collector in collectors:
        try:
            source, events = collector()
        except Exception as exc:
            # A programming/parser failure is still represented as unavailable.
            name = getattr(collector, "__name__", "unknown source")
            source = source_record(
                name, name, "#", "error",
                f"Collector failed: {type(exc).__name__}: {exc}",
            )
            events = []
        sources.append(source)
        incidents.extend(events)

    incidents.sort(key=lambda item: item.get("published_at") or "", reverse=True)
    document = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "notice": (
            "Vendor-published information only. Unavailable retrieval is unknown, not healthy. "
            "Severity is mapped from vendor wording."
        ),
        "sources": sources,
        "incidents": incidents,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)

    unavailable = [source["name"] for source in sources if source["retrieval_status"] != "available"]
    print(f"Wrote {OUTPUT} with {len(incidents)} updates.")
    if unavailable:
        print("Unavailable sources: " + ", ".join(unavailable), file=sys.stderr)
    # Complete the publication even if one vendor is down: its unavailable card is essential data.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
