"""A fake Apify API on httpx2.MockTransport, fed with the synthetic fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx2

from pnsi.connectors.apify import ApifyClient

FIXTURES = Path(__file__).parent / "fixtures" / "apify"


def load(name: str) -> list[dict[str, Any]]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeApify:
    def __init__(
        self,
        *,
        used_usd: float = 0.0,
        account_max_usd: float | None = 5.0,
        posts: list[dict[str, Any]] | None = None,
        comments: list[dict[str, Any]] | None = None,
        group_posts: list[dict[str, Any]] | None = None,
        post_run_cost: float = 0.016,
        comment_run_cost: float = 0.011,
        status_code: int = 200,
        # False reproduces Apify reporting 0 USD on a just-finished pay-per-event run.
        report_cost: bool = True,
        delete_ok: bool = True,
    ) -> None:
        self.used_usd = used_usd
        self.account_max_usd = account_max_usd
        self.posts = load("posts.json") if posts is None else posts
        self.comments = load("comments.json") if comments is None else comments
        self.group_posts = load("group_posts.json") if group_posts is None else group_posts
        self.report_cost = report_cost
        self.post_run_cost = post_run_cost
        self.comment_run_cost = comment_run_cost
        self.status_code = status_code
        self.runs: list[dict[str, Any]] = []
        self.deleted: list[str] = []
        self.delete_ok = delete_ok
        self._datasets: dict[str, list[dict[str, Any]]] = {}

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        if self.status_code != 200:
            return httpx2.Response(self.status_code, json={"error": {"message": "fake error"}})
        path = request.url.path
        if request.method == "DELETE":
            self.deleted.append(path)
            return httpx2.Response(204 if self.delete_ok else 500)
        if path == "/v2/users/me/limits":
            limits = {"maxMonthlyUsageUsd": self.account_max_usd} if self.account_max_usd else {}
            return httpx2.Response(
                200,
                json={
                    "data": {
                        "monthlyUsageCycle": {},
                        "limits": limits,
                        "current": {"monthlyUsageUsd": self.used_usd},
                    }
                },
            )
        if path.startswith("/v2/actors/") and path.endswith("/runs"):
            actor = path.split("/")[3]
            body = json.loads(request.content)
            n = len(self.runs)
            dataset = f"ds-{n}"
            if actor.endswith("posts-scraper"):
                self._datasets[dataset] = self.posts
                cost = self.post_run_cost
            elif actor.endswith("groups-scraper"):
                self._datasets[dataset] = self.group_posts
                cost = self.post_run_cost
            else:
                url = body["startUrls"][0]["url"]
                self._datasets[dataset] = [c for c in self.comments if c["facebookUrl"] == url]
                cost = self.comment_run_cost
            self.runs.append(
                {
                    "actor": actor,
                    "input": body,
                    "max_charge": float(request.url.params["maxTotalChargeUsd"]),
                }
            )
            return httpx2.Response(
                201,
                json={
                    "data": {
                        "id": f"run-{n}",
                        "status": "SUCCEEDED",
                        "defaultDatasetId": dataset,
                        "defaultKeyValueStoreId": f"kv-{n}",
                        "usageTotalUsd": cost if self.report_cost else 0.0,
                    }
                },
            )
        if path.startswith("/v2/datasets/"):
            return httpx2.Response(200, json=self._datasets[path.split("/")[3]])
        return httpx2.Response(404, json={"error": {"message": "unknown path"}})

    def client(self) -> ApifyClient:
        return ApifyClient(
            "fake-token-for-tests",
            transport=httpx2.MockTransport(self.handler),
            sleep=lambda _s: None,
        )
