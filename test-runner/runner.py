"""
Test Runner Service — Web UI for sending realistic test data to the Incident Platform.

Provides an interactive dashboard to:
  - View & send predefined alert scenarios one-by-one or all at once
  - Send custom alerts with free-form fields
  - Run continuous load with configurable interval
  - Monitor service health in real time
  - View execution history with AI analysis results

Runs as a FastAPI server on port 8006.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test-runner")

# ── Configuration ────────────────────────────────────────────

ALERT_URL = os.getenv("ALERT_URL", "http://alert-ingestion:8001/api/v1/alerts")
INCIDENT_URL = os.getenv("INCIDENT_URL", "http://incident-management:8002/api/v1/incidents")
ONCALL_URL = os.getenv("ONCALL_URL", "http://oncall-service:8003/api/v1/oncall")
AI_ANALYSIS_URL = os.getenv("AI_ANALYSIS_URL", "http://ai-analysis:8005/api/v1/analyze")
HEALTH_URLS = {
    "alert-ingestion": "http://alert-ingestion:8001/health",
    "incident-management": "http://incident-management:8002/health",
    "oncall-service": "http://oncall-service:8003/health",
    "notification-service": "http://notification-service:8004/health",
    "ai-analysis": "http://ai-analysis:8005/health",
}
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8006"))

# ── Test Scenarios ───────────────────────────────────────────

ALERT_SCENARIOS = [
    {
        "id": "cpu-high",
        "category": "CPU / Compute",
        "service": "payment-api",
        "severity": "critical",
        "message": "CPU utilization at 98% on payment-api-pod-3. Process java consuming 95% CPU.",
        "labels": {"env": "production", "region": "us-east-1", "pod": "payment-api-pod-3"},
    },
    {
        "id": "cpu-throttle",
        "category": "CPU / Compute",
        "service": "auth-service",
        "severity": "high",
        "message": "CPU throttling detected on auth-service container. CPU limit exceeded by 40%.",
        "labels": {"env": "production", "region": "eu-west-1", "container": "auth-svc"},
    },
    {
        "id": "mem-oom",
        "category": "Memory",
        "service": "user-service",
        "severity": "critical",
        "message": "OOM Killed: user-service process terminated by kernel. Memory usage exceeded 4GB limit.",
        "labels": {"env": "production", "pod": "user-svc-pod-1"},
    },
    {
        "id": "mem-high",
        "category": "Memory",
        "service": "cache-service",
        "severity": "high",
        "message": "High memory usage on cache-service: 92% utilization. Possible memory leak detected.",
        "labels": {"env": "staging", "host": "cache-01"},
    },
    {
        "id": "disk-full",
        "category": "Disk",
        "service": "log-collector",
        "severity": "high",
        "message": "Disk space critically low: /var/log at 96% capacity. Only 2GB remaining.",
        "labels": {"env": "production", "host": "log-01", "mount": "/var/log"},
    },
    {
        "id": "net-timeout",
        "category": "Network",
        "service": "api-gateway",
        "severity": "critical",
        "message": "Connection timeout to downstream payment-api service. Gateway timeout after 30s.",
        "labels": {"env": "production", "downstream": "payment-api"},
    },
    {
        "id": "net-refused",
        "category": "Network",
        "service": "order-service",
        "severity": "high",
        "message": "Connection refused to inventory-service on port 8080. ECONNREFUSED.",
        "labels": {"env": "production", "target": "inventory-service:8080"},
    },
    {
        "id": "db-pool",
        "category": "Database",
        "service": "user-service",
        "severity": "critical",
        "message": "Database connection pool exhausted. All 50 connections in use. New queries timing out.",
        "labels": {"env": "production", "db": "users-primary"},
    },
    {
        "id": "db-slow",
        "category": "Database",
        "service": "analytics-service",
        "severity": "medium",
        "message": "Slow query detected: SELECT with 3 table joins taking 15 seconds. Query plan using sequential scan.",
        "labels": {"env": "production", "db": "analytics-replica"},
    },
    {
        "id": "http-500",
        "category": "HTTP Errors",
        "service": "api-gateway",
        "severity": "critical",
        "message": "Error rate spike: 500 Internal Server Error rate at 25% over last 5 minutes.",
        "labels": {"env": "production", "endpoint": "/api/v1/checkout"},
    },
    {
        "id": "http-401",
        "category": "HTTP Errors",
        "service": "auth-service",
        "severity": "medium",
        "message": "Elevated 401 Unauthorized responses. Rate increased from 2% to 15% in 10 minutes.",
        "labels": {"env": "production", "endpoint": "/api/v1/login"},
    },
    {
        "id": "ssl-expiry",
        "category": "SSL/TLS",
        "service": "api-gateway",
        "severity": "high",
        "message": "SSL certificate expiring in 7 days for api.example.com. Auto-renewal failed.",
        "labels": {"env": "production", "domain": "api.example.com"},
    },
    {
        "id": "k8s-crash",
        "category": "Kubernetes",
        "service": "payment-api",
        "severity": "high",
        "message": "Pod crash loop detected: payment-api-pod-5 restarted 8 times in 10 minutes. CrashLoopBackOff.",
        "labels": {"env": "production", "pod": "payment-api-pod-5", "namespace": "default"},
    },
    {
        "id": "k8s-hpa",
        "category": "Kubernetes",
        "service": "notification-worker",
        "severity": "medium",
        "message": "Kubernetes HPA unable to scale: notification-worker deployment max replicas (10) reached.",
        "labels": {"env": "production", "deployment": "notification-worker"},
    },
    {
        "id": "queue-backlog",
        "category": "Queue",
        "service": "order-processor",
        "severity": "high",
        "message": "Message queue backlog growing: orders-queue has 50000 pending messages. Consumer lag increasing.",
        "labels": {"env": "production", "queue": "orders-queue", "broker": "rabbitmq"},
    },
]

ONCALL_SCHEDULES = [
    {"team": "platform", "user_name": "alice", "user_email": "alice@example.com"},
    {"team": "backend", "user_name": "bob", "user_email": "bob@example.com"},
    {"team": "frontend", "user_name": "charlie", "user_email": "charlie@example.com"},
    {"team": "sre", "user_name": "diana", "user_email": "diana@example.com"},
    {"team": "data", "user_name": "eve", "user_email": "eve@example.com"},
]

# ── State ────────────────────────────────────────────────────

execution_log: deque = deque(maxlen=200)
continuous_task: Optional[asyncio.Task] = None
ws_clients: set[WebSocket] = set()


# ── Models ───────────────────────────────────────────────────


class CustomAlert(BaseModel):
    service: str
    severity: str
    message: str
    labels: dict = {}


class ContinuousConfig(BaseModel):
    interval: int = 15
    categories: list[str] = []


# ── Helpers ──────────────────────────────────────────────────


async def broadcast(event: dict):
    """Send event to all connected WebSocket clients."""
    dead = set()
    msg = json.dumps(event)
    for ws in ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    ws_clients.difference_update(dead)


async def send_alert(alert: dict) -> dict:
    """Send alert to ingestion service and return result."""
    payload = {k: v for k, v in alert.items() if k not in ("id", "category")}
    result = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario_id": alert.get("id", "custom"),
        "service": alert["service"],
        "severity": alert["severity"],
        "message": alert["message"][:100],
        "status": "pending",
        "alert_id": None,
        "incident_id": None,
        "ai_suggestions": [],
    }

    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Send alert
        try:
            resp = await client.post(ALERT_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            result["alert_id"] = data.get("alert_id")
            result["incident_id"] = data.get("incident_id")
            result["status"] = "sent"
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            execution_log.appendleft(result)
            await broadcast({"type": "result", "data": result})
            return result

        # 2. AI analysis
        try:
            ai_payload = {
                "message": alert["message"],
                "service": alert["service"],
                "severity": alert["severity"],
                "alert_id": result["alert_id"],
                "incident_id": result["incident_id"],
            }
            ai_resp = await client.post(AI_ANALYSIS_URL, json=ai_payload)
            ai_resp.raise_for_status()
            ai_data = ai_resp.json()
            result["ai_suggestions"] = ai_data.get("suggestions", [])[:3]
            result["status"] = "analysed"
        except Exception:
            result["status"] = "sent"  # alert sent OK, AI failed

    execution_log.appendleft(result)
    await broadcast({"type": "result", "data": result})
    return result


async def check_health() -> dict:
    """Check health of all services."""
    health = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in HEALTH_URLS.items():
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    health[name] = {"status": "healthy", "data": resp.json()}
                else:
                    health[name] = {"status": "unhealthy", "code": resp.status_code}
            except Exception as e:
                health[name] = {"status": "unreachable", "error": str(e)[:80]}
    return health


async def setup_oncall() -> list[dict]:
    """Configure on-call schedules."""
    results = []
    async with httpx.AsyncClient(timeout=10) as client:
        for sched in ONCALL_SCHEDULES:
            try:
                resp = await client.post(f"{ONCALL_URL}/schedule", json=sched)
                results.append({"team": sched["team"], "user": sched["user_name"], "status": resp.status_code})
            except Exception as e:
                results.append(
                    {"team": sched["team"], "user": sched["user_name"], "status": "error", "error": str(e)[:60]}
                )
    return results


# ── Continuous mode ──────────────────────────────────────────


async def _continuous_loop(interval: int, categories: list[str]):
    """Background loop sending random alerts."""
    pool = ALERT_SCENARIOS
    if categories:
        pool = [s for s in ALERT_SCENARIOS if s["category"].lower() in [c.lower() for c in categories]]
    if not pool:
        pool = ALERT_SCENARIOS

    count = 0
    try:
        while True:
            scenario = random.choice(pool)
            alert = dict(scenario)
            count += 1
            alert["message"] += f" [auto #{count} @ {datetime.now(timezone.utc).strftime('%H:%M:%S')}]"
            await broadcast({"type": "continuous_tick", "count": count, "scenario": scenario["id"]})
            await send_alert(alert)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        await broadcast({"type": "continuous_stopped", "total": count})


# ── FastAPI App ──────────────────────────────────────────────

app = FastAPI(title="Test Runner", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "test-runner", "scenarios": len(ALERT_SCENARIOS)}


# ── API ──────────────────────────────────────────────────────


@app.get("/api/scenarios")
async def list_scenarios():
    """List all available test scenarios."""
    categories = {}
    for s in ALERT_SCENARIOS:
        cat = s["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(
            {
                "id": s["id"],
                "service": s["service"],
                "severity": s["severity"],
                "message": s["message"],
                "labels": s.get("labels", {}),
            }
        )
    return {"total": len(ALERT_SCENARIOS), "categories": categories}


@app.post("/api/send/{scenario_id}")
async def send_scenario(scenario_id: str):
    """Send a single predefined scenario."""
    scenario = next((s for s in ALERT_SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        return {"error": f"Scenario '{scenario_id}' not found"}, 404
    return await send_alert(scenario)


@app.post("/api/send-all")
async def send_all():
    """Send all scenarios sequentially."""
    results = {"sent": 0, "failed": 0, "analysed": 0, "details": []}
    for scenario in ALERT_SCENARIOS:
        r = await send_alert(scenario)
        results["details"].append(r)
        if r["status"] == "analysed":
            results["analysed"] += 1
            results["sent"] += 1
        elif r["status"] == "sent":
            results["sent"] += 1
        else:
            results["failed"] += 1
        await asyncio.sleep(0.3)
    return results


@app.post("/api/send-custom")
async def send_custom(alert: CustomAlert):
    """Send a custom alert."""
    return await send_alert(
        {
            "id": "custom",
            "category": "Custom",
            "service": alert.service,
            "severity": alert.severity,
            "message": alert.message,
            "labels": alert.labels,
        }
    )


@app.post("/api/continuous/start")
async def start_continuous(config: ContinuousConfig):
    """Start continuous alert generation."""
    global continuous_task
    if continuous_task and not continuous_task.done():
        return {"status": "already_running"}
    continuous_task = asyncio.create_task(_continuous_loop(config.interval, config.categories))
    return {"status": "started", "interval": config.interval}


@app.post("/api/continuous/stop")
async def stop_continuous():
    """Stop continuous alert generation."""
    global continuous_task
    if continuous_task and not continuous_task.done():
        continuous_task.cancel()
        continuous_task = None
        return {"status": "stopped"}
    return {"status": "not_running"}


@app.get("/api/continuous/status")
async def continuous_status():
    running = continuous_task is not None and not continuous_task.done()
    return {"running": running}


@app.get("/api/health-check")
async def health_check_all():
    """Check health of all platform services."""
    return await check_health()


@app.post("/api/setup-oncall")
async def api_setup_oncall():
    """Setup on-call schedules."""
    return await setup_oncall()


@app.get("/api/history")
async def get_history():
    """Get recent execution history."""
    return list(execution_log)


@app.delete("/api/history")
async def clear_history():
    """Clear execution history."""
    execution_log.clear()
    return {"status": "cleared"}


# ── WebSocket (live results) ─────────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(websocket)


# ── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
