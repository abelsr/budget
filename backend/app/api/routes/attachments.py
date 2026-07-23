from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import CurrentUserDep, DbDep
from app.config import settings
from app.models import Attachment, Transaction, User
from app.schemas.attachments import AttachmentResponse

router = APIRouter(tags=["attachments"])

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXACT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _get_attachment(db, household_id: str, attachment_id: str) -> Attachment:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None or attachment.household_id != household_id:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return attachment


@router.post("/transactions/{transaction_id}/attachments", status_code=201)
def upload_attachment(
    transaction_id: str,
    db: DbDep,
    user: CurrentUserDep,
    file: Annotated[UploadFile, File(...)],
) -> AttachmentResponse:
    household_id = _household_id(user)
    tx = db.get(Transaction, transaction_id)
    if tx is None or tx.household_id != household_id:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    content_type = file.content_type or ""
    if not (content_type.startswith("image/") or content_type in ALLOWED_EXACT_TYPES):
        raise HTTPException(status_code=415, detail="Tipo de archivo no permitido")

    content = file.file.read()
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="El archivo excede el límite de 10 MB")

    attachment = Attachment(
        transaction_id=tx.id,
        household_id=household_id,
        filename=file.filename or "archivo",
        content_type=content_type,
        size_bytes=len(content),
        storage_path="",
    )
    db.add(attachment)
    db.flush()  # genera attachment.id

    suffix = Path(attachment.filename).suffix
    directory = Path(settings.attachments_dir) / household_id
    directory.mkdir(parents=True, exist_ok=True)
    storage_path = directory / f"{attachment.id}{suffix}"
    storage_path.write_bytes(content)
    attachment.storage_path = str(storage_path)

    db.commit()
    db.refresh(attachment)
    return AttachmentResponse.model_validate(attachment)


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: str, db: DbDep, user: CurrentUserDep
) -> FileResponse:
    household_id = _household_id(user)
    attachment = _get_attachment(db, household_id, attachment_id)
    path = Path(attachment.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return FileResponse(
        path, media_type=attachment.content_type, filename=attachment.filename
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: str, db: DbDep, user: CurrentUserDep) -> None:
    household_id = _household_id(user)
    attachment = _get_attachment(db, household_id, attachment_id)
    Path(attachment.storage_path).unlink(missing_ok=True)
    db.delete(attachment)
    db.commit()
