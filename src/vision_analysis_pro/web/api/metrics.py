"""Prometheus metrics helpers for the API layer."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from threading import Lock
from typing import Any

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REQUEST_DURATION_BUCKETS_MS = (5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0)
INFERENCE_DURATION_BUCKETS_MS = (
    5.0,
    10.0,
    25.0,
    50.0,
    100.0,
    250.0,
    500.0,
    1000.0,
    2500.0,
    5000.0,
)


class ApiMetrics(Mapping[str, Any]):
    """Wrap Prometheus collectors while keeping readable metric snapshots."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self._lock = Lock()
        self._snapshot: dict[str, Any] = {
            "requests_total": 0,
            "requests_in_flight": 0,
            "requests_failed_total": 0,
            "request_duration_ms_sum": 0.0,
            "request_duration_ms_count": 0,
            "request_duration_ms_last": 0.0,
            "inference_requests_total": 0,
            "inference_failures_total": 0,
            "inference_success_total": 0,
            "inference_duration_ms_sum": 0.0,
            "inference_duration_ms_count": 0,
            "inference_duration_ms_last": 0.0,
            "inference_detections_total": 0,
            "inference_visualizations_total": 0,
            "inference_input_bytes_total": 0,
            "report_requests_total": 0,
            "report_query_requests_total": 0,
            "report_results_total": 0,
            "report_detections_total": 0,
            "report_duplicates_total": 0,
            "report_not_found_total": 0,
            "health_live_checks_total": 0,
            "health_ready_checks_total": 0,
            "health_ready_failures_total": 0,
            "request_status_total": {},
        }
        self._counters = {
            "requests_total": Counter(
                "vision_api_requests",
                "Total HTTP requests.",
                registry=self.registry,
            ),
            "requests_failed_total": Counter(
                "vision_api_requests_failed",
                "Total failed HTTP requests.",
                registry=self.registry,
            ),
            "inference_requests_total": Counter(
                "vision_api_inference_requests",
                "Total inference requests.",
                registry=self.registry,
            ),
            "inference_failures_total": Counter(
                "vision_api_inference_failures",
                "Total failed inference requests.",
                registry=self.registry,
            ),
            "inference_success_total": Counter(
                "vision_api_inference_success",
                "Total successful inference requests.",
                registry=self.registry,
            ),
            "inference_detections_total": Counter(
                "vision_api_inference_detections",
                "Total detections returned by inference requests.",
                registry=self.registry,
            ),
            "inference_visualizations_total": Counter(
                "vision_api_inference_visualizations",
                "Total inference requests returning visualizations.",
                registry=self.registry,
            ),
            "inference_input_bytes_total": Counter(
                "vision_api_inference_input_bytes",
                "Total input bytes accepted by inference requests.",
                registry=self.registry,
            ),
            "report_requests_total": Counter(
                "vision_api_report_requests",
                "Total edge report requests.",
                registry=self.registry,
            ),
            "report_query_requests_total": Counter(
                "vision_api_report_query_requests",
                "Total edge report query requests.",
                registry=self.registry,
            ),
            "report_results_total": Counter(
                "vision_api_report_results",
                "Total edge inference results received.",
                registry=self.registry,
            ),
            "report_detections_total": Counter(
                "vision_api_report_detections",
                "Total edge detections received.",
                registry=self.registry,
            ),
            "report_duplicates_total": Counter(
                "vision_api_report_duplicates",
                "Total duplicate report batches ignored.",
                registry=self.registry,
            ),
            "report_not_found_total": Counter(
                "vision_api_report_not_found",
                "Total report queries that missed persisted batches.",
                registry=self.registry,
            ),
            "health_live_checks_total": Counter(
                "vision_api_health_live_checks",
                "Total live health checks.",
                registry=self.registry,
            ),
            "health_ready_checks_total": Counter(
                "vision_api_health_ready_checks",
                "Total ready health checks.",
                registry=self.registry,
            ),
            "health_ready_failures_total": Counter(
                "vision_api_health_ready_failures",
                "Total failed ready health checks.",
                registry=self.registry,
            ),
        }
        self._gauges = {
            "requests_in_flight": Gauge(
                "vision_api_requests_in_flight",
                "In-flight HTTP requests.",
                registry=self.registry,
            ),
            "request_duration_ms_last": Gauge(
                "vision_api_request_duration_ms_last",
                "Last observed HTTP request duration in milliseconds.",
                registry=self.registry,
            ),
            "inference_duration_ms_last": Gauge(
                "vision_api_inference_duration_ms_last",
                "Last observed inference duration in milliseconds.",
                registry=self.registry,
            ),
        }
        self._histograms = {
            "request_duration_ms": Histogram(
                "vision_api_request_duration_ms",
                "Observed HTTP request duration in milliseconds.",
                buckets=REQUEST_DURATION_BUCKETS_MS,
                registry=self.registry,
            ),
            "inference_duration_ms": Histogram(
                "vision_api_inference_duration_ms",
                "Observed inference duration in milliseconds.",
                buckets=INFERENCE_DURATION_BUCKETS_MS,
                registry=self.registry,
            ),
        }
        self._request_status_counter = Counter(
            "vision_api_request_status",
            "Total HTTP requests by method, route and status code.",
            labelnames=("method", "path", "status_code"),
            registry=self.registry,
        )

    @property
    def content_type(self) -> str:
        return CONTENT_TYPE_LATEST

    def inc(self, key: str, amount: int | float = 1) -> None:
        metric = self._counters[key]
        with self._lock:
            metric.inc(amount)
            self._snapshot[key] += amount

    def inc_gauge(self, key: str, amount: int | float = 1) -> None:
        metric = self._gauges[key]
        with self._lock:
            metric.inc(amount)
            self._snapshot[key] += amount

    def dec_gauge(self, key: str, amount: int | float = 1) -> None:
        metric = self._gauges[key]
        with self._lock:
            metric.dec(amount)
            self._snapshot[key] -= amount

    def observe(self, key: str, value: float) -> None:
        metric = self._histograms[key]
        last_key = f"{key}_last"
        sum_key = f"{key}_sum"
        count_key = f"{key}_count"
        with self._lock:
            metric.observe(value)
            self._snapshot[sum_key] += value
            self._snapshot[count_key] += 1
            self._snapshot[last_key] = value
            self._gauges[last_key].set(value)

    def inc_request_status(self, *, method: str, path: str, status_code: int) -> None:
        key = (method, path, str(status_code))
        with self._lock:
            self._request_status_counter.labels(
                method=method,
                path=path,
                status_code=str(status_code),
            ).inc()
            request_status_total: dict[tuple[str, str, str], int] = self._snapshot[
                "request_status_total"
            ]
            request_status_total[key] = request_status_total.get(key, 0) + 1

    def render(self) -> str:
        return generate_latest(self.registry).decode("utf-8")

    def __getitem__(self, key: str) -> Any:
        value = self._snapshot[key]
        if isinstance(value, dict):
            return dict(value)
        return value

    def __iter__(self) -> Iterator[str]:
        return iter(self._snapshot)

    def __len__(self) -> int:
        return len(self._snapshot)


def create_api_metrics() -> ApiMetrics:
    return ApiMetrics()
