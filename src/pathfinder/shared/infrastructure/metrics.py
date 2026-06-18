"""Prometheus metrics for Pathfinder."""
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class Metrics:
    def __init__(self):
        if not PROMETHEUS_AVAILABLE:
            self._counter = lambda name, desc, labels: _NoopCounter()
            self._histogram = lambda name, desc, labels: _NoopHistogram()
            self._gauge = lambda name, desc, labels: _NoopGauge()
            return

        self.agent_executions = Counter(
            "pathfinder_agent_executions_total", "Total agent executions",
            ["intent", "status"],
        )
        self.agent_latency = Histogram(
            "pathfinder_agent_latency_seconds", "Agent execution latency",
            ["intent"], buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
        )
        self.agent_tokens = Counter(
            "pathfinder_agent_tokens_total", "Total tokens used by agent",
            ["model", "type"],
        )
        self.job_discovery = Counter(
            "pathfinder_job_discovery_total", "Jobs discovered",
            ["source", "status"],
        )
        self.job_search_latency = Histogram(
            "pathfinder_job_search_latency_seconds", "Job search latency",
            buckets=[0.01, 0.05, 0.1, 0.3, 0.5, 1],
        )
        self.match_computations = Counter(
            "pathfinder_match_computations_total", "Match computations",
            ["tier"],
        )
        self.knowledge_ingested = Counter(
            "pathfinder_knowledge_chunks_total", "Knowledge chunks ingested",
        )
        self.knowledge_search_latency = Histogram(
            "pathfinder_knowledge_search_latency_seconds", "Knowledge search latency",
            buckets=[0.01, 0.05, 0.1, 0.3, 0.5, 1],
        )
        self.tailoring_generations = Counter(
            "pathfinder_tailoring_total", "Resume tailoring operations",
            ["strategy"],
        )
        self.api_requests = Counter(
            "pathfinder_api_requests_total", "API requests",
            ["method", "path", "status"],
        )
        self.api_latency = Histogram(
            "pathfinder_api_latency_seconds", "API request latency",
            ["method", "path"], buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
        )
        self.active_users = Gauge(
            "pathfinder_active_users", "Active users in last hour",
        )
        self.db_connections = Gauge(
            "pathfinder_db_connections", "Database connections",
            ["state"],
        )

    def get_metrics(self) -> str:
        if not PROMETHEUS_AVAILABLE:
            return "# prometheus_client not installed\n"
        from prometheus_client import generate_latest
        return generate_latest(REGISTRY).decode()


class _NoopCounter:
    def labels(self, **kw): return self
    def inc(self, amount=1): pass

class _NoopHistogram:
    def labels(self, **kw): return self
    def observe(self, amount): pass

class _NoopGauge:
    def labels(self, **kw): return self
    def set(self, value): pass
    def inc(self, amount=1): pass
    def dec(self, amount=1): pass


metrics = Metrics()
