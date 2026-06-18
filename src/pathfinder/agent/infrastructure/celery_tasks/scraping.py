"""Celery tasks for job discovery sweeps."""
import asyncio
import logging
from celery import Celery
from pathfinder.shared.config import get_settings
from pathfinder.shared.infrastructure.database import get_sessionmaker
from pathfinder.jobs.infrastructure.scraping.greenhouse_scraper import GreenhouseScraper
from pathfinder.jobs.infrastructure.scraping.ycombinator_scraper import YCombinatorScraper
from pathfinder.jobs.infrastructure.scraping.hn_scraper import HackerNewsScraper
from pathfinder.jobs.domain.services import JobNormalizer, JobDedupService, JobEnrichmentService
from pathfinder.jobs.infrastructure.persistence.job_repository import SqlJobRepository
from pathfinder.jobs.infrastructure.persistence.company_repository import SqlCompanyRepository

logger = logging.getLogger(__name__)
settings = get_settings()

app = Celery("pathfinder", broker=settings.redis_url)
app.conf.update(
    task_serializer="json", accept_content=["json"],
    timezone="UTC", enable_utc=True, task_acks_late=True,
    worker_prefetch_multiplier=1,
)

_scrapers = [GreenhouseScraper(), YCombinatorScraper(), HackerNewsScraper()]


async def _sweep_all_async() -> dict:
    maker = get_sessionmaker()
    total_new, total_updated = 0, 0
    results = {}

    for scraper in _scrapers:
        try:
            raw_jobs = await scraper.sweep()
            new_count, updated_count = 0, 0
            async with maker() as session:
                job_repo = SqlJobRepository(session)
                company_repo = SqlCompanyRepository(session)
                dedup = JobDedupService(job_repo, company_repo)

                for raw in raw_jobs:
                    try:
                        job = JobNormalizer.normalize(raw)
                        job = JobEnrichmentService.enrich(job)
                        _, is_new = await dedup.deduplicate(job)
                        if is_new:
                            new_count += 1
                        else:
                            updated_count += 1
                    except Exception:
                        pass
                await session.commit()

            total_new += new_count
            total_updated += updated_count
            results[scraper.source_name] = {"raw": len(raw_jobs), "new": new_count, "updated": updated_count}
            logger.info(f"{scraper.source_name}: {new_count} new, {updated_count} updated")
        except Exception as e:
            logger.error(f"Sweep failed for {scraper.source_name}: {e}")
            results[scraper.source_name] = {"error": str(e)[:200]}

    logger.info(f"Sweep complete: {total_new} new, {total_updated} updated")
    return {"new": total_new, "updated": total_updated, "sources": results}


@app.task(name="sweep_all_sources", bind=True, max_retries=1)
def sweep_all_sources(self):
    return asyncio.run(_sweep_all_async())


@app.task(name="mark_stale_jobs", bind=True)
def mark_stale_jobs(self, older_than_days: int = 30):
    async def _run():
        maker = get_sessionmaker()
        async with maker() as session:
            repo = SqlJobRepository(session)
            count = await repo.mark_stale_jobs(older_than_days)
            await session.commit()
            logger.info(f"Marked {count} jobs as stale")
            return {"stale_count": count}
    return asyncio.run(_run())


from celery.schedules import crontab
app.conf.beat_schedule = {
    "sweep-all-sources": {"task": "sweep_all_sources", "schedule": crontab(minute="7")},
    "mark-stale-jobs": {"task": "mark_stale_jobs", "schedule": crontab(hour="4", minute="23"), "kwargs": {"older_than_days": 30}},
}
app.conf.timezone = "UTC"
