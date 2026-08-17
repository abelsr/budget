"""Materialización de reglas recurrentes.

**Por qué lazy y no un job.** La app es self-hosted: no hay cron ni scheduler
garantizado, y un contenedor apagado tres días no debe perder la renta. Así que
las transacciones se generan al leer —quien abre la app dispara el catch-up— y
el estado vive en `next_run_date`, no en una bitácora de ejecuciones.

**Por qué no duplica.** La lectura de reglas vencidas toma `SELECT ... FOR
UPDATE`, y la inserción y el avance de `next_run_date` van en la misma
transacción de DB. Si dos peticiones concurrentes (el Dashboard dispara tres, o
dos miembros abren la app a la vez) llegan juntas, la segunda se bloquea; al
liberarse, Postgres re-evalúa el `WHERE` contra la fila ya actualizada, la
regla no califica y se va con las manos vacías. En SQLite —los tests— el
`FOR UPDATE` no se renderiza, pero ahí no hay concurrencia.
"""

import calendar
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, RecurringRule, Transaction
from app.services.account_access import visible_accounts

#: Frecuencias soportadas. Quincenal/anual/personalizada quedan fuera del
#: alcance de esta fase.
FREQUENCIES = ("weekly", "monthly")

#: Cuánto puede quedar `next_run_date` en el pasado al crear una regla. Sin
#: tope, una fecha de hace años materializaría cientos de transacciones de
#: golpe en la primera lectura.
MAX_BACKFILL_DAYS = 366


def advance(current: date, frequency: str, anchor_day: int | None = None) -> date:
    """Siguiente fecha de ejecución después de `current`.

    En mensual, `anchor_day` es el día que la regla quiere (28-31 incluidos):
    si el mes destino no lo tiene, se recorta al último día **sin** perder el
    ancla, de modo que enero 31 → febrero 28 → marzo 31.
    """
    if frequency == "weekly":
        return current + timedelta(days=7)
    if frequency == "monthly":
        year = current.year + 1 if current.month == 12 else current.year
        month = 1 if current.month == 12 else current.month + 1
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(anchor_day or current.day, last_day))
    raise ValueError(f"Frecuencia no soportada: {frequency}")


def next_future_run(rule: RecurringRule, today: date) -> date:
    """Primera fecha de ejecución posterior a `today`, sin generar nada.

    Se usa al reactivar una regla pausada: quien la pausó no quiere que al
    reanudarla le lluevan los meses que estuvo apagada.
    """
    run_date = rule.next_run_date
    while run_date <= today:
        run_date = advance(run_date, rule.frequency, rule.anchor_day)
    return run_date


def materialize_due(
    db: Session, household_id: str, user_id: str, today: date | None = None
) -> int:
    """Genera las transacciones pendientes del hogar y devuelve cuántas creó.

    Una regla atrasada varios periodos materializa todas sus ocurrencias en un
    solo paso, cada una con su propia fecha.
    """
    today = today or date.today()
    rules = db.scalars(
        select(RecurringRule).join(Account)
        .where(
            RecurringRule.household_id == household_id,
            visible_accounts(user_id),
            RecurringRule.active.is_(True),
            RecurringRule.next_run_date <= today,
        )
        .with_for_update()
    ).all()

    created = 0
    for rule in rules:
        while rule.next_run_date <= today:
            db.add(
                Transaction(
                    household_id=rule.household_id,
                    type=rule.type,
                    amount=rule.amount,
                    category_id=rule.category_id,
                    account_id=rule.account_id,
                    member_id=rule.created_by_id,
                    date=rule.next_run_date,
                    note=rule.note,
                    recurring_rule_id=rule.id,
                )
            )
            rule.next_run_date = advance(
                rule.next_run_date, rule.frequency, rule.anchor_day
            )
            created += 1

    if created:
        db.commit()
    from app.services.housekeeping import maybe_purge

    maybe_purge(db)
    return created
