#!/usr/bin/env python3
"""ICRC IHL databases adapter for ICRCSearcher."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from skillkit import HTTP, RetrievalError, clean, result, snippet, terms

PROG = "icrc_search.py"
DESCRIPTION = "Search the ICRC IHL databases and Customary IHL rules/practice."
CACHE_DEFAULT = ".icrc-cache"
FETCH_TIMEOUT_DEFAULT = 300

BASE = "https://ihl-databases.icrc.org"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/155.0.0.0 Safari/537.36"
)
INDEXES: dict[str, list[str]] = {
    "ihl": [
        "tspc_treaty_search",
        "tspc_article_search",
        "tspc_commentary_search",
        "tspc_participant_search",
        "np_search",
    ],
    "customary": ["cihl_rule_search", "cihl_practice_search"],
}


def _headers() -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Accept": "application/vnd.api+json, application/json;q=0.9, */*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def make_http(args: argparse.Namespace) -> HTTP:
    return HTTP(
        args.cache,
        offline=args.offline,
        ttl=args.cache_ttl,
        timeout=args.timeout,
        user_agent=UA,
        min_interval=0.4,
    )


def add_search_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--database",
        choices=("ihl", "customary", "all"),
        default="all",
        help="Database family (default: all)",
    )
    parser.add_argument("--lang", default="en", help="ICRC site language (default: en)")
    parser.add_argument("--limit", type=int, default=10, help="1..50 per index")
    parser.add_argument("--offset", type=int, default=0, help=">= 0")
    parser.add_argument(
        "--date-from",
        dest="date_from",
        help="National-practice date lower bound YYYY-MM-DD (np_search only)",
    )
    parser.add_argument(
        "--date-to",
        dest="date_to",
        help="National-practice date upper bound YYYY-MM-DD (np_search only)",
    )
    parser.add_argument(
        "--no-term-fallback",
        action="store_true",
        help="Do not retry a blocked multi-word phrase as a term-by-term intersection",
    )


def add_fetch_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text-out", help="Write extracted page text here")


def _record_url(record: dict[str, Any], language: str, meta: dict[str, Any]) -> str:
    attrs = record.get("attributes") or {}
    path = attrs.get("field_path")
    if path:
        return urljoin(f"{BASE}/{language}/", str(path).lstrip("/"))
    href = ((record.get("links") or {}).get("self") or {}).get("href")
    if href:
        return str(href).replace("http://", "https://", 1)
    return meta["source_url"]


def _title(record: dict[str, Any], index: str) -> str:
    attrs = record.get("attributes") or {}
    for key in (
        "title",
        "field_short_title",
        "field_treaty_content_title",
        "field_np_english_title",
        "field_cihl_title",
        "field_rule_title",
    ):
        value = attrs.get(key)
        if isinstance(value, dict):
            value = value.get("value") or value.get("processed")
        if value:
            return clean(value)
    return f"{index}: {record.get('id', '')}"


def _body(record: dict[str, Any]) -> str:
    attrs = record.get("attributes") or {}
    for key in ("body", "field_cihl_content", "field_rule_text", "field_practice_text"):
        value = attrs.get(key)
        if isinstance(value, dict):
            value = value.get("processed") or value.get("value")
        if value:
            return clean(value)
    return ""


def search(query: str, args: argparse.Namespace, http: HTTP) -> dict[str, Any]:
    if not query.strip():
        raise ValueError("A non-empty query is required")
    if not 1 <= args.limit <= 50:
        raise ValueError("limit must be 1..50")
    if args.offset < 0:
        raise ValueError("offset must be >= 0")

    families = ["ihl", "customary"] if args.database == "all" else [args.database]
    indexes = [index for family in families for index in INDEXES[family]]
    rows: list[dict[str, Any]] = []
    counts: dict[str, Any] = {}
    warnings: list[str] = []
    failures = 0
    for index in indexes:
        try:
            params: dict[str, Any] = {
                "page[limit]": args.limit,
                "page[offset]": args.offset,
                "filter[fulltext]": query,
            }
            date_from = getattr(args, "date_from", None)
            date_to = getattr(args, "date_to", None)
            if index == "np_search" and (date_from or date_to):
                params.update(
                    {
                        "filter[date_lower][operator]": ">=",
                        "filter[date_lower][path]": "date",
                        "filter[date_lower][value]": date_from or "1000-01-01",
                        "filter[date_upper][operator]": "<=",
                        "filter[date_upper][path]": "date",
                        "filter[date_upper][value]": date_to or "9999-12-31",
                    }
                )
            data, meta = http.json(
                f"{BASE}/{args.lang}/jsonapi/index/{index}",
                params,
                headers=_headers(),
            )
        except RetrievalError as exc:
            failures += 1
            warnings.append(f"{index}: {type(exc).__name__}: {exc}")
            continue
        records = data.get("data")
        if not isinstance(records, list):
            failures += 1
            warnings.append(f"{index}: response has no data array")
            continue
        counts[index] = (data.get("meta") or {}).get("count")
        for record in records:
            attrs = record.get("attributes") or {}
            rows.append(
                result(
                    _title(record, index),
                    _record_url(record, args.lang, meta),
                    "icrc-jsonapi:" + index,
                    _body(record),
                    id=record.get("id"),
                    index=index,
                    language=args.lang,
                    metadata=attrs,
                    access="api-record",
                    content_scope=(
                        "ICRC Drupal JSON:API record; the snippet is derived from the "
                        "record's own text fields, not a separate full-text fetch"
                    ),
                )
            )

    if failures == len(indexes) and not rows and len(terms(query)) > 1 and not args.no_term_fallback:
        warnings.append(
            "Every index rejected the original phrase; retrying as a bounded term-by-term intersection."
        )
        rows, counts, fallback_warnings = _term_fallback(http, query, args)
        warnings.extend(fallback_warnings)
        failures = 0

    if failures and not rows:
        status = "unavailable-or-incomplete"
    elif failures:
        status = "partial"
    elif rows:
        status = "ok"
    else:
        status = "no-results-in-queried-index"
    total = sum(value for value in counts.values() if isinstance(value, int)) if counts else None
    next_offset = None
    if total is not None and rows and args.offset + len(rows) < total:
        next_offset = args.offset + len(rows)
    return {
        "status": status,
        "query": query,
        "database": args.database,
        "language": args.lang,
        "date_range": {
            "from": getattr(args, "date_from", None) or None,
            "to": getattr(args, "date_to", None) or None,
            "applied_to": (
                ["np_search"]
                if (getattr(args, "date_from", None) or getattr(args, "date_to", None))
                else []
            ),
        },
        "total": total,
        "counts": counts,
        "results": rows,
        "pagination": {
            "offset": args.offset,
            "limit": args.limit,
            "next_offset": next_offset,
        },
        "warnings": warnings,
        "scope": (
            "ICRC IHL databases: treaties, article-by-article commentary, national practice, "
            "and Customary IHL rules/practice; total is the sum of per-index server counts when available"
        ),
        "evidence": http.evidence,
    }


def _term_fallback(
    http: HTTP, query: str, args: argparse.Namespace
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    """Bounded term-by-term intersection used when ICRC rejects a phrase."""
    families = ["ihl", "customary"] if args.database == "all" else [args.database]
    indexes = [index for family in families for index in INDEXES[family]]
    tokens = list(dict.fromkeys(terms(query)))[:4]
    rows: list[dict[str, Any]] = []
    counts: dict[str, Any] = {}
    warnings: list[str] = []
    for index in indexes:
        per_term: list[dict[str, dict[str, Any]]] = []
        labels: list[str] = []
        for token in tokens:
            try:
                data, meta = http.json(
                    f"{BASE}/{args.lang}/jsonapi/index/{index}",
                    {"page[limit]": 50, "page[offset]": 0, "filter[fulltext]": token},
                    headers=_headers(),
                )
            except RetrievalError as exc:
                warnings.append(f"{index}/{token}: {type(exc).__name__}: {exc}")
                per_term = []
                break
            records = data.get("data")
            if not isinstance(records, list):
                warnings.append(f"{index}/{token}: response has no data array")
                per_term = []
                break
            per_term.append({str(record.get("id")): record for record in records})
            labels.append(token)
        if not per_term:
            continue
        common = set.intersection(*[set(records) for records in per_term])
        counts[index] = len(common)
        for record_id in common:
            record = per_term[0][record_id]
            attrs = record.get("attributes") or {}
            rows.append(
                result(
                    _title(record, index),
                    _record_url(record, args.lang, meta),
                    "icrc-token-intersection:" + index,
                    _body(record),
                    id=record_id,
                    index=index,
                    language=args.lang,
                    metadata=attrs,
                    matched_terms=labels,
                    access=(
                        "bounded term-by-term intersection over the ICRC index; "
                        "not the site's own phrase search"
                    ),
                    content_scope=(
                        "ICRC Drupal JSON:API record matched term-by-term and intersected locally; "
                        "not a full-text judgment"
                    ),
                )
            )
    return rows[: args.limit], counts, warnings


def fetch(locator: str, args: argparse.Namespace, http: HTTP) -> dict[str, Any]:
    parsed = urlparse(locator)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "ihl-databases.icrc.org":
        raise ValueError("fetch expects an https://ihl-databases.icrc.org/ URL")
    body, meta = http.get(locator, headers=_headers())
    if body.startswith(b"%PDF"):
        from skillkit import pdf_pages

        pages = pdf_pages(body)
        text = "\n\n".join(f"@@PAGE {p['page']}@@\n{p['text']}" for p in pages)
        if args.text_out:
            Path(args.text_out).write_text(text, encoding="utf-8")
        return {
            "status": "ok",
            "url": meta["source_url"],
            "pages": len(pages),
            "needs_ocr": not any(p["text"].strip() for p in pages),
            "page_text": pages,
            "text_out": str(Path(args.text_out).resolve()) if args.text_out else None,
            "sha256": meta["sha256"],
            "retrieved_at": meta["retrieved_at"],
        }
    if "json" in meta["content_type"].lower():
        return {
            "status": "ok",
            "url": meta["source_url"],
            "data": json.loads(body),
            "sha256": meta["sha256"],
            "retrieved_at": meta["retrieved_at"],
        }
    soup = BeautifulSoup(body, "html.parser")
    container = (
        soup.select_one("main")
        or soup.select_one("article")
        or soup.select_one(".node__content")
        or soup.body
        or soup
    )
    for node in container.select("script, style, nav, header, footer, input, select, button, textarea, noscript"):
        node.decompose()
    text = container.get_text("\n", strip=True)
    if len(text) < 100:
        raise RetrievalError("Insufficient ICRC page text; page may be a shell or access page")
    links = []
    seen = set()
    for anchor in container.select("a[href]"):
        href = urljoin(meta["source_url"], anchor["href"])
        if href in seen:
            continue
        seen.add(href)
        links.append({"text": clean(anchor.get_text(" ", strip=True)), "url": href})
    if args.text_out:
        Path(args.text_out).write_text(text, encoding="utf-8")
    return {
        "status": "ok",
        "url": meta["source_url"],
        "text": text,
        "text_characters": len(text),
        "document_links": links,
        "content_scope": "ICRC public HTML page text; the linked document may be a treaty, commentary, rule, or practice record",
        "text_out": str(Path(args.text_out).resolve()) if args.text_out else None,
        "sha256": meta["sha256"],
        "retrieved_at": meta["retrieved_at"],
    }


def doctor(args: argparse.Namespace) -> dict[str, Any]:
    checks = [
        {"check": "python", "ok": True, "detail": "Python runtime available"},
        {"check": "requests", "ok": True, "detail": "requests importable"},
        {"check": "beautifulsoup4", "ok": True, "detail": "bs4 importable"},
    ]
    if args.no_probe:
        return {"ok": True, "status": "ok (probes skipped)", "checks": checks}
    http = make_http(args)
    probes = []
    for family, index in (("ihl", "tspc_treaty_search"), ("customary", "cihl_rule_search")):
        try:
            data, meta = http.json(
                f"{BASE}/en/jsonapi/index/{index}",
                {"page[limit]": 1, "filter[fulltext]": "genocide"},
                headers=_headers(),
            )
            probes.append(
                {
                    "check": "index:" + index,
                    "ok": isinstance(data.get("data"), list),
                    "http_status": meta["http_status"],
                    "bytes": meta["bytes"],
                    "count": (data.get("meta") or {}).get("count"),
                }
            )
        except Exception as exc:
            probes.append(
                {
                    "check": "index:" + index,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    checks.extend(probes)
    ok = any(item.get("ok") for item in probes)
    return {
        "ok": ok,
        "status": "ok" if ok else "error",
        "checks": checks,
        "catalog": {"databases": INDEXES},
    }
