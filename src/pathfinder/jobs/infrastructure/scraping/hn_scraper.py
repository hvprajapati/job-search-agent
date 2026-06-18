"""Hacker News Who's Hiring scraper."""
import re
import httpx
from datetime import datetime, timezone, timedelta
from pathfinder.jobs.domain.value_objects import RawJobEntry, SourceType


class HackerNewsScraper:
    source_name = "hackernews"
    HN_API = "https://hacker-news.firebaseio.com/v0"
    SEARCH_API = "https://hn.algolia.com/api/v1/search"

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
        client = await self._get_client()
        try:
            # Find latest Who's Hiring thread
            cutoff = int((datetime.now(timezone.utc) - timedelta(days=45)).timestamp())
            sr = await client.get(self.SEARCH_API, params={
                "query": "Who is hiring", "tags": "story",
                "numericFilters": f"created_at_i>{cutoff}", "hitsPerPage": 5,
            })
            sr.raise_for_status()
            hits = sr.json().get("hits", [])
            thread_id = None
            for h in hits:
                t = h.get("title", "")
                if "who is hiring" in t.lower() and "month" in t.lower():
                    thread_id = h.get("objectID")
                    break
            if not thread_id:
                return jobs

            # Fetch thread comments
            tr = await client.get(f"{self.HN_API}/item/{thread_id}.json")
            tr.raise_for_status()
            kids = tr.json().get("kids", [])[:50]

            for kid in kids:
                try:
                    cr = await client.get(f"{self.HN_API}/item/{kid}.json")
                    if cr.status_code != 200:
                        continue
                    comment = cr.json()
                    text = re.sub(r"<[^>]+>", "", comment.get("text", ""))
                    if len(text) < 20:
                        continue
                    parsed = self._parse(text)
                    if parsed:
                        jobs.append(RawJobEntry(
                            source_name=self.source_name, source_type=SourceType.COMMUNITY,
                            raw_title=parsed.get("title", ""), raw_company=parsed.get("company", ""),
                            raw_location=parsed.get("location", ""), raw_description=text,
                            source_url=f"https://news.ycombinator.com/item?id={kid}",
                            source_id=str(kid), raw_metadata=parsed,
                        ))
                except Exception:
                    continue
        except Exception:
            pass
        return jobs

    def _parse(self, text: str) -> dict | None:
        first = text.strip().split("\n")[0].strip()
        if len(first) < 10:
            return None
        if "|" in first:
            parts = [p.strip() for p in first.split("|")]
            return {"company": parts[0] if len(parts) > 0 else "",
                    "title": parts[1] if len(parts) > 1 else "",
                    "location": parts[2] if len(parts) > 2 else ""}
        m = re.match(r"(.+?)\s+(?:is\s+hiring|hiring)\s+(.+?)(?:\s+\((.+?)\))?", first, re.IGNORECASE)
        if m:
            return {"company": m.group(1).strip(), "title": m.group(2).strip(),
                    "location": m.group(3) or ""}
        return {"company": first[:100], "title": "", "location": ""}

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
