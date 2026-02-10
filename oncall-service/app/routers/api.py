import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.database import get_db_connection
from app.metrics import (
    active_escalation_timers,
    auto_escalation_runs_total,
    escalation_notifications_total,
    escalation_rate,
    escalations_total,
    oncall_current,
)
from app.models import (
    AutoEscalationResult,
    CurrentOnCallResponse,
    Engineer,
    EscalateRequest,
    EscalateResponse,
    EscalationPolicyCreateRequest,
    EscalationPolicyLevel,
    EscalationPolicyResponse,
    OnCallEngineer,
    OnCallMetrics,
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers -- rotation logic
# ---------------------------------------------------------------------------


def _compute_current_oncall(schedule: dict) -> tuple[Engineer | None, Engineer | None]:
    """Compute the current primary and secondary on-call from a rotation schedule.

    For *weekly* rotations the on-call engineer index is determined by
    the number of full weeks since ``start_date``.  For *daily* rotations
    the index is the number of full days since ``start_date``.

    Returns (primary_engineer, secondary_engineer) where secondary is the
    next engineer in the rotation or ``None`` if the team has only one
    member.
    """
    engineers = schedule["engineers"]
    if not engineers:
        return None, None

    # Parse engineers -- they're stored as JSONB (list of dicts)
    if isinstance(engineers, str):
        engineers = json.loads(engineers)

    engineer_list = [Engineer(**e) if isinstance(e, dict) else e for e in engineers]
    if not engineer_list:
        return None, None

    start = schedule["start_date"]
    if isinstance(start, str):
        start = date.fromisoformat(start)
    elif isinstance(start, datetime):
        start = start.date()

    today = date.today()
    delta_days = (today - start).days
    if delta_days < 0:
        delta_days = 0

    rotation_type = schedule.get("rotation_type", "weekly")
    if rotation_type == "daily":
        idx = delta_days % len(engineer_list)
    else:  # weekly
        idx = (delta_days // 7) % len(engineer_list)

    primary = engineer_list[idx]
    secondary = engineer_list[(idx + 1) % len(engineer_list)] if len(engineer_list) > 1 else None

    return primary, secondary


# ---------------------------------------------------------------------------
# POST /schedules -- create a new rotation schedule
# ---------------------------------------------------------------------------


@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(body: ScheduleCreateRequest):
    """Create a new on-call rotation schedule for a team."""
    schedule_id = str(uuid.uuid4())
    engineers_json = [e.model_dump() for e in body.engineers]

    try:
        with get_db_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO oncall.schedules (id, team, rotation_type, start_date, engineers, escalation_minutes)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    RETURNING id, team, rotation_type, start_date, engineers, escalation_minutes, created_at
                    """,
                    (
                        schedule_id,
                        body.team,
                        body.rotation_type.value,
                        body.start_date.isoformat(),
                        json.dumps(engineers_json),
                        body.escalation_minutes,
                    ),
                )
                row = cur.fetchone()
    except Exception as exc:
        logger.error(f"Failed to create schedule: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create schedule") from exc

    engineers_data = row["engineers"]
    if isinstance(engineers_data, str):
        engineers_data = json.loads(engineers_data)

    return ScheduleResponse(
        id=str(row["id"]),
        team=row["team"],
        rotation_type=row["rotation_type"],
        start_date=row["start_date"],
        engineers=[Engineer(**e) for e in engineers_data],
        escalation_minutes=row["escalation_minutes"],
        created_at=row["created_at"],
    )


# ---------------------------------------------------------------------------
# GET /schedules -- list all schedules
# ---------------------------------------------------------------------------


@router.get("/schedules", response_model=ScheduleListResponse)
def list_schedules(
    team: Optional[str] = Query(None, description="Filter by team name"),
):
    """List all on-call schedules, optionally filtered by team."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if team:
                    cur.execute(
                        "SELECT * FROM oncall.schedules WHERE team = %s ORDER BY created_at DESC",
                        (team,),
                    )
                else:
                    cur.execute("SELECT * FROM oncall.schedules ORDER BY created_at DESC")
                rows = cur.fetchall()
    except Exception as exc:
        logger.error(f"Failed to list schedules: {exc}")
        raise HTTPException(status_code=500, detail="Failed to list schedules") from exc

    schedules = []
    for row in rows:
        engineers_data = row["engineers"]
        if isinstance(engineers_data, str):
            engineers_data = json.loads(engineers_data)
        schedules.append(
            ScheduleResponse(
                id=str(row["id"]),
                team=row["team"],
                rotation_type=row["rotation_type"],
                start_date=row["start_date"],
                engineers=[Engineer(**e) for e in engineers_data],
                escalation_minutes=row["escalation_minutes"],
                created_at=row["created_at"],
            )
        )

    return ScheduleListResponse(schedules=schedules, total=len(schedules))


# ---------------------------------------------------------------------------
# GET /oncall/current -- who is on-call right now?
# ---------------------------------------------------------------------------


@router.get("/oncall/current", response_model=CurrentOnCallResponse)
def get_current_oncall(
    team: str = Query(..., description="Team name to look up"),
):
    """Get the current primary and secondary on-call engineers for a team."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM oncall.schedules WHERE team = %s ORDER BY created_at DESC LIMIT 1",
                    (team,),
                )
                schedule = cur.fetchone()
    except Exception as exc:
        logger.error(f"Failed to query on-call: {exc}")
        raise HTTPException(status_code=500, detail="Failed to query on-call schedule") from exc

    if not schedule:
        raise HTTPException(status_code=404, detail=f"No schedule found for team '{team}'")

    primary_eng, secondary_eng = _compute_current_oncall(schedule)

    if not primary_eng:
        raise HTTPException(status_code=404, detail=f"No engineers configured for team '{team}'")

    # Update Prometheus gauge
    oncall_current.labels(team=team, engineer=primary_eng.email, role="primary").set(1)
    if secondary_eng:
        oncall_current.labels(team=team, engineer=secondary_eng.email, role="secondary").set(1)

    primary = OnCallEngineer(name=primary_eng.name, email=primary_eng.email, role="primary")
    secondary = (
        OnCallEngineer(name=secondary_eng.name, email=secondary_eng.email, role="secondary") if secondary_eng else None
    )

    return CurrentOnCallResponse(
        team=team,
        primary=primary,
        secondary=secondary,
        schedule_id=str(schedule["id"]),
        rotation_type=schedule["rotation_type"],
        escalation_minutes=schedule["escalation_minutes"],
    )


# ---------------------------------------------------------------------------
# POST /escalate -- escalate an incident to the secondary on-call
# ---------------------------------------------------------------------------


@router.post("/escalate", response_model=EscalateResponse, status_code=status.HTTP_201_CREATED)
async def escalate_incident(body: EscalateRequest):
    """Escalate an incident: reassign from primary to secondary on-call.

    Determines escalation level, records the event, sends notification
    to the next on-call engineer, and starts a new escalation timer.
    """
    team = body.team

    # If no team given, try to infer from the incident
    if not team:
        team = "platform"  # default fallback

    level = body.level or 1

    # Look up the current schedule
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM oncall.schedules WHERE team = %s ORDER BY created_at DESC LIMIT 1",
                    (team,),
                )
                schedule = cur.fetchone()
    except Exception as exc:
        logger.error(f"Failed to query schedule for escalation: {exc}")
        raise HTTPException(status_code=500, detail="Failed to query schedule") from exc

    if not schedule:
        raise HTTPException(status_code=404, detail=f"No schedule found for team '{team}'")

    primary_eng, secondary_eng = _compute_current_oncall(schedule)

    if not primary_eng:
        raise HTTPException(status_code=404, detail=f"No engineers configured for team '{team}'")

    # Determine escalation target based on level and policy
    from_engineer = primary_eng.email
    to_engineer = None

    if level == 1 and secondary_eng:
        to_engineer = secondary_eng.email
    elif level >= 2:
        # Escalate to manager
        to_engineer = settings.MANAGER_EMAIL
        from_engineer = secondary_eng.email if secondary_eng else primary_eng.email
    else:
        # Single engineer team — try manager as target
        to_engineer = settings.MANAGER_EMAIL

    if not to_engineer:
        raise HTTPException(
            status_code=422,
            detail=f"No secondary on-call for team '{team}' -- cannot escalate",
        )

    # Record escalation in the database
    escalation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    reason = body.reason or "No acknowledgment within escalation window"

    try:
        with get_db_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO oncall.escalations (id, incident_id, from_engineer, to_engineer, level, reason, escalated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (escalation_id, body.incident_id, from_engineer, to_engineer, level, reason, now),
                )
    except Exception as exc:
        logger.error(f"Failed to record escalation: {exc}")
        raise HTTPException(status_code=500, detail="Failed to record escalation") from exc

    # Increment Prometheus counter
    escalations_total.labels(team=team).inc()

    # Deactivate any existing escalation timer for this incident
    try:
        with get_db_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE oncall.escalation_timers SET is_active = FALSE WHERE incident_id = %s AND is_active = TRUE",
                    (body.incident_id,),
                )
    except Exception:
        pass  # Non-critical

    # Start new escalation timer for the next level
    _start_escalation_timer(body.incident_id, team, level + 1, to_engineer)

    # Send notification to the escalation target
    await _notify_engineer(
        incident_id=body.incident_id,
        engineer=to_engineer,
        message=f"[ESCALATED L{level}] Incident {body.incident_id} escalated to you. Reason: {reason}",
        team=team,
    )

    logger.info(f"Escalation L{level}: incident={body.incident_id} from={from_engineer} to={to_engineer} team={team}")

    return EscalateResponse(
        escalation_id=escalation_id,
        incident_id=body.incident_id,
        from_engineer=from_engineer,
        to_engineer=to_engineer,
        level=level,
        reason=reason,
        escalated_at=now,
    )


# ---------------------------------------------------------------------------
# GET /escalations -- list escalation history
# ---------------------------------------------------------------------------


@router.get("/escalations")
def list_escalations(
    incident_id: Optional[str] = Query(None, description="Filter by incident ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List escalation history."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if incident_id:
                    cur.execute(
                        """
                        SELECT * FROM oncall.escalations
                        WHERE incident_id = %s
                        ORDER BY escalated_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (incident_id, limit, offset),
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM oncall.escalations
                        ORDER BY escalated_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )
                rows = cur.fetchall()
    except Exception as exc:
        logger.error(f"Failed to list escalations: {exc}")
        raise HTTPException(status_code=500, detail="Failed to list escalations") from exc

    return {
        "escalations": [
            {
                "id": str(r["id"]),
                "incident_id": r["incident_id"],
                "from_engineer": r["from_engineer"],
                "to_engineer": r["to_engineer"],
                "level": r.get("level", 1),
                "reason": r.get("reason"),
                "escalated_at": r["escalated_at"].isoformat() if r["escalated_at"] else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


# ---------------------------------------------------------------------------
# Notification helper
# ---------------------------------------------------------------------------


async def _notify_engineer(incident_id: str, engineer: str, message: str, team: str):
    """Send a notification to an engineer via the Notification Service."""
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_CLIENT_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notify",
                json={
                    "incident_id": incident_id,
                    "engineer": engineer,
                    "channel": "mock",
                    "message": message,
                },
            )
            notif_status = "sent" if resp.status_code < 400 else "failed"
            escalation_notifications_total.labels(
                team=team,
                channel="mock",
                status=notif_status,
            ).inc()
            logger.info(f"Notification sent to {engineer} for {incident_id}: {notif_status}")
    except Exception as e:
        escalation_notifications_total.labels(
            team=team,
            channel="mock",
            status="failed",
        ).inc()
        logger.warning(f"Notification service unavailable for {incident_id}: {e}")


# ---------------------------------------------------------------------------
# Escalation timer helpers
# ---------------------------------------------------------------------------


def _start_escalation_timer(incident_id: str, team: str, next_level: int, assigned_to: str):
    """Create an escalation timer for the next escalation level."""
    # Look up the escalation policy to find wait time for next level
    wait_minutes = settings.DEFAULT_ESCALATION_MINUTES
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT wait_minutes FROM oncall.escalation_policies WHERE team = %s AND level = %s",
                    (team, next_level),
                )
                policy = cur.fetchone()
                if policy:
                    wait_minutes = policy["wait_minutes"]
    except Exception:
        pass  # Use default

    now = datetime.now(timezone.utc)
    escalate_after = now + timedelta(minutes=wait_minutes)

    try:
        with get_db_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO oncall.escalation_timers
                        (incident_id, team, current_level, assigned_to, escalate_after, is_active)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    """,
                    (incident_id, team, next_level, assigned_to, escalate_after),
                )
        active_escalation_timers.labels(team=team).inc()
        logger.info(f"Escalation timer set: incident={incident_id} level={next_level} at={escalate_after}")
    except Exception as e:
        logger.error(f"Failed to create escalation timer: {e}")


# ---------------------------------------------------------------------------
# POST /escalation-policies -- create/replace escalation policy
# ---------------------------------------------------------------------------


@router.post("/escalation-policies", response_model=EscalationPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_escalation_policy(body: EscalationPolicyCreateRequest):
    """Create or replace escalation policy levels for a team."""
    try:
        with get_db_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                # Delete existing policy for the team
                cur.execute("DELETE FROM oncall.escalation_policies WHERE team = %s", (body.team,))

                # Insert new levels
                for lvl in body.levels:
                    cur.execute(
                        """
                        INSERT INTO oncall.escalation_policies (team, level, wait_minutes, notify_target)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (body.team, lvl.level, lvl.wait_minutes, lvl.notify_target),
                    )
    except Exception as exc:
        logger.error(f"Failed to create escalation policy: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create escalation policy") from exc

    return EscalationPolicyResponse(team=body.team, levels=body.levels)


# ---------------------------------------------------------------------------
# GET /escalation-policies -- list all escalation policies
# ---------------------------------------------------------------------------


@router.get("/escalation-policies")
def list_escalation_policies(
    team: Optional[str] = Query(None, description="Filter by team name"),
):
    """List escalation policies, optionally filtered by team."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if team:
                    cur.execute(
                        "SELECT * FROM oncall.escalation_policies WHERE team = %s ORDER BY level",
                        (team,),
                    )
                else:
                    cur.execute("SELECT * FROM oncall.escalation_policies ORDER BY team, level")
                rows = cur.fetchall()
    except Exception as exc:
        logger.error(f"Failed to list escalation policies: {exc}")
        raise HTTPException(status_code=500, detail="Failed to list escalation policies") from exc

    # Group by team
    policies: dict = {}
    for r in rows:
        t = r["team"]
        if t not in policies:
            policies[t] = []
        policies[t].append(
            {
                "level": r["level"],
                "wait_minutes": r["wait_minutes"],
                "notify_target": r["notify_target"],
            }
        )

    return {
        "policies": [{"team": t, "levels": levels} for t, levels in policies.items()],
        "total": len(policies),
    }


# ---------------------------------------------------------------------------
# GET /escalation-policies/{team} -- get policy for a specific team
# ---------------------------------------------------------------------------


@router.get("/escalation-policies/{team}", response_model=EscalationPolicyResponse)
def get_escalation_policy(team: str):
    """Get escalation policy for a specific team."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM oncall.escalation_policies WHERE team = %s ORDER BY level",
                    (team,),
                )
                rows = cur.fetchall()
    except Exception as exc:
        logger.error(f"Failed to get escalation policy: {exc}")
        raise HTTPException(status_code=500, detail="Failed to get escalation policy") from exc

    if not rows:
        raise HTTPException(status_code=404, detail=f"No escalation policy found for team '{team}'")

    levels = [
        EscalationPolicyLevel(level=r["level"], wait_minutes=r["wait_minutes"], notify_target=r["notify_target"])
        for r in rows
    ]

    return EscalationPolicyResponse(team=team, levels=levels)


