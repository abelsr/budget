"""Reglas recurrentes: avance de fechas, materialización lazy y endpoints.

El avance de fechas se prueba como función pura y la materialización pasándole
un `today` explícito. Los tests que van por HTTP usan el hoy real y fechas
relativas a él (`today - timedelta(...)`), así no se vuelven rojos al cambiar
el calendario.
"""

from datetime import date, timedelta

import pytest

from app.models import RecurringRule, Transaction
from app.services.recurring import advance, materialize_due, next_future_run


@pytest.fixture(name="world")
def world_fixture(world_factory):
    """Dos hogares con cuenta y categoría propias, para probar aislamiento."""
    return world_factory(
        accounts=(
            {"household": 1, "name": "Débito", "kind": "debit", "opening_balance": 100},
            {"household": 2, "name": "Débito", "kind": "debit", "opening_balance": 0},
        ),
        categories=(
            {"household": 1, "name": "Casa", "icon": "home", "color": "#30b0c7", "type": "expense"},
            {"household": 2, "name": "Casa", "icon": "home", "color": "#30b0c7", "type": "expense"},
        ),
    )


def make_rule(session, world, **overrides) -> RecurringRule:
    """Regla en h1. Por defecto mensual, vence hoy, gasto de 30."""
    next_run_date = overrides.pop("next_run_date", date.today())
    frequency = overrides.pop("frequency", "monthly")
    fields = {
        "household_id": world["h1"].id,
        "type": "expense",
        "amount": 30,
        "category_id": world["categories"][0].id,
        "account_id": world["account1"].id,
        "created_by_id": world["u1"].id,
        "frequency": frequency,
        "next_run_date": next_run_date,
        "anchor_day": next_run_date.day if frequency == "monthly" else None,
        "note": "Renta",
    }
    fields.update(overrides)
    rule = RecurringRule(**fields)
    session.add(rule)
    session.commit()
    return rule


def create_rule_via_api(client, headers, world, **overrides):
    payload = {
        "type": "expense",
        "amount": 30.0,
        "categoryId": world["categories"][0].id,
        "accountId": world["account1"].id,
        "frequency": "monthly",
        "nextRunDate": date.today().isoformat(),
        "note": "Renta",
    }
    payload.update(overrides)
    resp = client.post("/recurring-rules", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------- advance(): la aritmética de fechas ----------


def test_advance_weekly_suma_siete_dias():
    assert advance(date(2026, 7, 25), "weekly") == date(2026, 8, 1)


def test_advance_monthly_mismo_dia_del_mes_siguiente():
    assert advance(date(2026, 7, 15), "monthly", 15) == date(2026, 8, 15)


def test_advance_monthly_recorta_en_febrero_sin_perder_el_ancla():
    """El caso que obliga a guardar `anchor_day`: si el 31 se recortara a 28 y
    marzo partiera de ahí, la renta se movería al 28 para siempre."""
    febrero = advance(date(2026, 1, 31), "monthly", 31)
    assert febrero == date(2026, 2, 28)
    assert advance(febrero, "monthly", 31) == date(2026, 3, 31)


def test_advance_monthly_respeta_el_año_bisiesto():
    assert advance(date(2028, 1, 31), "monthly", 31) == date(2028, 2, 29)


def test_advance_monthly_cruza_el_año():
    assert advance(date(2026, 12, 31), "monthly", 31) == date(2027, 1, 31)


def test_advance_rechaza_frecuencia_desconocida():
    with pytest.raises(ValueError):
        advance(date(2026, 7, 25), "quincenal")


# ---------- materialize_due(): generación y no-duplicación ----------


def test_materializa_todas_las_ocurrencias_atrasadas(session, world):
    """Una regla con tres periodos de atraso genera tres transacciones, cada
    una con su fecha, no una sola con la de hoy."""
    rule = make_rule(
        session, world, frequency="weekly", next_run_date=date(2026, 6, 1)
    )

    created = materialize_due(session, world["h1"].id, world["u1"].id, today=date(2026, 6, 20))

    assert created == 3
    dates = sorted(
        tx.date for tx in session.query(Transaction).filter_by(recurring_rule_id=rule.id)
    )
    assert dates == [date(2026, 6, 1), date(2026, 6, 8), date(2026, 6, 15)]
    assert rule.next_run_date == date(2026, 6, 22)


def test_materializar_dos_veces_no_duplica(session, world):
    make_rule(session, world, frequency="weekly", next_run_date=date(2026, 6, 1))
    today = date(2026, 6, 20)

    assert materialize_due(session, world["h1"].id, world["u1"].id, today=today) == 3
    assert materialize_due(session, world["h1"].id, world["u1"].id, today=today) == 0
    assert session.query(Transaction).count() == 3


def test_mensual_del_31_sobrevive_a_los_meses_cortos(session, world):
    """Enero 31 → febrero 28 → marzo 31: el ancla no se pierde al recortar."""
    make_rule(session, world, frequency="monthly", next_run_date=date(2026, 1, 31))

    materialize_due(session, world["h1"].id, world["u1"].id, today=date(2026, 3, 31))

    dates = sorted(tx.date for tx in session.query(Transaction).all())
    assert dates == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]


