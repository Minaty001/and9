# Phase 36: Analytics

## Purpose
Usage analytics and reporting with event tracking, performance metrics, report generation, anomaly detection, and dashboard rendering. `UsageTracker` records user events with aggregation, trends, and top-N queries. `PerformanceTracker` records performance metrics (response times, latencies) with statistical summaries (min, max, avg, median, p95, p99) and time series. `ReportGenerator` produces daily/weekly/monthly analytics reports with computed metrics, charts data, insights, and anomaly detection (spikes/drops). `DashboardGenerator` creates self-contained HTML dashboards from report data with inline CSS.

## Architecture
```
UsageTracker
  ├── track_event(Event) — record event with type, session, category, duration
  ├── get_event_count(type, period) → int
  ├── get_top_events(limit) → List[Dict]
  ├── get_event_trend(type) → daily time series
  └── get_events_in_period(start, end) / get_event_type_counts(start, end)

PerformanceTracker
  ├── record_metric(name, value, tags, unit) → UsageMetric
  ├── get_metric_stats(name) → {count, min, max, avg, median, p95, p99}
  ├── get_metric_timeseries(name) → List[TimeSeriesPoint]
  └── get_average(name) / get_all_metric_names()

ReportGenerator
  ├── generate_report(type) → AnalyticsReport
  ├── _compute_metrics / _compute_charts / _compute_insights
  └── _detect_anomalies — spike and drop detection

DashboardGenerator
  ├── generate_dashboard(report) → HTML string
  └── export_dashboard(report, path) → writes HTML file

Models: Event, UsageMetric, TimeSeriesPoint, AnalyticsReport
```

## Code
```python
class UsageTracker:
    def track_event(self, event: Event):
        self._events.append(event)
        self._prune_old()

    def get_top_events(self, limit=10) -> List[Dict]:
        counter = Counter(e.event_type for e in self._events)
        return [{"event_type": k, "count": v} for k, v in counter.most_common(limit)]

class PerformanceTracker:
    def record_metric(self, name, value, tags=None, unit="ms") -> UsageMetric:
        metric = UsageMetric(metric_name=name, value=value, unit=unit, tags=tags or {})
        self._metrics.append(metric)
        return metric

    def get_metric_stats(self, name) -> dict:
        values = sorted([m.value for m in self._metrics if m.metric_name == name])
        n = len(values)
        return {"count": n, "min": values[0], "max": values[-1], "avg": round(sum(values)/n, 2),
                "median": values[n//2], "p95": values[int(n*0.95)], "p99": values[int(n*0.99)]} if n else {}

class ReportGenerator:
    def generate_report(self, report_type="daily") -> AnalyticsReport:
        events = self.usage_tracker.get_events_in_period(period_start, period_end)
        metrics = self._compute_metrics(events)
        insights = self._compute_insights(events, metrics)
        anomalies = self._detect_anomalies(events)
        return AnalyticsReport(report_id=uuid.uuid4().hex[:12], report_type=report_type, metrics=metrics, insights=insights, anomalies=anomalies)
```

## Location
`app/core/analytics/` — usage tracker, performance tracker, report generator, dashboard generator
