"""Offline tests for ICRCSearcher."""
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import icrc_adapter as adapter  # noqa: E402


def meta(url="https://ihl-databases.icrc.org/en/jsonapi/index/test"):
    return {"source_url": url, "http_status": 200, "content_type": "application/vnd.api+json",
            "bytes": 100, "retrieved_at": "2026-11-09T00:00:00Z", "sha256": "0" * 64}


class FakeHttp:
    def __init__(self, data):
        self.data = data
        self.evidence = []

    def json(self, url, params=None, headers=None):
        return self.data, meta(url)


def args(**kwargs):
    base = dict(database="ihl", lang="en", limit=1, offset=0, no_term_fallback=True,
                cache=".cache", offline=False, cache_ttl=0, timeout=30)
    base.update(kwargs)
    return argparse.Namespace(**base)


class IcrcTests(unittest.TestCase):
    def test_search_parses_index_record(self):
        payload = {
            "meta": {"count": 3},
            "data": [{
                "id": "abc",
                "type": "node--treaty",
                "attributes": {
                    "title": "Geneva Convention I",
                    "field_path": "/en/ihl-treaties/gci-1949",
                    "body": "<p>Article text</p>",
                },
                "links": {"self": {"href": "http://ihl-databases.icrc.org/en/jsonapi/node/treaty/abc"}},
            }],
        }
        out = adapter.search("genocide", args(), FakeHttp(payload))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["counts"]["tspc_treaty_search"], 3)
        self.assertEqual(len(out["counts"]), 5)
        self.assertEqual(out["results"][0]["id"], "abc")
        self.assertIn("Article text", out["results"][0]["snippet"])

    def test_zero_hits_is_not_an_error(self):
        out = adapter.search("nothing", args(), FakeHttp({"meta": {"count": 0}, "data": []}))
        self.assertEqual(out["status"], "no-results-in-queried-index")


if __name__ == "__main__":
    unittest.main()
