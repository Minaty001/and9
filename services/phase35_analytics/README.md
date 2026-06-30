# Phase 35: Analytics

## Overview

Usage tracking, performance metrics, user engagement, report generation with daily/weekly/monthly summaries and anomaly detection.

## Architecture

```
Events / Metrics
     │
     ├──────────────┬──────────────┐
     ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌──────────────┐
│UsageTracker │ │Performance │ │ReportGenerator│
│            │ │Tracker     │ │              │
│ Event count │ │ Stats      │ │ Insights     │
│ Trends     │ │ Time series│ │ Anomalies    │
│ Top events │ │ Avg/median │ │ Charts       │
└────────────┘ └────────────┘ └──────────────┘
     │              │              │
     └──────────────┴──────────────┘
                    │
                    ▼
        ┌─────────────────────┐
        │ AnalyticsService     │
        │ (ServiceBase)        │
        └─────────────────────┘
```

## Components

- **UsageTracker**: Tracks events with per-type counts, daily trends, and top event rankings. Supports period filtering (today/week/month).
- **PerformanceTracker**: Records numeric metrics with statistical summaries (min/max/avg/median/p95/p99) and time series queries.
- **ReportGenerator**: Aggregates events and metrics into daily/weekly/monthly reports. Generates insights (peak hour, most used feature). Detects anomalies (spikes >3x average, drops <30% of average).
- **AnalyticsService**: ServiceBase wrapper with event tracking, metric recording, report generation, and data export.

## Usage

```python
from services.phase35_analytics import AnalyticsService, Event
svc = AnalyticsService()
await svc.initialize()

# Track usage
await svc.track_event(Event(
    event_type="page_view", user_id="user123",
    category="navigation", duration_ms=1500
))

# Record performance
await svc.record_metric("response_time", 245.3, tags={"endpoint": "/api"})

# Generate report
report = await svc.generate_report("daily")
for insight in report.insights:
    print(insight)
```

## Report Insights

- Total events and unique users
- Peak usage hour
- Average event duration
- Most used features
- Anomaly detection (spikes and drops)

## Test Coverage

22+ tests covering all components and the service wrapper.
