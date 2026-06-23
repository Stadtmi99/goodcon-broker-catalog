#!/usr/bin/env python3
"""
Broker catalog generator (Phase 12).

Builds The Good Con broker catalog from public sources and emits a versioned
`brokers.json` matching the app's `BrokerCatalog` schema (GoodCon/Models).

Sources:
  - justvanish (MIT, https://github.com/AnalogJ/justvanish) — per-org YAML with
    opt-out emails + URLs. This is the email-actionable layer the app's SMTP
    flow needs. Attribution: see catalog/ATTRIBUTION.md.

Privacy: this script only assembles PUBLIC, non-personalized broker data. No
user PII is involved. The app fetches the published output anonymously.

Output schema (envelope):
  { "schemaVersion": 1, "generatedAt": "<ISO8601>", "brokers": [Entity, ...] }
Entity matches GoodCon/Models/Entity.swift.

Usage:
  python3 catalog/generate.py --justvanish /path/to/justvanish [--out catalog/brokers.json]
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
import uuid

import yaml

SCHEMA_VERSION = 1
# Stable namespace so uuid5(domain) ids never churn across regenerations.
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://thegoodcon.com/brokers")

# usage tokens that mean "this channel accepts a deletion/opt-out request"
ACTIONABLE_USAGES = {"delete.ccpa", "request.ccpa", "donotsell.ccpa",
                     "delete.gdpr", "request.gdpr"}

# organization_type -> (category, sourceType)
TYPE_MAP = {
    "databroker": ("Data Broker", "thirdParty"),
    "advertiser": ("Advertising Network", "tracking"),
    "tracker": ("Tracking Network", "tracking"),
    "platform": ("Platform", "firstParty"),
}


def _first_actionable_email(contact: dict) -> str | None:
    emails = (contact or {}).get("email") or []
    # Prefer an email explicitly tied to a delete/request action.
    for entry in emails:
        usages = set(entry.get("usage") or [])
        if usages & ACTIONABLE_USAGES and entry.get("address"):
            return entry["address"].strip()
    # Fall back to any listed email.
    for entry in emails:
        if entry.get("address"):
            return entry["address"].strip()
    return None


def _opt_out_url(org: dict) -> str | None:
    contact = org.get("contact") or {}
    forms = contact.get("form") or []
    for entry in forms:
        if isinstance(entry, dict) and entry.get("address"):
            return entry["address"].strip()
        if isinstance(entry, str) and entry:
            return entry.strip()
    website = org.get("website")
    return website.strip() if isinstance(website, str) and website else None


def _category_and_source(org: dict) -> tuple[str, str]:
    types = org.get("organization_type") or []
    for t in types:
        if t in TYPE_MAP:
            return TYPE_MAP[t]
    return ("Data Broker", "thirdParty")


def _region(org: dict) -> str:
    regs = set(org.get("regulation") or [])
    if "gdpr" in regs:
        return "eu"
    return "us"


def entity_from_org(domain: str, org: dict) -> dict | None:
    name = org.get("organization_name")
    if not name:
        return None
    email = _first_actionable_email(org.get("contact") or {})
    url = _opt_out_url(org)
    if not email and not url:
        return None  # nothing actionable — skip
    category, source_type = _category_and_source(org)
    return {
        "id": str(uuid.uuid5(NAMESPACE, domain)),
        "name": name.strip(),
        "category": category,
        "contactEmail": email,
        "contactURL": url,
        "isManualOnly": email is None,
        "sourceType": source_type,
        "confidence": "medium",
        "whyTheyHaveYourData": None,
        "optOutInstructions": None,
        "region": _region(org),
        "surveyTags": [],
    }


def build(justvanish_dir: pathlib.Path) -> list[dict]:
    org_dir = justvanish_dir / "data" / "organizations"
    if not org_dir.is_dir():
        sys.exit(f"justvanish organizations dir not found: {org_dir}")

    by_domain: dict[str, dict] = {}
    skipped = 0
    for path in sorted(org_dir.glob("*.yaml")):
        domain = path.stem  # filename is the canonical domain
        try:
            org = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError:
            skipped += 1
            continue
        entity = entity_from_org(domain, org)
        if entity is None:
            skipped += 1
            continue
        by_domain[domain] = entity  # dedupe by domain

    entities = sorted(by_domain.values(), key=lambda e: e["name"].lower())
    automated = sum(1 for e in entities if not e["isManualOnly"])
    print(f"built {len(entities)} brokers "
          f"({automated} automated, {len(entities) - automated} manual), "
          f"skipped {skipped}", file=sys.stderr)
    return entities


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--justvanish", required=True, type=pathlib.Path,
                    help="path to a cloned justvanish repo")
    ap.add_argument("--out", default="catalog/brokers.json", type=pathlib.Path)
    args = ap.parse_args()

    entities = build(args.justvanish)
    catalog = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc)
                        .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "brokers": entities,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {args.out} ({len(entities)} brokers)", file=sys.stderr)


if __name__ == "__main__":
    main()
