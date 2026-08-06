from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


DateFormat = Literal["DD/MM/YYYY", "MM/DD/YYYY"]


class ImportMapping(_CamelModel):
    date: str = Field(min_length=1, max_length=120)
    amount: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=120)


class ImportPreviewRow(_CamelModel):
    source_position: int
    date: date
    amount: float
    description: str | None
    duplicate_reasons: list[Literal["household", "fingerprint", "file"]] = []
    selected: bool


class ImportPreviewOut(_CamelModel):
    headers: list[str]
    suggested_mapping: ImportMapping
    mapping: ImportMapping
    date_format: DateFormat
    rows: list[ImportPreviewRow]


class ImportBatchOut(_CamelModel):
    id: str
    account_id: str
    source_filename: str
    mapping: ImportMapping
    selected_count: int
    imported_count: int
    skipped_count: int
    created_at: datetime


class ImportCommitOut(_CamelModel):
    batch: ImportBatchOut
    selected_count: int
    imported_count: int
    skipped_count: int


class ImportRowOut(_CamelModel):
    id: str
    source_position: int
    source_snapshot: dict
    transaction_baseline: dict
    advisory_reasons: list[Literal["household", "fingerprint", "file"]]
    status: str
    transaction_id: str | None
    current_transaction: "ImportTransactionStateOut | None"
    edit_events: list["TransactionEditEventOut"]


class ImportTransactionStateOut(_CamelModel):
    id: str
    type: str
    amount: float
    category_id: str | None
    account_id: str
    date: date
    note: str | None
    deleted_at: datetime | None
    delete_reason: str | None


class TransactionEditEventOut(_CamelModel):
    id: str
    transaction_id: str
    edited_by_id: str
    before_snapshot: dict
    after_snapshot: dict
    created_at: datetime


class ImportBatchDetailOut(ImportBatchOut):
    rows: list[ImportRowOut]
    edit_events: list[TransactionEditEventOut]


class ImportRevertConflict(_CamelModel):
    row_id: str
    transaction_id: str


class ImportRevertConflictOut(_CamelModel):
    conflicts: list[ImportRevertConflict]


class ImportRevertConflictResponse(_CamelModel):
    detail: ImportRevertConflictOut
