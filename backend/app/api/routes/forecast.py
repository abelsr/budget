from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUserDep, DbDep
from app.models import User
from app.schemas.forecast import ForecastPoint, ForecastResponse, ForecastUpcoming
from app.services.forecast import build_forecast
from app.services.recurring import materialize_due

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("", response_model=ForecastResponse)
def get_forecast(
    db: DbDep,
    user: CurrentUserDep,
    days: Annotated[int, Query(ge=14, le=180)] = 90,
) -> ForecastResponse:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")

    # Convención de todos los endpoints de lectura: materializar antes de leer,
    # para que el opening balance no falte ninguna ocurrencia vencida.
    materialize_due(db, user.household_id, user.id)
    result = build_forecast(db, user.household_id, date.today(), days)
    return ForecastResponse(
        as_of=result.as_of,
        days=result.days,
        opening_balance=result.opening_balance,
        balance=[
            ForecastPoint(
                date=point.date,
                income=point.income,
                expense=point.expense,
                delta=point.delta,
                balance=point.balance,
            )
            for point in result.points
        ],
        upcoming=[
            ForecastUpcoming(
                date=event.date,
                type=event.type,
                amount=event.amount,
                label=event.label,
                source=event.source,
            )
            for event in result.upcoming
        ],
    )
