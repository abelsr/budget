from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from app.api.deps import CurrentUserDep, DbDep
from app.models import Category
from app.schemas.tickets import TicketScanResponse
from app.services.vision import (
    TicketScanError,
    TicketScanUnavailable,
    analyze_ticket,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/scan", response_model=TicketScanResponse)
def scan_ticket(
    db: DbDep,
    current_user: CurrentUserDep,
    file: Annotated[UploadFile, File(...)],
) -> TicketScanResponse:
    if current_user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no tiene hogar")

    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=415, detail="El archivo debe ser una imagen"
        )

    image_bytes = file.file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413, detail="La imagen excede el límite de 10 MB"
        )

    categories = db.scalars(
        select(Category).where(
            Category.household_id == current_user.household_id,
            Category.type == "expense",
            Category.active.is_(True),
        )
    ).all()
    if not categories:
        raise HTTPException(
            status_code=400,
            detail="No hay categorías de gasto activas en el hogar",
        )
    category_dicts = [{"id": c.id, "name": c.name} for c in categories]

    try:
        result = analyze_ticket(image_bytes, file.content_type, category_dicts)
    except TicketScanUnavailable:
        raise HTTPException(
            status_code=501,
            detail="Escáner no configurado: falta GEMINI_API_KEY",
        ) from None
    except TicketScanError:
        raise HTTPException(
            status_code=502, detail="Error al analizar el ticket"
        ) from None

    return TicketScanResponse(**result)
