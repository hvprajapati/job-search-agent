"""Greenhouse job board scraper."""
import asyncio
import time
import httpx
from pathfinder.jobs.domain.value_objects import RawJobEntry, SourceType


GREENHOUSE_COMPANIES = [
    "stripe", "airbnb", "dropbox", "square", "shopify", "spotify",
    "cloudflare", "datadog", "figma", "notion", "linear", "vercel",
    "github", "gitlab", "reddit", "pinterest", "uber", "doordash",
    "coinbase", "plaid", "brex", "ramp", "mercury",
    "anthropic", "openai", "databricks", "snowflake", "confluent", "mongodb",
    "hashicorp", "twilio", "asana", "atlassian",
]
API_URL = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"


class GreenhouseScraper:
    source_name = "greenhouse"

    def __init__(self, companies: list[str] | None = None) -> None:
        self._companies = companies or GREENHOUSE_COMPANIES
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0, headers={
                "User-Agent": "Pathfinder/0.1 (Job Discovery Agent)"
            })
        return self._client

    async def sweep(self) -> list[RawJobEntry]:
        jobs: list[RawJobEntry] = []
        sem = asyncio.Semaphore(5)

        async def fetch(company: str) -> list[RawJobEntry]:
            async with sem:
                try:
                    client = await self._get_client()
                    resp = await client.get(API_URL.format(company=company))
                    resp.raise_for_status()
                    data = resp.json()
                    return [
                        RawJobEntry(
                            source_name=self.source_name, source_type=SourceType.CAREER_PAGE,
                            raw_title=j.get("title", ""),
                            raw_company=j.get("company_name", company),
                            raw_location=(j.get("location") or {}).get("name", ""),
                            raw_description=j.get("content", ""),
                            source_url=j.get("absolute_url", ""),
                            application_url=j.get("absolute_url", ""),
                            source_id=str(j.get("id", "")),
                        )
                        for j in data.get("jobs", [])
                    ]
                except Exception:
                    return []

        tasks = [fetch(c) for c in self._companies]
        results = await asyncio.gather(*tasks)
        for r in results:
            jobs.extend(r)
        return jobs

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
