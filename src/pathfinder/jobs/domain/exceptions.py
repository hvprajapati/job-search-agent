"""Job domain exceptions."""
from pathfinder.shared.domain.exceptions import NotFoundError, DomainError, ValidationError


class JobNotFoundError(NotFoundError):
    def __init__(self, job_id: str = "") -> None:
        super().__init__(f"Job not found{' : ' + job_id if job_id else ''}")


class CompanyNotFoundError(NotFoundError):
    def __init__(self, company_id: str = "") -> None:
        super().__init__(f"Company not found{' : ' + company_id if company_id else ''}")


class ScrapingError(DomainError):
    def __init__(self, source: str, detail: str = "") -> None:
        super().__init__(f"Scraping failed for {source}{': ' + detail if detail else ''}")


class InvalidFilterError(ValidationError):
    def __init__(self, field: str) -> None:
        super().__init__(f"Invalid filter: {field}", field=field)
