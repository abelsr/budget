from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import or_, select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Alert, RecurringRule, User
from app.schemas.alerts import AlertGenerateResult, AlertOut, AlertRead
from app.services.alerts import generate_alerts
from app.services.recurring import materialize_due

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _out(alert: Alert) -> AlertOut:
    return AlertOut(id=alert.id, kind=alert.kind, message=alert.message, payload=alert.payload, read_at=alert.read_at, created_at=alert.created_at)


def _visible_alert(db, household_id: str, user_id: str, alert_id: str) -> Alert:
    alert = db.scalar(select(Alert).where(
        Alert.id == alert_id, Alert.household_id == household_id,
        or_(Alert.user_id.is_(None), Alert.user_id == user_id),
    ))
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return alert


@router.get("")
def list_alerts(db: DbDep, user: CurrentUserDep) -> list[AlertOut]:
    household_id = _household_id(user)
    generate_alerts(db, household_id)
    alerts = db.scalars(select(Alert).where(
        Alert.household_id == household_id,
        or_(Alert.user_id.is_(None), Alert.user_id == user.id),
    ).order_by(Alert.read_at.is_not(None), Alert.created_at.desc())).all()
    return [_out(alert) for alert in alerts]


@router.post("/read")
def read_alerts(payload: AlertRead, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if payload.alert_id is not None:
        _visible_alert(db, household_id, user.id, payload.alert_id).read_at = now
    else:
        alerts = db.scalars(select(Alert).where(
            Alert.household_id == household_id, Alert.read_at.is_(None),
            or_(Alert.user_id.is_(None), Alert.user_id == user.id),
        )).all()
        for alert in alerts:
            alert.read_at = now
    db.commit()


@router.post("/{alert_id}/generate", response_model=AlertGenerateResult)
def generate_recurring_alert(alert_id: str, db: DbDep, user: CurrentUserDep) -> AlertGenerateResult:
    household_id = _household_id(user)
    alert = _visible_alert(db, household_id, user.id, alert_id)
    if alert.kind != "recurring_overdue":
        raise HTTPException(status_code=422, detail="Esta alerta no puede generar movimientos")
    rule_id = alert.payload.get("recurring_rule_id")
    if not isinstance(rule_id, str) or db.get(RecurringRule, rule_id) is None:
        raise HTTPException(status_code=409, detail="La regla ya no existe")
    generated = materialize_due(db, household_id, user.id)
    alert.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return AlertGenerateResult(generated=generated)