# ---------------------------------------------------------------------------
# POST /check-escalations -- automatic escalation check
# ---------------------------------------------------------------------------


@router.post("/check-escalations", response_model=AutoEscalationResult)
async def check_escalations():
    """Check for expired escalation timers and trigger automatic escalation.

    This endpoint is designed to be called periodically (e.g., every minute)
    by a cron job or scheduler. It finds all active timers whose
    `escalate_after` timestamp has passed, and triggers escalation for each.
    """
    auto_escalation_runs_total.inc()
    now = datetime.now(timezone.utc)
    details = []

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, incident_id, team, current_level, assigned_to
                    FROM oncall.escalation_timers
                    WHERE is_active = TRUE AND escalate_after <= %s
                    ORDER BY escalate_after
                    """,
                    (now,),
                )
                expired_timers = cur.fetchall()
    except Exception as exc:
        logger.error(f"Failed to check escalation timers: {exc}")
        raise HTTPException(status_code=500, detail="Failed to check escalation timers") from exc

    escalated_count = 0

    for timer in expired_timers:
        timer_id = str(timer["id"])
        incident_id = timer["incident_id"]
        team = timer["team"]
        current_level = timer["current_level"]

        # Check if incident is still unacknowledged
        incident_status = None
        try:
            async with httpx.AsyncClient(timeout=settings.HTTP_CLIENT_TIMEOUT) as client:
                resp = await client.get(
                    f"{settings.INCIDENT_SERVICE_URL}/api/v1/incidents/{incident_id}",
                )
                if resp.status_code == 200:
                    incident_data = resp.json()
                    incident_status = incident_data.get("status")
        except Exception as e:
            logger.warning(f"Could not check incident {incident_id} status: {e}")

        # If incident is already acknowledged or resolved, deactivate the timer
        if incident_status in ("acknowledged", "in_progress", "resolved", "closed", "mitigated"):
            try:
                with get_db_connection(autocommit=True) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE oncall.escalation_timers SET is_active = FALSE WHERE id = %s",
                            (timer_id,),
                        )
                active_escalation_timers.labels(team=team).dec()
            except Exception:
                pass
            details.append(
                {
                    "incident_id": incident_id,
                    "action": "skipped",
                    "reason": f"Incident already {incident_status}",
                }
            )
            continue

        # Look up the schedule for the team
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM oncall.schedules WHERE team = %s ORDER BY created_at DESC LIMIT 1",
                        (team,),
                    )
                    schedule = cur.fetchone()
        except Exception:
            schedule = None

        if not schedule:
            details.append({"incident_id": incident_id, "action": "skipped", "reason": "No schedule found"})
            continue

        primary_eng, secondary_eng = _compute_current_oncall(schedule)
        from_engineer = timer["assigned_to"]

        # Determine next target based on policy
        to_engineer = None
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT notify_target FROM oncall.escalation_policies WHERE team = %s AND level = %s",
                        (team, current_level),
                    )
                    policy_row = cur.fetchone()
        except Exception:
            policy_row = None

        if policy_row:
            target = policy_row["notify_target"]
            if target == "secondary" and secondary_eng:
                to_engineer = secondary_eng.email
            elif target == "manager":
                to_engineer = settings.MANAGER_EMAIL
            else:
                to_engineer = target  # Direct email
        elif secondary_eng and current_level == 1:
            to_engineer = secondary_eng.email
        else:
            to_engineer = settings.MANAGER_EMAIL

        # Record escalation
        escalation_id = str(uuid.uuid4())
        reason = f"Auto-escalation: no acknowledgment within escalation window (level {current_level})"

        try:
            with get_db_connection(autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO oncall.escalations (id, incident_id, from_engineer, to_engineer, level, reason, escalated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (escalation_id, incident_id, from_engineer, to_engineer, current_level, reason, now),
                    )
                    # Deactivate this timer
                    cur.execute(
                        "UPDATE oncall.escalation_timers SET is_active = FALSE WHERE id = %s",
                        (timer_id,),
                    )
        except Exception as e:
            logger.error(f"Failed to record auto-escalation for {incident_id}: {e}")
            continue

        escalations_total.labels(team=team).inc()
        active_escalation_timers.labels(team=team).dec()

        # Start next-level timer if within loop count
        max_level = settings.ESCALATION_LOOP_COUNT + 1
        if current_level < max_level:
            _start_escalation_timer(incident_id, team, current_level + 1, to_engineer)

        # Send notification
        await _notify_engineer(
            incident_id=incident_id,
            engineer=to_engineer,
            message=f"[AUTO-ESCALATED L{current_level}] Incident {incident_id} escalated to you. "
            f"Previous assignee ({from_engineer}) did not acknowledge.",
            team=team,
        )

        escalated_count += 1
        details.append(
            {
                "incident_id": incident_id,
                "action": "escalated",
                "level": current_level,
                "from": from_engineer,
                "to": to_engineer,
            }
        )

    return AutoEscalationResult(
        checked=len(expired_timers),
        escalated=escalated_count,
        details=details,
    )


# ---------------------------------------------------------------------------
# GET /metrics/oncall -- key on-call metrics
# ---------------------------------------------------------------------------


@router.get("/metrics/oncall", response_model=OnCallMetrics)
def get_oncall_metrics():
    """Return key on-call metrics: MTTA, MTTR, escalation rate, on-call load."""
    metrics: dict = {
        "total_incidents": 0,
        "total_escalations": 0,
        "escalation_rate_pct": None,
        "avg_mtta_seconds": None,
        "avg_mttr_seconds": None,
        "oncall_load": {},
        "by_team": {},
    }

    # Escalation counts by team
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total escalations
                cur.execute("SELECT COUNT(*) AS cnt FROM oncall.escalations")
                metrics["total_escalations"] = cur.fetchone()["cnt"]

                # Escalations by team (inferred from schedules + from_engineer)
                cur.execute("""
                    SELECT s.team, COUNT(e.id) AS cnt
                    FROM oncall.escalations e
                    LEFT JOIN oncall.schedules s ON s.team = (
                        SELECT s2.team FROM oncall.schedules s2
                        WHERE s2.engineers::text LIKE '%%' || e.from_engineer || '%%'
                        LIMIT 1
                    )
                    GROUP BY s.team
                """)
                for r in cur.fetchall():
                    if r["team"]:
                        metrics["by_team"][r["team"]] = r["cnt"]
    except Exception as e:
        logger.warning(f"Failed to query escalation metrics: {e}")

    # Incident metrics from incident-management service (cross-service query)
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) AS total,
                        AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at)))
                            FILTER (WHERE acknowledged_at IS NOT NULL) AS avg_mtta,
                        AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)))
                            FILTER (WHERE resolved_at IS NOT NULL) AS avg_mttr
                    FROM incidents.incidents
                """)
                row = cur.fetchone()
                if row:
                    metrics["total_incidents"] = row["total"]
                    if row["avg_mtta"]:
                        metrics["avg_mtta_seconds"] = round(row["avg_mtta"], 2)
                    if row["avg_mttr"]:
                        metrics["avg_mttr_seconds"] = round(row["avg_mttr"], 2)

                # Escalation rate
                if row and row["total"] > 0:
                    rate = (metrics["total_escalations"] / row["total"]) * 100
                    metrics["escalation_rate_pct"] = round(rate, 2)
                    escalation_rate.set(rate)

                # On-call load (incidents assigned per engineer this week)
                cur.execute("""
                    SELECT assigned_to::text, COUNT(*) AS cnt
                    FROM incidents.incidents
                    WHERE created_at >= now() - interval '7 days'
                      AND assigned_to IS NOT NULL
                    GROUP BY assigned_to
                """)
                for r in cur.fetchall():
                    if r["assigned_to"]:
                        metrics["oncall_load"][r["assigned_to"]] = r["cnt"]
    except Exception as e:
        logger.warning(f"Failed to query incident metrics: {e}")

    return OnCallMetrics(**metrics)
