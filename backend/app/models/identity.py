import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return uuid.uuid4().hex


class Household(Base):
    __tablename__ = "households"
    __table_args__ = (
        ForeignKeyConstraint(
            ["owner_id", "id"], ["users.id", "users.household_id"],
            name="fk_households_owner_membership", deferrable=True, initially="DEFERRED",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    currency_code: Mapped[str] = mapped_column(String(3), default="MXN")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    owner_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    members: Mapped[list["User"]] = relationship(back_populates="household", foreign_keys="User.household_id")
    accounts: Mapped[list["Account"]] = relationship(back_populates="household")
    categories: Mapped[list["Category"]] = relationship(back_populates="household")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("id", "household_id", name="uq_users_id_household_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email_verified: Mapped[bool] = mapped_column(default=False, server_default="false")
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    household_id: Mapped[str | None] = mapped_column(ForeignKey("households.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    household: Mapped[Household | None] = relationship(back_populates="members", foreign_keys=[household_id])


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"))
    token: Mapped[str] = mapped_column(String(64), unique=True, default=new_id)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RefreshToken(Base):
    """Revocable backing row for a signed access token.

    Every token the app signs carries a unique ``jti``; this table records
    its window (``expires_at`` = issuance + ``refresh_token_expiry_days``) and
    whether it was revoked. Revocation is a flag, never a delete, so a
    ``remove_member``/``change_password`` can void every outstanding token of
    a user in one update.

    Tokens signed *without* a ``jti`` (pre-deploy 30-day tokens, test fixtures)
    have no row here: ``get_current_user`` treats them as legacy and only
    checks the JWT itself — see the note in ``app.api.deps``.
    """

    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship()
