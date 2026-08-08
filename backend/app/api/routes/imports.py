import csv
import hashlib
import io
import json
import os
import re
from threading import Lock
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUserDep, DbDep
from app.models import (
    Account,
    Category,
    Household,
    ImportBatch,
    ImportFingerprint,
    ImportRow,
    MerchantRule,
    Transaction,
    TransactionEditEvent,
    User,
)
from app.services.reconciliation import invalidate_completed_reconciliation
from app.schemas.imports import (
    DateFormat,
    ImportBatchDetailOut,
    ImportBatchOut,
    ImportCommitOut,
    ImportMapping,
    ImportPreviewOut,
    ImportPreviewRow,
    ImportRevertConflict,
    ImportRevertConflictOut,
    ImportRevertConflictResponse,
    ImportRowOut,
    ImportTransactionStateOut,
    TransactionEditEventOut,
)
from app.services.account_access import can_operate, visible_accounts
from app.services.categorization import matching_category_id

router = APIRouter(prefix="/import", tags=["import"])

_MAX_BYTES = 5 * 1024 * 1024
_MAX_ROWS = 1_000
_MAX_HEADERS = 30
_MAX_HEADER_LENGTH = 120
_MAX_FIELD_LENGTH = 10_000
_MONEY_SCALE = Decimal("0.0001")
_WHITESPACE = re.compile(r"\s+")
_CURRENCY = re.compile(r"[^0-9,().+-]")
_CSV_FIELD_LIMIT_LOCK = Lock()


def _household_id(user: User) -> str:
    if user.household_id is None:
        raise HTTPException(status_code=400, detail="El usuario no pertenece a un hogar")
    return user.household_id


def _csv_error() -> HTTPException:
    # Parsing failures deliberately never expose statement fields or parser details.
    return HTTPException(status_code=422, detail="CSV inválido")


def _account(db, household_id: str, user_id: str, account_id: str) -> Account:
    account = db.get(Account, account_id)
    if account is None or account.household_id != household_id or not can_operate(account, user_id):
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return account


async def _file_bytes(file: UploadFile) -> bytes:
    content = await file.read(_MAX_BYTES + 1)
    if len(content) > _MAX_BYTES:
        raise _csv_error()
    return content


def _normalize_header(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip()).casefold()


def _suggest_mapping(headers: list[str]) -> ImportMapping:
    def match(*terms: str) -> str | None:
        for header in headers:
            name = _normalize_header(header)
            if name in terms or any(term in name for term in terms):
                return header
        return None

    date_header = match("date", "fecha")
    amount_header = match("amount", "importe", "monto", "cantidad", "valor", "debit", "credit")
    description_header = match("description", "descripcion", "descripción", "concepto", "detalle", "note", "memo")
    if not date_header or not amount_header or not description_header:
        raise _csv_error()
    return ImportMapping(date=date_header, amount=amount_header, description=description_header)


def _parse_mapping(raw: str | None, headers: list[str]) -> ImportMapping:
    if raw is None:
        return _suggest_mapping(headers)
    try:
        mapping = ImportMapping.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValueError):
        raise _csv_error() from None
    if len({mapping.date, mapping.amount, mapping.description}) != 3 or any(
        field not in headers for field in (mapping.date, mapping.amount, mapping.description)
    ):
        raise _csv_error()
    return mapping


def _parse_date(value: str, date_format: DateFormat) -> date:
    try:
        return datetime.strptime(
            value.strip(), "%d/%m/%Y" if date_format == "DD/MM/YYYY" else "%m/%d/%Y"
        ).date()
    except ValueError:
        raise _csv_error() from None


def _detect_date_format(value: str) -> DateFormat:
    parts = value.strip().split("/")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise _csv_error()
    first, second = int(parts[0]), int(parts[1])
    if first > 12:
        return "DD/MM/YYYY"
    if second > 12:
        return "MM/DD/YYYY"
    return "DD/MM/YYYY"


