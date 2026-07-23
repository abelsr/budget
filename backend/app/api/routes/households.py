from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Household, Invitation, User
from app.schemas.households import (
    HouseholdResponse,
    InvitationResponse,
    MemberResponse,
)

router = APIRouter(prefix="/households", tags=["households"])

INVITATION_TTL_DAYS = 7


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _require_household(db: DbDep, user: User) -> Household:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    household = db.get(Household, user.household_id)
    if household is None:  # defensivo: la FK debería garantizarlo
        raise HTTPException(status_code=400, detail="Hogar no encontrado")
    return household


@router.get("/me", response_model=HouseholdResponse)
def get_my_household(db: DbDep, user: CurrentUserDep) -> Household:
    return _require_household(db, user)


@router.get("/me/members", response_model=list[MemberResponse])
def get_my_household_members(db: DbDep, user: CurrentUserDep) -> list[User]:
    household = _require_household(db, user)
    return list(db.scalars(select(User).where(User.household_id == household.id)))


@router.post("/me/invitations", response_model=InvitationResponse, status_code=201)
def create_invitation(db: DbDep, user: CurrentUserDep) -> InvitationResponse:
    household = _require_household(db, user)
    invitation = Invitation(
        household_id=household.id,
        created_by_id=user.id,
        expires_at=_now() + timedelta(days=INVITATION_TTL_DAYS),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return InvitationResponse(
        token=invitation.token,
        invite_url=f"/login?invite={invitation.token}",
        expires_at=invitation.expires_at,
    )
