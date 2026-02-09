import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_db_connection
from app.metrics import escalations_total, oncall_current
from app.models import (
    CurrentOnCallResponse,
    Engineer,
    EscalateRequest,
    EscalateResponse,
    OnCallEngineer,
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
        import json

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
                        __import__("json").dumps(engineers_json),
                        body.escalation_minutes,
                    ),
                )
                row = cur.fetchone()
    except Exception as exc:
        logger.error(f"Failed to create schedule: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create schedule") from exc

    engineers_data = row["engineers"]
    if isinstance(engineers_data, str):
        engineers_data = __import__("json").loads(engineers_data)

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
            engineers_data = __import__("json").loads(engineers_data)
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
def escalate_incident(body: EscalateRequest):
    """Escalate an incident: reassign from primary to secondary on-call."""
    team = body.team

    # If no team given, try to infer from the incident
    if not team:
        team = "platform"  # default fallback

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

    if not secondary_eng:
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
                    INSERT INTO oncall.escalations (id, incident_id, from_engineer, to_engineer, reason, escalated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (escalation_id, body.incident_id, primary_eng.email, secondary_eng.email, reason, now),
                )
    except Exception as exc:
        logger.error(f"Failed to record escalation: {exc}")
        raise HTTPException(status_code=500, detail="Failed to record escalation") from exc

    # Increment Prometheus counter
    escalations_total.labels(team=team).inc()

    logger.info(
        f"Escalation: incident={body.incident_id} from={primary_eng.email} to={secondary_eng.email} team={team}"
    )

    return EscalateResponse(
        escalation_id=escalation_id,
        incident_id=body.incident_id,
        from_engineer=primary_eng.email,
        to_engineer=secondary_eng.email,
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
                "reason": r.get("reason"),
                "escalated_at": r["escalated_at"].isoformat() if r["escalated_at"] else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }
