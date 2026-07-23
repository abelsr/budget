import base64
import io
import json
from datetime import date

from openai import AsyncOpenAI
from PIL import Image, ImageOps

from app.config import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
HTTP_TIMEOUT_SECONDS = 30
# Redimensiona fotos grandes (las de celular pesan 5-10 MB); los modelos
# de visión downsamplean de todos modos, así se reduce payload y costo.
MAX_IMAGE_DIMENSION = 2048


class TicketScanUnavailable(Exception):
    """El escáner no está configurado (falta OPENROUTER_API_KEY)."""


class TicketScanError(Exception):
    """Falló la llamada al modelo de visión o su respuesta es inválida."""


def normalize_image(image_bytes: bytes) -> bytes:
    """Endereza la imagen según su orientación EXIF y la redimensiona.

    Las fotos de celular guardan la rotación en EXIF (orientation=6/8) y los
    pipelines de visión no siempre la honran: llegan de lado y el modelo lee
    mal (fechas y totales incorrectos). Si la imagen no se puede procesar,
    se devuelven los bytes originales.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        if max(img.size) > MAX_IMAGE_DIMENSION:
            img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()
    except Exception:
        return image_bytes


async def analyze_ticket(
    image_bytes: bytes, mime_type: str, categories: list[dict]
) -> dict:
    """Analiza la imagen de un ticket con un LLM de visión (OpenRouter,
    API compatible con OpenAI) y devuelve datos estructurados.

    categories: [{"id": ..., "name": ...}] de categorías expense activas del
    hogar. Devuelve dict snake_case: merchant, total, date,
    suggested_category_id, confidence.
    """
    if settings.openrouter_api_key is None:
        raise TicketScanUnavailable("Falta OPENROUTER_API_KEY")

    client = AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=settings.openrouter_api_key,
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    normalized = normalize_image(image_bytes)
    data_url = (
        "data:image/jpeg;base64,"
        f"{base64.b64encode(normalized).decode('ascii')}"
    )

    try:
        completion = await client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _build_prompt(categories)},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(completion.choices[0].message.content or "{}")
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
