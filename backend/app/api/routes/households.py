from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DbDep
from app.config import settings
from app.core.security import revoke_user_refresh_tokens
from app.models import Account, Household, Invitation, User
from app.schemas.households import (
    ActiveInvitationResponse,
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


def _require_owner(db: DbDep, user: User) -> Household:
    household = _require_household(db, user)
    if household.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Solo la persona propietaria puede administrar el hogar")
    return household


@router.get("/me", response_model=HouseholdResponse)
def get_my_household(db: DbDep, user: CurrentUserDep) -> HouseholdResponse:
    household = _require_household(db, user)
    return HouseholdResponse(
        id=household.id,
        name=household.name,
        currency_code=household.currency_code,
        is_owner=household.owner_id == user.id,
    )


@router.get("/me/members", response_model=list[MemberResponse])
def get_my_household_members(db: DbDep, user: CurrentUserDep) -> list[MemberResponse]:
    household = _require_household(db, user)
    members = db.scalars(
        select(User)
        .where(User.household_id == household.id)
        .order_by(User.id != household.owner_id, User.name, User.id)
    ).all()
    return [
        MemberResponse(
            id=member.id,
            name=member.name,
            email=member.email,
            is_owner=member.id == household.owner_id,
        )
        for member in members
    ]


@router.post("/me/invitations", response_model=InvitationResponse, status_code=201)
def create_invitation(db: DbDep, user: CurrentUserDep) -> InvitationResponse:
    household = db.scalar(
        select(Household)
        .where(Household.id == user.household_id, Household.owner_id == user.id)
        .with_for_update()
    )
    if household is None:
        _require_owner(db, user)
        raise HTTPException(status_code=404, detail="Hogar no encontrado")
    active_count = db.scalar(
        select(func.count(Invitation.id)).where(
            Invitation.household_id == household.id,
            Invitation.used_at.is_(None),
            Invitation.expires_at > _now(),
        )
    )
    if active_count >= settings.max_active_invitations_per_household:
        raise HTTPException(status_code=409, detail="Este hogar alcanzó el máximo de invitaciones activas")
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


@router.get("/me/invitations", response_model=list[ActiveInvitationResponse])
def list_active_invitations(
    db: DbDep, user: CurrentUserDep
) -> list[ActiveInvitationResponse]:
    household = _require_owner(db, user)
    invitations = db.scalars(
        select(Invitation)
        .where(
            Invitation.household_id == household.id,
            Invitation.used_at.is_(None),
            Invitation.expires_at > _now(),
        )
        .order_by(Invitation.created_at.desc(), Invitation.id)
    ).all()
    return [
        ActiveInvitationResponse(
            id=invitation.id,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
        )
        for invitation in invitations
    ]


@router.delete("/me/invitations/{invitation_id}", status_code=204)
def revoke_invitation(invitation_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household = _require_owner(db, user)
    invitation = db.scalar(
        select(Invitation)
        .where(
            Invitation.id == invitation_id,
            Invitation.household_id == household.id,
        )
        .with_for_update()
    )
    if (
        invitation is None
        or invitation.used_at is not None
        or invitation.expires_at <= _now()
    ):
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    db.delete(invitation)
    db.commit()


@router.delete("/me/members/{member_id}", status_code=204)
def remove_member(member_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household = _require_owner(db, user)
    # Serializa expulsiones concurrentes sobre esta fila mientras se verifica y
    # se desasocia la membresía; no bloquea las demás solicitudes autenticadas.
    member = db.scalar(
        select(User)
        .where(User.id == member_id, User.household_id == household.id)
        .with_for_update()
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")
    if member.id == household.owner_id:
        raise HTTPException(status_code=409, detail="La persona propietaria no puede eliminarse del hogar")
    if db.scalar(select(Account.id).where(Account.owner_id == member.id).limit(1)):
        raise HTTPException(status_code=409, detail="No se puede expulsar a una persona con cuentas personales")
    # An expelled member's sessions die with the expulsion: their tokens are
    # revoked so a stolen/expelled credential stops working immediately.
    revoke_user_refresh_tokens(db, member.id)
    member.household_id = None
    db.commit()