def test_la_transaccion_generada_hereda_los_datos_de_la_regla(session, world):
    rule = make_rule(session, world, next_run_date=date(2026, 7, 1))

    materialize_due(session, world["h1"].id, world["u1"].id, today=date(2026, 7, 1))

    tx = session.query(Transaction).one()
    assert tx.type == rule.type
    assert float(tx.amount) == 30.0
    assert tx.category_id == rule.category_id
    assert tx.account_id == rule.account_id
    assert tx.note == "Renta"
    assert tx.recurring_rule_id == rule.id
    # Se atribuye al autor de la regla, no a quien abrió la app
    assert tx.member_id == world["u1"].id


def test_regla_pausada_no_materializa(session, world):
    make_rule(session, world, next_run_date=date(2026, 7, 1), active=False)

    assert materialize_due(session, world["h1"].id, world["u1"].id, today=date(2026, 7, 20)) == 0
    assert session.query(Transaction).count() == 0


def test_regla_futura_no_materializa(session, world):
    make_rule(session, world, next_run_date=date(2026, 8, 1))

    assert materialize_due(session, world["h1"].id, world["u1"].id, today=date(2026, 7, 25)) == 0


def test_materializar_no_toca_otros_hogares(session, world):
    make_rule(session, world, next_run_date=date(2026, 7, 1))

    assert materialize_due(session, world["h2"].id, world["u2"].id, today=date(2026, 7, 20)) == 0
    assert session.query(Transaction).count() == 0


def test_next_future_run_salta_el_periodo_pausado(session, world):
    rule = make_rule(session, world, frequency="weekly", next_run_date=date(2026, 6, 1))

    assert next_future_run(rule, date(2026, 6, 20)) == date(2026, 6, 22)
    # No generó nada: solo calcula
    assert session.query(Transaction).count() == 0


# ---------- Endpoints ----------


