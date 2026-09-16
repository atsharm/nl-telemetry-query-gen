"""Definitions and few-shot examples for each supported telemetry query language.

Each entry gives the translator enough grounding (a short spec + example
NL -> query pairs) to produce syntactically valid queries without needing
a fine-tuned model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryLanguageSpec:
    name: str
    description: str
    examples: list[tuple[str, str]]


LOGQL = QueryLanguageSpec(
    name="LogQL",
    description=(
        "Grafana Loki's query language for logs. Selects log streams via "
        "label matchers in braces, then optionally pipes through filters "
        "and parsers, e.g. {job=\"app\"} |= \"error\" | json | rate(5m)."
    ),
    examples=[
        (
            "show me error logs from the payments service in the last 15 minutes",
            '{service="payments"} |= "error" [15m]',
        ),
        (
            "count of 500 errors per minute for the api service",
            'sum(count_over_time({service="api"} |= "500" [1m]))',
        ),
    ],
)

PROMQL = QueryLanguageSpec(
    name="PromQL",
    description=(
        "Prometheus's query language for metrics. Selects a metric by name "
        "with optional label matchers, then applies functions/aggregations, "
        "e.g. rate(http_requests_total{job=\"api\"}[5m])."
    ),
    examples=[
        (
            "request rate for the api service over the last 5 minutes",
            'rate(http_requests_total{job="api"}[5m])',
        ),
        (
            "p99 latency for the checkout service",
            'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="checkout"}[5m])) by (le))',
        ),
    ],
)

MQL = QueryLanguageSpec(
    name="MQL",
    description=(
        "OCI Monitoring Query Language for metrics. Format: "
        "namespace/metric[interval]{dimension = \"value\"}.aggregation, "
        "e.g. oci_computeagent/CpuUtilization[1m].mean()."
    ),
    examples=[
        (
            "average cpu utilization over the last minute",
            "oci_computeagent/CpuUtilization[1m].mean()",
        ),
        (
            "max memory utilization for instance i-123 over 5 minutes",
            'oci_computeagent/MemoryUtilization[5m]{resourceId = "i-123"}.max()',
        ),
    ],
)

SUPPORTED_LANGUAGES: dict[str, QueryLanguageSpec] = {
    "logql": LOGQL,
    "promql": PROMQL,
    "mql": MQL,
}