def _parse_money(value: str) -> Decimal:
    text = value.strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = _CURRENCY.sub("", text).replace(" ", "")
    if not text or text.count("-") > 1 or ("-" in text and not text.startswith("-")):
        raise _csv_error()
    comma, dot = text.rfind(","), text.rfind(".")
    if comma != -1 and dot != -1:
        decimal_at = max(comma, dot)
        decimal = text[decimal_at]
        text = text.replace("," if decimal == "." else ".", "").replace(decimal, ".")
    elif comma != -1 or dot != -1:
        separator = "," if comma != -1 else "."
        before, after = text.rsplit(separator, 1)
        # A three-digit tail is normally a thousands group (1,234 / 1.234).
        text = before + after if len(after) == 3 else before + "." + after
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise _csv_error() from None
    if negative:
        amount = -amount
    if not amount.is_finite() or amount == 0:
        raise _csv_error()
    return amount.quantize(_MONEY_SCALE, rounding=ROUND_HALF_UP)


def _parse_csv(content: bytes, mapping_raw: str | None, date_format_raw: str | None) -> tuple[list[str], ImportMapping, DateFormat, list[dict]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise _csv_error() from None
    try:
        # csv.field_size_limit is process-global, so don't let another request
        # change the parser bound while this file is being read.
        with _CSV_FIELD_LIMIT_LOCK:
            previous_limit = csv.field_size_limit(_MAX_FIELD_LENGTH)
            try:
                reader = csv.reader(io.StringIO(text, newline=""), strict=True)
                headers = next(reader)
                if not headers or len(headers) > _MAX_HEADERS or any(
                    not header.strip() or len(header) > _MAX_HEADER_LENGTH for header in headers
                ) or len({_normalize_header(header) for header in headers}) != len(headers):
                    raise _csv_error()
                mapping = _parse_mapping(mapping_raw, headers)
                raw_rows = list(reader)
            finally:
                csv.field_size_limit(previous_limit)
    except (csv.Error, StopIteration):
        raise _csv_error() from None
    if not raw_rows or len(raw_rows) > _MAX_ROWS:
        raise _csv_error()
    if any(len(row) != len(headers) or not any(field.strip() for field in row) for row in raw_rows):
        raise _csv_error()
    date_format: DateFormat
    if date_format_raw is None:
        date_format = _detect_date_format(raw_rows[0][headers.index(mapping.date)])
    elif date_format_raw in ("DD/MM/YYYY", "MM/DD/YYYY"):
        date_format = date_format_raw
    else:
        raise _csv_error()
    rows = []
    for position, raw in enumerate(raw_rows, start=1):
        source = dict(zip(headers, raw, strict=True))
        description = _WHITESPACE.sub(" ", source[mapping.description].strip()) or None
        rows.append({
            "position": position,
            "source": source,
            "date": _parse_date(source[mapping.date], date_format),
            "amount": _parse_money(source[mapping.amount]),
            "description": description,
        })
    return headers, mapping, date_format, rows


def _fingerprint(row: dict) -> str:
    canonical = f"{row['date'].isoformat()}|{row['amount']:.4f}|{row['description'] or ''}"
    return hashlib.sha256(canonical.encode()).hexdigest()


def _canonical_amount(value: Decimal | str | float) -> str:
    return f"{Decimal(str(value)).quantize(_MONEY_SCALE):.4f}"


def _direct_duplicate(db, household_id: str, user_id: str, row: dict) -> bool:
    # A direct warning must never reveal a peer's personal-account activity.
    direct = db.scalars(select(Transaction).join(Account).where(
        Transaction.household_id == household_id,
        Transaction.deleted_at.is_(None),
        Transaction.date == row["date"],
        func.abs(Transaction.amount) == abs(row["amount"]),
        visible_accounts(user_id),
    )).all()
    return any(
        _WHITESPACE.sub(" ", (tx.note or "").strip()) == (row["description"] or "")
        for tx in direct
    )


def _advisory_reasons(
    db, household_id: str, user_id: str, account_id: str, row: dict, file_fingerprints: set[str]
) -> list[str]:
    fingerprint = _fingerprint(row)
    reasons = []
    if fingerprint in file_fingerprints:
        reasons.append("file")
    file_fingerprints.add(fingerprint)
    if db.scalar(select(ImportFingerprint.id).where(
        ImportFingerprint.household_id == household_id,
        ImportFingerprint.account_id == account_id,
        ImportFingerprint.fingerprint == fingerprint,
    ).limit(1)) is not None:
        reasons.append("fingerprint")
    if _direct_duplicate(db, household_id, user_id, row):
        reasons.append("household")
    return reasons


def _preview_rows(db, household_id: str, user_id: str, account_id: str, rows: list[dict]) -> list[ImportPreviewRow]:
    file_fingerprints: set[str] = set()
    result = []
    for row in rows:
        reasons = _advisory_reasons(
            db, household_id, user_id, account_id, row, file_fingerprints
        )
        result.append(ImportPreviewRow(
            source_position=row["position"], date=row["date"], amount=float(row["amount"]),
            description=row["description"], duplicate_reasons=reasons, selected=not reasons,
        ))
    return result


def _batch_out(batch: ImportBatch) -> ImportBatchOut:
    return ImportBatchOut(
        id=batch.id, account_id=batch.account_id, source_filename=batch.source_filename,
        mapping=batch.mapping, selected_count=batch.selected_count, imported_count=batch.imported_count,
        skipped_count=batch.skipped_count, created_at=batch.created_at,
    )


def _get_batch(db, household_id: str, user_id: str, batch_id: str) -> ImportBatch:
    batch = db.get(ImportBatch, batch_id)
    if batch is None or batch.household_id != household_id:
        raise HTTPException(status_code=404, detail="Importación no encontrada")
    _account(db, household_id, user_id, batch.account_id)
    return batch


@router.post("/preview")
async def preview_import(
    db: DbDep,
    user: CurrentUserDep,
    file: Annotated[UploadFile, File()],
    account_id: Annotated[str, Form(alias="accountId")],
    mapping: Annotated[str | None, Form()] = None,
    date_format: Annotated[str | None, Form(alias="dateFormat")] = None,
) -> ImportPreviewOut:
    household_id = _household_id(user)
    _account(db, household_id, user.id, account_id)
    headers, parsed_mapping, parsed_format, rows = _parse_csv(await _file_bytes(file), mapping, date_format)
    return ImportPreviewOut(
        headers=headers, suggested_mapping=_suggest_mapping(headers), mapping=parsed_mapping,
        date_format=parsed_format, rows=_preview_rows(db, household_id, user.id, account_id, rows),
    )


@router.post("/commit", status_code=201)
async def commit_import(
    db: DbDep,
    user: CurrentUserDep,
    file: Annotated[UploadFile, File()],
    account_id: Annotated[str, Form(alias="accountId")],
    mapping: Annotated[str, Form()],
    date_format: Annotated[str, Form(alias="dateFormat")],
    selected_positions: Annotated[str, Form(alias="selectedPositions")],
) -> ImportCommitOut:
    household_id = _household_id(user)
    _account(db, household_id, user.id, account_id)
    _headers, parsed_mapping, parsed_format, rows = _parse_csv(
        await _file_bytes(file), mapping, date_format
    )
    try:
        selected = json.loads(selected_positions)
        if not isinstance(selected, list) or not selected or any(type(item) is not int for item in selected):
            raise ValueError
        selected_set = set(selected)
    except (json.JSONDecodeError, ValueError):
        raise _csv_error() from None
    by_position = {row["position"]: row for row in rows}
    if len(selected_set) != len(selected) or not selected_set.issubset(by_position):
        raise _csv_error()
    chosen = [by_position[position] for position in selected]
    filename = os.path.basename(file.filename or "statement.csv")[:255] or "statement.csv"
    try:
        # This lock serializes per-household category provisioning on PostgreSQL.
        db.scalar(select(Household).where(Household.id == household_id).with_for_update())
        categories = {}
        for tx_type in ("expense", "income"):
            category = db.scalar(select(Category).where(
                Category.household_id == household_id, Category.type == tx_type,
                Category.name == "Unclassified", Category.active.is_(True), Category.deleted.is_(False),
            ))
            if category is None:
                category = Category(
                    household_id=household_id, name="Unclassified", type=tx_type,
                    icon="tag", color="#6b7280",
                )
                db.add(category)
                db.flush()
            categories[tx_type] = category
        merchant_rules = db.scalars(
            select(MerchantRule).join(Category).where(
                MerchantRule.household_id == household_id,
                Category.active.is_(True),
                Category.deleted.is_(False),
            )
        ).all()
        batch = ImportBatch(
            household_id=household_id, account_id=account_id, created_by_id=user.id,
            source_filename=filename, mapping=parsed_mapping.model_dump(by_alias=True),
            selected_count=len(chosen), imported_count=0, skipped_count=0,
        )
        db.add(batch)
        db.flush()
        file_fingerprints: set[str] = set()
        for row in chosen:
            tx_type = "income" if row["amount"] > 0 else "expense"
            amount = abs(row["amount"])
            category_id = matching_category_id(merchant_rules, row["description"], tx_type) or categories[tx_type].id
            baseline = {
                "type": tx_type, "amount": _canonical_amount(amount), "category_id": category_id,
                "account_id": account_id, "date": row["date"].isoformat(), "note": row["description"],
            }
            advisory_reasons = _advisory_reasons(
                db, household_id, user.id, account_id, row, file_fingerprints
            )
            import_row = ImportRow(
                batch_id=batch.id, source_position=row["position"], source_snapshot=row["source"],
                transaction_baseline=baseline, advisory_reasons=advisory_reasons,
                status="skipped", transaction_id=None,
            )
            db.add(import_row)
            db.flush()
            fingerprint = _fingerprint(row)
            if db.scalar(select(ImportFingerprint.id).where(
                ImportFingerprint.household_id == household_id, ImportFingerprint.account_id == account_id,
                ImportFingerprint.fingerprint == fingerprint,
            ).limit(1)) is not None:
                import_row.status = "skipped_fingerprint"
                batch.skipped_count += 1
                continue
            try:
                with db.begin_nested():
                    transaction = Transaction(
                        household_id=household_id, type=tx_type, amount=amount,
                        category_id=category_id, account_id=account_id, member_id=user.id,
                        date=row["date"], note=row["description"], import_batch_id=batch.id,
                    )
                    db.add(transaction)
                    db.flush()
                    import_row.transaction_id = transaction.id
                    import_row.status = "imported"
                    # The fingerprint's composite FK includes this row's transaction link.
                    db.flush()
                    db.add(ImportFingerprint(
                        batch_id=batch.id, household_id=household_id, account_id=account_id,
                        fingerprint=fingerprint, import_row_id=import_row.id, transaction_id=transaction.id,
                    ))
                    db.flush()
                batch.imported_count += 1
            except IntegrityError:
                # A concurrent fingerprint winner is an advisory skip, not a failed batch.
                import_row.status = "skipped_fingerprint"
                import_row.transaction_id = None
                if "fingerprint" not in import_row.advisory_reasons:
                    import_row.advisory_reasons = [*import_row.advisory_reasons, "fingerprint"]
                batch.skipped_count += 1
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(batch)
    return ImportCommitOut(
        batch=_batch_out(batch), selected_count=batch.selected_count,
        imported_count=batch.imported_count, skipped_count=batch.skipped_count,
    )


@router.get("/batches")
def list_batches(db: DbDep, user: CurrentUserDep) -> list[ImportBatchOut]:
    household_id = _household_id(user)
    batches = db.scalars(select(ImportBatch).where(
        ImportBatch.household_id == household_id,
    ).order_by(ImportBatch.created_at.desc())).all()
    return [
        _batch_out(batch) for batch in batches
        if (account := db.get(Account, batch.account_id)) is not None and can_operate(account, user.id)
    ]


@router.get("/batches/{batch_id}")
def get_batch(batch_id: str, db: DbDep, user: CurrentUserDep) -> ImportBatchDetailOut:
    batch = _get_batch(db, _household_id(user), user.id, batch_id)
    rows = db.scalars(select(ImportRow).where(ImportRow.batch_id == batch.id).order_by(ImportRow.source_position)).all()
    transaction_ids = [row.transaction_id for row in rows if row.transaction_id]
    transactions = {} if not transaction_ids else {
        transaction.id: transaction for transaction in db.scalars(select(Transaction).where(
            Transaction.id.in_(transaction_ids)
        )).all()
    }
    events = [] if not transaction_ids else db.scalars(select(TransactionEditEvent).where(
        TransactionEditEvent.transaction_id.in_(transaction_ids)
    ).order_by(TransactionEditEvent.created_at)).all()
    return ImportBatchDetailOut(
        **_batch_out(batch).model_dump(),
        rows=[ImportRowOut(
            id=row.id, source_position=row.source_position, source_snapshot=row.source_snapshot,
            transaction_baseline=row.transaction_baseline, advisory_reasons=row.advisory_reasons,
            status=row.status, transaction_id=row.transaction_id,
            current_transaction=(ImportTransactionStateOut(
                id=transaction.id, type=transaction.type, amount=float(transaction.amount),
                category_id=transaction.category_id, account_id=transaction.account_id,
                date=transaction.date, note=transaction.note, deleted_at=transaction.deleted_at,
                delete_reason=transaction.delete_reason,
            ) if (transaction := transactions.get(row.transaction_id)) is not None else None),
            edit_events=[TransactionEditEventOut(
                id=event.id, transaction_id=event.transaction_id, edited_by_id=event.edited_by_id,
                before_snapshot=event.before_snapshot, after_snapshot=event.after_snapshot,
                created_at=event.created_at,
            ) for event in events if event.transaction_id == row.transaction_id],
        ) for row in rows],
        edit_events=[TransactionEditEventOut(
            id=event.id, transaction_id=event.transaction_id, edited_by_id=event.edited_by_id,
            before_snapshot=event.before_snapshot, after_snapshot=event.after_snapshot,
            created_at=event.created_at,
        ) for event in events],
    )


def _matches_baseline(transaction: Transaction, baseline: dict) -> bool:
    return (
        transaction.type == baseline["type"]
        and _canonical_amount(transaction.amount) == baseline["amount"]
        and transaction.category_id == baseline["category_id"]
        and transaction.account_id == baseline["account_id"]
        and transaction.date.isoformat() == baseline["date"]
        and transaction.note == baseline["note"]
    )


@router.post("/{batch_id}/revert", responses={409: {"model": ImportRevertConflictResponse}})
def revert_batch(batch_id: str, db: DbDep, user: CurrentUserDep) -> ImportBatchOut:
    batch = _get_batch(db, _household_id(user), user.id, batch_id)
    rows = db.scalars(select(ImportRow).where(
        ImportRow.batch_id == batch.id, ImportRow.status == "imported", ImportRow.transaction_id.is_not(None)
    ).with_for_update()).all()
    transactions = {tx.id: tx for tx in db.scalars(select(Transaction).where(
        Transaction.id.in_([row.transaction_id for row in rows])
    ).with_for_update()).all()} if rows else {}
    conflicts = [ImportRevertConflict(row_id=row.id, transaction_id=row.transaction_id) for row in rows if (
        (tx := transactions.get(row.transaction_id)) is None or tx.deleted_at is not None or not _matches_baseline(tx, row.transaction_baseline)
    )]
    if conflicts:
        raise HTTPException(status_code=409, detail=ImportRevertConflictOut(conflicts=conflicts).model_dump(by_alias=True))
    now = datetime.now()
    for row in rows:
        baseline = row.transaction_baseline
        conditions = [
            Transaction.id == row.transaction_id,
            Transaction.deleted_at.is_(None),
            Transaction.type == baseline["type"],
            Transaction.amount == Decimal(baseline["amount"]),
            Transaction.category_id == baseline["category_id"],
            Transaction.account_id == baseline["account_id"],
            Transaction.date == date.fromisoformat(baseline["date"]),
        ]
        conditions.append(
            Transaction.note.is_(None) if baseline["note"] is None else Transaction.note == baseline["note"]
        )
        if db.execute(update(Transaction).where(*conditions).values(
            deleted_at=now, delete_reason="import_revert"
        )).rowcount != 1:
            # Locks should make this unreachable for API edits; the predicate
            # also protects against any writer that did not participate in them.
            db.rollback()
            conflict = ImportRevertConflict(row_id=row.id, transaction_id=row.transaction_id)
            raise HTTPException(
                status_code=409,
                detail=ImportRevertConflictOut(conflicts=[conflict]).model_dump(by_alias=True),
            )
        invalidate_completed_reconciliation(db, transactions[row.transaction_id])
    db.commit()
    return _batch_out(batch)


@router.post("/{batch_id}/restore")
def restore_batch(batch_id: str, db: DbDep, user: CurrentUserDep) -> ImportBatchOut:
    batch = _get_batch(db, _household_id(user), user.id, batch_id)
    transaction_ids = db.scalars(select(ImportRow.transaction_id).where(
        ImportRow.batch_id == batch.id, ImportRow.status == "imported", ImportRow.transaction_id.is_not(None)
    )).all()
    if transaction_ids:
        transactions = db.scalars(select(Transaction).where(Transaction.id.in_(transaction_ids)).with_for_update()).all()
        for transaction in transactions:
            if transaction.delete_reason == "import_revert":
                invalidate_completed_reconciliation(db, transaction)
                transaction.deleted_at = None
                transaction.delete_reason = None
    db.commit()
    return _batch_out(batch)
