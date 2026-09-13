from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from .models import TestResult


class Reporter:
    def __init__(self, report_dir: Path) -> None:
        self.report_dir = report_dir
        self.console = Console()

    def console_report(self, results: list[TestResult]) -> None:
        table = Table(title="School Discord Manager — E2E Test Suite")
        table.add_column("Test")
        table.add_column("Status")
        table.add_column("Duration", justify="right")
        for result in results:
            table.add_row(result.name, result.status.upper(), f"{result.duration_seconds:.2f}s")
        self.console.print(table)

    def write_json(self, results: list[TestResult], duration_seconds: float) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "status": "passed" if all(r.status in {"passed", "skipped", "warning"} for r in results) else "failed",
            "total": len(results),
            "passed": sum(r.status == "passed" for r in results),
            "failed": sum(r.status == "failed" for r in results),
            "warnings": sum(r.status == "warning" for r in results),
            "skipped": sum(r.status == "skipped" for r in results),
            "duration_seconds": duration_seconds,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tests": [{"name": r.name, "status": r.status, "duration_seconds": r.duration_seconds,
                       "message": r.message, "details": r.details} for r in results],
        }
        path = self.report_dir / "latest.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def write_html(self, results: list[TestResult], duration_seconds: float) -> Path:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        rows = "\n".join(
            f"<tr><td>{html.escape(r.name)}</td><td>{html.escape(r.status.upper())}</td>"
            f"<td>{r.duration_seconds:.2f}s</td><td><pre>{html.escape(r.message)}</pre></td></tr>"
            for r in results
        )
        document = f"""<!doctype html><html><head><meta charset='utf-8'><title>School Discord Manager E2E</title></head>
<body><h1>School Discord Manager — E2E</h1><p>Duration: {duration_seconds:.2f}s</p>
<table border='1' cellspacing='0' cellpadding='6'><thead><tr><th>Test</th><th>Status</th><th>Duration</th><th>Message</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""
        path = self.report_dir / "latest.html"
        path.write_text(document, encoding="utf-8")
        return path
