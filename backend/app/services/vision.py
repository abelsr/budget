import base64
import json
from datetime import date

import httpx

from app.config import settings

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

HTTP_TIMEOUT_SECONDS = 30


class TicketScanUnavailable(Exception):
    """El escáner no está configurado (falta GEMINI_API_KEY)."""


class TicketScanError(Exception):
    """Falló la llamada al proveedor de visión o su respuesta es inválida."""


def analyze_ticket(
    image_bytes: bytes, mime_type: str, categories: list[dict]
) -> dict:
    """Analiza la imagen de un ticket con Gemini y devuelve datos estructurados.

    categories: [{"id": ..., "name": ...}] de categorías expense activas del
    hogar. Devuelve dict snake_case: merchant, total, date,
    suggested_category_id, confidence.
    """
    if settings.gemini_api_key is None:
        raise TicketScanUnavailable("Falta GEMINI_API_KEY")

    prompt = _build_prompt(categories)
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        }
                    },
                    {"text": prompt},
                ]
            }
        ],
        "generation_config": {"response_mime_type": "application/json"},
    }

    try:
        response = httpx.post(
            GEMINI_URL,
            params={"key": settings.gemini_api_key},
            json=payload,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)
    except Exception as exc:
        raise TicketScanError("Error al analizar el ticket") from exc

    return _validate(data, categories)


def _build_prompt(categories: list[dict]) -> str:
    category_lines = "\n".join(
        f'- id "{c["id"]}": {c["name"]}' for c in categories
    )
    today = date.today().isoformat()
    return (
        "Analiza la imagen de este ticket de compra y extrae sus datos. "
        "Responde ÚNICAMENTE con un objeto JSON con estas llaves:\n"
        '- "merchant": nombre del comercio (string).\n'
        '- "total": monto total pagado (número positivo).\n'
        '- "date": fecha del ticket en formato YYYY-MM-DD; si no es legible, '
        f'usa hoy ({today}).\n'
        '- "suggested_category_id": el id de la categoría más apropiada de '
        "esta lista (elige exactamente uno):\n"
        f"{category_lines}\n"
        '- "confidence": qué tan seguro estás de la extracción (número 0-1).'
    )


def _validate(data: dict, categories: list[dict]) -> dict:
    if not isinstance(data, dict):
        raise TicketScanError("Respuesta del modelo no es un objeto JSON")

    merchant = str(data.get("merchant") or "").strip()
    if not merchant:
        raise TicketScanError("El modelo no detectó el comercio")

    try:
        total = float(data["total"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TicketScanError("El modelo no detectó el total") from exc
    if total <= 0:
        raise TicketScanError("Total inválido")

    try:
        ticket_date = date.fromisoformat(str(data.get("date") or ""))
    except ValueError:
        ticket_date = date.today()

    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    valid_ids = [c["id"] for c in categories]
    suggested_category_id = str(data.get("suggested_category_id") or "")
    if suggested_category_id not in valid_ids:
        suggested_category_id = valid_ids[0]
        confidence = min(confidence, 0.5)

    return {
        "merchant": merchant,
        "total": total,
        "date": ticket_date,
        "suggested_category_id": suggested_category_id,
        "confidence": confidence,
    }
