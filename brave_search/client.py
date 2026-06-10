import time
from typing import Any

import httpx
from opentelemetry.trace import StatusCode

from .config import BraveSearchConfig
from .models import (
    DiscussionResult,
    FaqResult,
    Infobox,
    LocationResult,
    NewsResult,
    SearchParams,
    SearchResponse,
    VideoResult,
    WebResult,
)
from .telemetry import logger, tracer


class BraveSearchClient:
    def __init__(self, config: BraveSearchConfig | None = None) -> None:
        cfg = config or BraveSearchConfig()
        self._http = httpx.AsyncClient(
            base_url=cfg.base_url,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": cfg.api_key,
            },
            timeout=cfg.timeout,
        )

    async def __aenter__(self) -> "BraveSearchClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.aclose()

    @staticmethod
    def _to_api_params(p: SearchParams) -> dict[str, Any]:
        params: dict[str, Any] = {"q": p.query, "count": p.count}
        if p.offset:
            params["offset"] = p.offset
        for field in ("country", "search_lang", "freshness"):
            if v := getattr(p, field):
                params[field] = v
        if p.safesearch != "moderate":
            params["safesearch"] = p.safesearch
        if p.extra_snippets:
            params["extra_snippets"] = True
        if p.result_filter:
            params["result_filter"] = ",".join(p.result_filter)
        return params

    @staticmethod
    def _parse(query: str, data: dict) -> SearchResponse:
        def section(key: str, model: type) -> list | None:
            results = data.get(key, {}).get("results")
            return [model.model_validate(r) for r in results] if results else None

        raw_infobox = data.get("infobox")
        return SearchResponse(
            query=query,
            web=section("web", WebResult) or [],
            news=section("news", NewsResult),
            discussions=section("discussions", DiscussionResult),
            faq=section("faq", FaqResult),
            infobox=Infobox.model_validate(raw_infobox) if raw_infobox else None,
            videos=section("videos", VideoResult),
            locations=section("locations", LocationResult),
        )

    async def search(self, params: SearchParams) -> SearchResponse:
        with tracer.start_as_current_span("brave_search.search") as span:
            span.set_attribute("search.query", params.query)
            span.set_attribute("search.count", params.count)
            t0 = time.perf_counter()
            try:
                r = await self._http.get(
                    "/web/search", params=self._to_api_params(params)
                )
                r.raise_for_status()
                response = self._parse(params.query, r.json())
                if params.result_filter:
                    span.set_attribute(
                        "search.result_filter", ",".join(params.result_filter)
                    )
                counts = {"web": len(response.web)}
                for key in ("news", "discussions", "faq", "videos", "locations"):
                    if sec := getattr(response, key):
                        counts[key] = len(sec)
                if response.infobox:
                    counts["infobox"] = 1
                for k, v in counts.items():
                    span.set_attribute(f"search.{k}_count", v)
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                logger.info(
                    "search.complete",
                    query=params.query,
                    elapsed_ms=elapsed_ms,
                    **counts,
                )
                return response
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                logger.error("search.failed", query=params.query, error=str(exc))
                raise
