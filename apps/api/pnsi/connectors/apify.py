"""Minimal Apify API client with a spending guard.

API reference: https://docs.apify.com/api/v2 (OpenAPI checked 2026-10-13).
Runs are started with `maxTotalChargeUsd`, so Apify itself refuses to charge
more than the cap we pass; the cap comes from the remaining monthly budget.
"""

from __future__ import annotations

import contextlib
import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx2

from pnsi.connectors.base import BudgetExhausted, ConnectorError, NotConfigured
from pnsi.log import get_logger

API_BASE = "https://api.apify.com"
TERMINAL = {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}
# Below this, a run could not even pay its start event.
MIN_RUN_BUDGET_USD = 0.02

log = get_logger(__name__)


def run_cost_usd(run: dict[str, Any]) -> float:
    """What a finished run cost, as far as the run object says.

    For pay-per-event actors, `usageTotalUsd` is often still 0 when the run turns
    SUCCEEDED (seen on 2026-10-22: 0.0 reported, 0.041 billed a minute later), so
    the charged events times their price are used when they say more. Callers add
    their own floor from the number of items received.
    """
    reported = float(run.get("usageTotalUsd") or 0)
    events = (run.get("pricingInfo") or {}).get("pricingPerEvent", {}).get("actorChargeEvents")
    from_events = 0.0
    for name, count in (run.get("chargedEventCounts") or {}).items():
        price = ((events or {}).get(name) or {}).get("eventPriceUsd")
        if isinstance(price, int | float) and isinstance(count, int | float):
            from_events += price * count
    return round(max(reported, from_events), 6)


@dataclass
class ActorResult:
    run_id: str
    status: str
    items: list[dict[str, Any]] = field(default_factory=list)
    cost_usd: float = 0.0


@dataclass
class Budget:
    """Spending allowed for this collection, from the monthly cap minus usage."""

    remaining_usd: float
    spent_usd: float = 0.0

    def cap(self, wanted_usd: float) -> float:
        available = self.remaining_usd - self.spent_usd
        if available < MIN_RUN_BUDGET_USD:
            raise BudgetExhausted(
                "Budget Apify du mois épuisé : collecte arrêtée avant tout dépassement."
            )
        return round(min(wanted_usd, available), 4)

    def charge(self, cost_usd: float) -> None:
        self.spent_usd += cost_usd


class ApifyClient:
    def __init__(
        self,
        token: str | None,
        *,
        transport: httpx2.BaseTransport | None = None,
        max_wait_secs: int = 600,
        sleep=time.sleep,
    ) -> None:
        if not token:
            raise NotConfigured("Apify non configuré : APIFY_TOKEN absent dans .env.")
        self._http = httpx2.Client(
            base_url=API_BASE,
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx2.Timeout(90.0, connect=15.0),
            transport=transport,
        )
        self._max_wait = max_wait_secs
        self._sleep = sleep

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """One call with backoff on 429 and 5xx. Errors never include the token."""
        for attempt in range(4):
            try:
                res = self._http.request(method, path, **kwargs)
            except httpx2.HTTPError as exc:
                if attempt == 3:
                    raise ConnectorError(f"Apify injoignable ({type(exc).__name__}).") from None
                self._sleep(2**attempt + random.random())  # noqa: S311
                continue
            if res.status_code == 429 or res.status_code >= 500:
                if attempt == 3:
                    raise ConnectorError(f"Apify indisponible (HTTP {res.status_code}).")
                retry_after = res.headers.get("retry-after")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                self._sleep(delay + random.random())  # noqa: S311
                continue
            if res.status_code == 401:
                raise NotConfigured("Jeton Apify refusé : vérifiez APIFY_TOKEN.")
            if res.status_code == 402:
                raise BudgetExhausted(
                    "Apify refuse la course : crédit ou limite du compte atteint."
                )
            if res.status_code >= 400:
                message = ""
                with contextlib.suppress(ValueError, AttributeError):
                    message = str(res.json().get("error", {}).get("message", ""))[:200]
                raise ConnectorError(f"Apify a répondu HTTP {res.status_code}. {message}".strip())
            return res.json()
        raise ConnectorError("Apify : nombre d'essais dépassé.")

    def budget(self, our_cap_usd: float) -> Budget:
        """Remaining spend this month: the lower of our cap and the account limit."""
        data = self._request("GET", "/v2/users/me/limits")["data"]
        used = float(data["current"].get("monthlyUsageUsd") or 0)
        account_max = data["limits"].get("maxMonthlyUsageUsd")
        ceiling = min(our_cap_usd, float(account_max)) if account_max else our_cap_usd
        return Budget(remaining_usd=max(0.0, ceiling - used))

    def run_actor(
        self,
        actor_id: str,
        run_input: dict[str, Any],
        *,
        max_charge_usd: float,
        timeout_secs: int = 300,
        max_items: int = 1000,
    ) -> ActorResult:
        run = self._request(
            "POST",
            f"/v2/actors/{actor_id}/runs",
            params={
                "maxTotalChargeUsd": max_charge_usd,
                "timeout": timeout_secs,
                "waitForFinish": 60,
            },
            json=run_input,
        )["data"]
        run_id = run["id"]
        deadline = time.monotonic() + self._max_wait
        while run["status"] not in TERMINAL:
            if time.monotonic() > deadline:
                self._request("POST", f"/v2/actor-runs/{run_id}/abort")
                raise ConnectorError(f"Course Apify trop longue, interrompue ({actor_id}).")
            run = self._request("GET", f"/v2/actor-runs/{run_id}", params={"waitForFinish": 60})[
                "data"
            ]

        status = run["status"]
        cost = run_cost_usd(run)
        log.info("apify_run_finished", actor=actor_id, status=status, cost_usd=cost)
        if status == "FAILED":
            raise ConnectorError(f"La course Apify a échoué ({actor_id}).")
        # SUCCEEDED, or TIMED-OUT / ABORTED with what was collected so far.
        items = self._request(
            "GET",
            f"/v2/datasets/{run['defaultDatasetId']}/items",
            params={"clean": "true", "format": "json", "limit": max_items},
        )
        return ActorResult(run_id=run_id, status=status, items=list(items), cost_usd=cost)
