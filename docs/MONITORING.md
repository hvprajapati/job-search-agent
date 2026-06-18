# Pathfinder Monitoring

## Metrics Endpoint
```
GET /v1/metrics  →  Prometheus text format
```

## Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `pathfinder_agent_executions_total` | Counter | Agent invocations by intent + status |
| `pathfinder_agent_latency_seconds` | Histogram | Agent execution time |
| `pathfinder_agent_tokens_total` | Counter | LLM token consumption |
| `pathfinder_job_discovery_total` | Counter | Jobs discovered by source |
| `pathfinder_match_computations_total` | Counter | Match computations by tier |
| `pathfinder_knowledge_chunks_total` | Counter | Knowledge chunks ingested |
| `pathfinder_tailoring_total` | Counter | Tailoring operations by strategy |
| `pathfinder_api_requests_total` | Counter | API requests by method/path/status |
| `pathfinder_api_latency_seconds` | Histogram | API latency |

## Prometheus Configuration
```yaml
scrape_configs:
  - job_name: pathfinder
    scrape_interval: 15s
    static_configs:
      - targets: ['pathfinder:8000']
    metrics_path: /v1/metrics
```

## Grafana Dashboard
Import `docs/grafana-dashboard.json` for pre-built dashboard.
