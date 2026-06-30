"""
Phase 35 — Dashboard Generator.

Generates self-contained HTML dashboards from analytics report data
with inline CSS styling.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional

from .config import AnalyticsConfig
from .models import AnalyticsReport

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """Generates self-contained HTML dashboards from analytics reports.

    Usage:
        gen = DashboardGenerator(config)
        html = gen.generate_dashboard(report)
        gen.export_dashboard(report, '/path/to/dashboard.html')
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or AnalyticsConfig()

    def generate_dashboard(self, report: AnalyticsReport) -> str:
        """Generate a complete HTML dashboard from a report.

        Args:
            report: The AnalyticsReport to visualize.

        Returns:
            Self-contained HTML string.
        """
        overview_html = self._render_overview(report)
        performance_html = self._render_performance(report)
        top_events_html = self._render_top_events(report)
        trend_html = self._render_daily_trend(report)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Analytics Dashboard - {report.report_type.capitalize()} Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; padding: 24px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 32px; border-radius: 12px; margin-bottom: 24px; }}
.header h1 {{ font-size: 28px; margin-bottom: 8px; }}
.header .meta {{ opacity: 0.85; font-size: 14px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.card {{ background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.card h3 {{ font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; color: #888; margin-bottom: 8px; }}
.card .value {{ font-size: 32px; font-weight: 700; color: #333; }}
.card .sub {{ font-size: 13px; color: #888; margin-top: 4px; }}
.section {{ background: #fff; border-radius: 10px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 24px; }}
.section h2 {{ font-size: 18px; margin-bottom: 16px; color: #444; border-bottom: 2px solid #f0f0f0; padding-bottom: 8px; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ text-align: left; padding: 10px 12px; font-size: 12px; text-transform: uppercase; color: #888; border-bottom: 2px solid #f0f0f0; }}
td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0f0; font-size: 14px; }}
tr:hover td {{ background: #f9fafb; }}
.bar {{ display: inline-block; height: 8px; border-radius: 4px; background: #667eea; margin-right: 8px; }}
.bar-label {{ font-size: 13px; color: #555; }}
.trend-list {{ list-style: none; }}
.trend-list li {{ padding: 6px 0; font-size: 14px; border-bottom: 1px solid #f5f5f5; display: flex; justify-content: space-between; }}
.trend-list li:last-child {{ border-bottom: none; }}
.status-good {{ color: #48bb78; }}
.status-warn {{ color: #ecc94b; }}
.status-bad {{ color: #f56565; }}
.insight-item {{ padding: 8px 12px; margin: 4px 0; background: #f0f4ff; border-left: 3px solid #667eea; border-radius: 4px; font-size: 14px; }}
.summary-card {{ display: inline-block; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: #fff; border-radius: 10px; padding: 24px; margin: 8px; min-width: 180px; }}
.summary-card h4 {{ font-size: 13px; opacity: 0.85; margin-bottom: 8px; text-transform: uppercase; }}
.summary-card .value {{ font-size: 28px; font-weight: 700; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>Analytics Dashboard</h1>
<div class="meta">{report.report_type.capitalize()} report &mdash; {report.period_start.strftime('%Y-%m-%d %H:%M')} to {report.period_end.strftime('%Y-%m-%d %H:%M')} &mdash; Generated {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}</div>
</div>
{overview_html}
{performance_html}
{top_events_html}
{trend_html}
</div>
</body>
</html>"""
        return html

    def generate_summary_card(self, metrics: dict) -> str:
        """Generate a summary card HTML snippet from metrics.

        Args:
            metrics: Dict with metric keys (total_events, unique_users, etc.).

        Returns:
            HTML string for a summary card.
        """
        total = metrics.get("total_events", 0)
        users = metrics.get("unique_users", 0)
        avg_dur = metrics.get("avg_duration_ms", 0)

        return f"""<div class="summary-card">
<h4>Summary</h4>
<div class="value">{total}</div>
<div style="margin-top:12px; font-size:13px; opacity:0.9;">
  {users} users &middot; {avg_dur}ms avg
</div>
</div>"""

    def export_dashboard(self, report: AnalyticsReport, path: str) -> bool:
        """Generate and write a dashboard HTML file.

        Args:
            report: The AnalyticsReport.
            path: Output file path.

        Returns:
            True if written successfully.
        """
        html = self.generate_dashboard(report)
        try:
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(path, "w") as f:
                f.write(html)
            logger.info("Dashboard exported to %s", path)
            return True
        except OSError as e:
            logger.error("Failed to export dashboard to %s: %s", path, e)
            return False

    def _render_overview(self, report: AnalyticsReport) -> str:
        """Render the overview section with metric cards."""
        metrics = report.metrics
        perf = report.performance_summary

        total_events = metrics.get("total_events", 0)
        unique_users = metrics.get("unique_users", 0)
        success_rate = perf.get("success_rate", 100.0)
        total_ops = perf.get("total_operations", 0)

        success_class = "status-good" if success_rate >= 95 else ("status-warn" if success_rate >= 80 else "status-bad")

        cards = f"""
<div class="grid">
  <div class="card">
    <h3>Total Events</h3>
    <div class="value">{total_events}</div>
    <div class="sub">in this period</div>
  </div>
  <div class="card">
    <h3>Active Users</h3>
    <div class="value">{unique_users}</div>
    <div class="sub">unique users</div>
  </div>
  <div class="card">
    <h3>Operations</h3>
    <div class="value">{total_ops}</div>
    <div class="sub">total operations</div>
  </div>
  <div class="card">
    <h3>Success Rate</h3>
    <div class="value {success_class}">{success_rate}%</div>
    <div class="sub">overall</div>
  </div>
</div>"""

        # Insights
        insights_html = ""
        if report.insights:
            items = "".join(
                f'<div class="insight-item">{insight}</div>'
                for insight in report.insights
            )
            insights_html = f'<h3 style="margin-bottom:8px;font-size:15px;">Insights</h3>{items}'

        return f"""
<div class="section">
<h2>Overview</h2>
{cards}
{insights_html}
</div>"""

    def _render_performance(self, report: AnalyticsReport) -> str:
        """Render the performance section with latency and error data."""
        perf = report.performance_summary
        if not perf:
            return ""

        avg_lat = perf.get("avg_latency", 0)
        p50 = perf.get("p50_latency", 0)
        p95 = perf.get("p95_latency", 0)
        p99 = perf.get("p99_latency", 0)
        error_rate = perf.get("error_rate", 0)
        success_rate = perf.get("success_rate", 100.0)
        slowest = perf.get("slowest_endpoint", "N/A")
        busiest = perf.get("busiest_hour", "N/A")

        error_class = "status-good" if error_rate < 5 else ("status-warn" if error_rate < 20 else "status-bad")

        return f"""
<div class="section">
<h2>Performance</h2>
<div class="grid">
  <div class="card">
    <h3>Avg Latency</h3>
    <div class="value">{avg_lat}ms</div>
  </div>
  <div class="card">
    <h3>P50 / P95 / P99</h3>
    <div class="value" style="font-size:20px;">{p50} / {p95} / {p99} ms</div>
  </div>
  <div class="card">
    <h3>Error Rate</h3>
    <div class="value {error_class}">{error_rate}%</div>
    <div class="sub">success: {success_rate}%</div>
  </div>
  <div class="card">
    <h3>Slowest Endpoint</h3>
    <div class="value" style="font-size:18px;">{slowest}</div>
  </div>
  <div class="card">
    <h3>Busiest Hour</h3>
    <div class="value">{busiest}</div>
  </div>
</div>
</div>"""

    def _render_top_events(self, report: AnalyticsReport) -> str:
        """Render the top events table."""
        top_events = report.top_events
        if not top_events:
            return ""

        rows = "".join(
            f"<tr><td>{i+1}</td><td>{e.get('event_type', '')}</td><td>{e.get('count', 0)}</td></tr>"
            for i, e in enumerate(top_events[:10])
        )

        return f"""
<div class="section">
<h2>Top Events</h2>
<table>
<thead><tr><th>#</th><th>Event Type</th><th>Count</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>"""

    def _render_daily_trend(self, report: AnalyticsReport) -> str:
        """Render the daily trend section."""
        charts = report.charts
        daily = charts.get("daily_events", {}) if charts else {}

        if not daily:
            return ""

        max_count = max(daily.values()) if daily else 1
        items = ""
        for day, count in sorted(daily.items()):
            pct = (count / max_count) * 100 if max_count > 0 else 0
            items += f'<li><span class="bar-label">{day}</span><span><span class="bar" style="width:{pct}px"></span>{count}</span></li>'

        # Also show hourly distribution
        hourly = charts.get("hourly_distribution", {}) if charts else {}
        hourly_items = ""
        if hourly:
            max_h = max(hourly.values()) if hourly else 1
            for h in range(24):
                count = hourly.get(str(h), 0)
                pct = (count / max_h) * 100 if max_h > 0 else 0
                if count > 0:
                    hourly_items += f'<li><span class="bar-label">{h}:00</span><span><span class="bar" style="width:{pct}px;background:#a78bfa;"></span>{count}</span></li>'

        hourly_section = ""
        if hourly_items:
            hourly_section = f"""
<h3 style="margin-top:20px;margin-bottom:8px;font-size:15px;">Hourly Distribution</h3>
<ul class="trend-list">{hourly_items}</ul>"""

        return f"""
<div class="section">
<h2>Daily Trend</h2>
<ul class="trend-list">{items}</ul>
{hourly_section}
</div>"""