def test_rule_crud_via_api(client, world):
    headers = world["headers1"]

    rule = create_rule_via_api(
        client, headers, world, nextRunDate=(date.today() + timedelta(days=30)).isoformat()
    )
    assert rule["householdId"] == world["h1"].id
    assert rule["active"] is True
    assert rule["createdById"] == world["u1"].id

    resp = client.get("/recurring-rules", headers=headers)
    assert resp.status_code == 200
    assert [r["id"] for r in resp.json()] == [rule["id"]]

    resp = client.patch(
        f"/recurring-rules/{rule['id']}",
        json={"amount": 45.5, "note": "Renta nueva"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == 45.5
    assert resp.json()["note"] == "Renta nueva"

    resp = client.delete(f"/recurring-rules/{rule['id']}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/recurring-rules", headers=headers).json() == []


def test_get_transactions_materializa_y_no_duplica(client, world):
    """El criterio central: una regla vencida aparece al cargar Movimientos y
    recargar no la vuelve a generar."""
    headers = world["headers1"]
    create_rule_via_api(
        client,
        headers,
        world,
        frequency="weekly",
        nextRunDate=(date.today() - timedelta(days=14)).isoformat(),
    )

    first = client.get("/transactions", headers=headers).json()
    assert len(first) == 3
    assert all(t["recurringRuleId"] is not None for t in first)

    second = client.get("/transactions", headers=headers).json()
    assert [t["id"] for t in second] == [t["id"] for t in first]


def test_los_saldos_y_el_resumen_ven_las_transacciones_generadas(client, world):
    """El Dashboard dispara las tres queries en paralelo: cuentas y resumen
    tienen que materializar por su cuenta o saldrían desfasados."""
    headers = world["headers1"]
    create_rule_via_api(client, headers, world, nextRunDate=date.today().isoformat())

    # Sin haber pedido /transactions antes
    accounts = client.get("/accounts", headers=headers).json()
    assert accounts[0]["balance"] == 70.0  # 100 de apertura − 30 del gasto

    summary = client.get("/summary/month", headers=headers).json()
    assert summary["expense"] == 30.0


def test_pausar_detiene_y_reactivar_no_rellena_lo_pausado(client, world):
    """La regla se pausa estando ya vencida: sin la pausa habría generado tres
    semanas. Al reanudarla salta hacia adelante en vez de cobrarlas."""
    headers = world["headers1"]
    rule = create_rule_via_api(
        client,
        headers,
        world,
        frequency="weekly",
        nextRunDate=(date.today() - timedelta(days=20)).isoformat(),
    )

    resp = client.patch(
        f"/recurring-rules/{rule['id']}", json={"active": False}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["active"] is False

    # Vencida pero pausada: cargar Movimientos no genera nada
    assert client.get("/transactions", headers=headers).json() == []

    resp = client.patch(
        f"/recurring-rules/{rule['id']}", json={"active": True}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["active"] is True
    # Reanuda hacia adelante, sin cobrar lo que estuvo apagada
    assert date.fromisoformat(resp.json()["nextRunDate"]) > date.today()
    assert client.get("/transactions", headers=headers).json() == []


def test_reactivar_una_regla_vigente_no_mueve_su_fecha(client, world):
    """Reanudar no debe empujar la fecha si la regla no se pasó de tiempo."""
    headers = world["headers1"]
    proxima = (date.today() + timedelta(days=5)).isoformat()
    rule = create_rule_via_api(
        client, headers, world, frequency="weekly", nextRunDate=proxima
    )
    client.patch(
        f"/recurring-rules/{rule['id']}", json={"active": False}, headers=headers
    )

    resp = client.patch(
        f"/recurring-rules/{rule['id']}", json={"active": True}, headers=headers
    )

    assert resp.json()["nextRunDate"] == proxima


def test_borrar_la_regla_conserva_las_transacciones(client, world):
    headers = world["headers1"]
    rule = create_rule_via_api(client, headers, world, nextRunDate=date.today().isoformat())
    generated = client.get("/transactions", headers=headers).json()
    assert len(generated) == 1

    resp = client.delete(f"/recurring-rules/{rule['id']}", headers=headers)
    assert resp.status_code == 204

    remaining = client.get("/transactions", headers=headers).json()
    assert [t["id"] for t in remaining] == [t["id"] for t in generated]
    # Suelta el enlace: la transacción sobrevive, pierde el badge
    assert remaining[0]["recurringRuleId"] is None


def test_crear_transaccion_con_repeat_crea_la_regla_ligada(client, world):
    headers = world["headers1"]

    resp = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": 1200.0,
            "categoryId": world["categories"][0].id,
            "accountId": world["account1"].id,
            "date": date.today().isoformat(),
            "note": "Renta",
            "repeat": "monthly",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    tx = resp.json()
    assert tx["recurringRuleId"] is not None

    rules = client.get("/recurring-rules", headers=headers).json()
    assert len(rules) == 1
    assert rules[0]["id"] == tx["recurringRuleId"]
    assert rules[0]["frequency"] == "monthly"
    # Esta transacción es la primera ocurrencia: la regla arranca en la siguiente
    assert date.fromisoformat(rules[0]["nextRunDate"]) > date.today()

    # Y no duplica hoy mismo
    assert len(client.get("/transactions", headers=headers).json()) == 1


def test_crear_transaccion_sin_repeat_no_crea_regla(client, world):
    headers = world["headers1"]

    resp = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": 10.0,
            "categoryId": world["categories"][0].id,
            "accountId": world["account1"].id,
            "date": date.today().isoformat(),
        },
        headers=headers,
    )

    assert resp.status_code == 201
    assert resp.json()["recurringRuleId"] is None
    assert client.get("/recurring-rules", headers=headers).json() == []


def test_validaciones_de_la_regla(client, world):
    headers = world["headers1"]
    base = {
        "type": "expense",
        "amount": 30.0,
        "categoryId": world["categories"][0].id,
        "accountId": world["account1"].id,
        "frequency": "monthly",
        "nextRunDate": date.today().isoformat(),
    }

    resp = client.post(
        "/recurring-rules", json={**base, "frequency": "quincenal"}, headers=headers
    )
    assert resp.status_code == 422

    resp = client.post("/recurring-rules", json={**base, "amount": 0}, headers=headers)
    assert resp.status_code == 422

    # Fecha demasiado atrás: materializarla generaría cientos de transacciones
    resp = client.post(
        "/recurring-rules",
        json={**base, "nextRunDate": (date.today() - timedelta(days=400)).isoformat()},
        headers=headers,
    )
    assert resp.status_code == 422

    resp = client.post(
        "/recurring-rules",
        json={**base, "categoryId": world["categories"][1].id},
        headers=headers,
    )
    assert resp.status_code == 404

    resp = client.post(
        "/recurring-rules",
        json={**base, "accountId": world["account2"].id},
        headers=headers,
    )
    assert resp.status_code == 404


def test_aislamiento_entre_hogares(client, world):
    headers1 = world["headers1"]
    headers2 = world["headers2"]
    rule = create_rule_via_api(
        client, headers1, world, nextRunDate=(date.today() + timedelta(days=5)).isoformat()
    )

    assert client.get("/recurring-rules", headers=headers2).json() == []
    assert (
        client.patch(
            f"/recurring-rules/{rule['id']}", json={"active": False}, headers=headers2
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/recurring-rules/{rule['id']}", headers=headers2).status_code
        == 404
    )
    # Y sigue intacta para su dueño
    assert client.get("/recurring-rules", headers=headers1).json()[0]["active"] is True
