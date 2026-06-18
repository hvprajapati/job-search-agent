"""Y Combinator Work at a Startup scraper."""
import httpx
from pathfinder.jobs.domain.value_objects import RawJobEntry, SourceType


class YCombinatorScraper:
    source_name = "ycombinator"
    API_URL = "https://www.workatastartup.com/api/jobs"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0, headers={
                "User-Agent": "Pathfinder/0.1 (Job Discovery Agent)"
            })
        return self._client

    async def sweep(self) -> list[RawJobEntry]:
        jobs: list[RawJobEntry] = []
        page = 1
        client = await self._get_client()
        while page <= 10:
            try:
                resp = await client.get(self.API_URL, params={"page": page, "per_page": 100})
                resp.raise_for_status()
                data = resp.json()
                batch = data.get("jobs", []) if isinstance(data, dict) else data
                if not batch:
                    break
                for j in batch:
                    locs = j.get("locations", [])
                    location = ", ".join(loc.get("name", "") for loc in locs) if locs else j.get("location", "")
                    jobs.append(RawJobEntry(
                        source_name=self.source_name, source_type=SourceType.JOB_BOARD,
                        raw_title=j.get("title", ""), raw_company=j.get("company_name", ""),
                        raw_location=location, raw_description=j.get("description", ""),
                        source_url=j.get("url", ""),
                        application_url=j.get("apply_url", "") or j.get("url", ""),
                        source_id=str(j.get("id", "")),
                        raw_metadata={"remote": j.get("remote", False), "skills": j.get("skills", [])},
                    ))
                page += 1
            except Exception:
                break
        return jobs

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
