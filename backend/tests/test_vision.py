import asyncio
import io
import json
from datetime import date
from types import SimpleNamespace

import pytest
from PIL import Image

from app.config import settings
from app.services import vision
from app.services.vision import (
    TicketScanError,
    TicketScanUnavailable,
    analyze_ticket,
    normalize_image,
)


def _jpeg_with_orientation(size: tuple[int, int], orientation: int) -> bytes:
    img = Image.new("RGB", size, color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    # Reescribe el JPEG agregando el tag EXIF Orientation (274)
    img_with_exif = Image.open(io.BytesIO(buffer.getvalue()))
    exif = img_with_exif.getexif()
    exif[274] = orientation
    out = io.BytesIO()
    img_with_exif.save(out, format="JPEG", exif=exif)
    return out.getvalue()


def test_normalize_image_applies_exif_rotation():
    # 100x200 con Orientation=6 (rotar 90°) debe quedar 200x100
    raw = _jpeg_with_orientation((100, 200), 6)

    result = normalize_image(raw)

    normalized = Image.open(io.BytesIO(result))
    assert normalized.size == (200, 100)


def test_normalize_image_downscales_large_images():
    raw = _jpeg_with_orientation((4000, 3000), 1)

    result = normalize_image(raw)

    normalized = Image.open(io.BytesIO(result))
    assert max(normalized.size) <= 2048


def test_normalize_image_returns_original_on_invalid_bytes():
    raw = b"esto no es una imagen"

    assert normalize_image(raw) == raw


# ---------------------------------------------------------------------------
# analyze_ticket: cliente OpenAI mockeado (nunca se llama a OpenRouter).
# ---------------------------------------------------------------------------

CATEGORIES = [
    {"id": "cat-comida", "name": "Comida"},
    {"id": "cat-transporte", "name": "Transporte"},
]


class FakeCompletions:
    def __init__(self, content, error):
        self.content = content
        self.error = error
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class FakeAsyncOpenAI:
    instances: list["FakeAsyncOpenAI"] = []

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.completions = FakeCompletions(FakeAsyncOpenAI.content, FakeAsyncOpenAI.error)
        self.chat = SimpleNamespace(completions=self.completions)
        FakeAsyncOpenAI.instances.append(self)


@pytest.fixture(name="fake_openai")
def fake_openai_fixture(monkeypatch):
    FakeAsyncOpenAI.instances = []
    FakeAsyncOpenAI.content = "{}"
    FakeAsyncOpenAI.error = None
    monkeypatch.setattr(vision, "AsyncOpenAI", FakeAsyncOpenAI)
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "openrouter_model", "test-model")
    return FakeAsyncOpenAI


def _scan():
    return asyncio.run(analyze_ticket(b"fake-image", "image/jpeg", CATEGORIES))


def _payload(**overrides):
    data = {
        "merchant": " Supermercado ",
        "total": 123.45,
        "date": "2026-08-15",
        "suggested_category_id": "cat-comida",
        "confidence": 0.9,
    }
    data.update(overrides)
    return json.dumps(data)


def test_analyze_ticket_without_api_key_raises_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)

    with pytest.raises(TicketScanUnavailable, match="OPENROUTER_API_KEY"):
        _scan()


def test_analyze_ticket_success_normalizes_and_calls_openrouter(fake_openai):
    fake_openai.content = _payload()

    result = _scan()

    assert result == {
        "merchant": "Supermercado",
        "total": 123.45,
        "date": date(2026, 8, 15),
        "suggested_category_id": "cat-comida",
        "confidence": 0.9,
    }
    client = fake_openai.instances[0]
    assert client.init_kwargs == {
        "base_url": vision.OPENROUTER_BASE_URL,
        "api_key": "test-key",
        "timeout": vision.HTTP_TIMEOUT_SECONDS,
    }
    call = client.completions.calls[0]
    assert call["model"] == "test-model"
    assert call["response_format"] == {"type": "json_object"}
    content = call["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert 'id "cat-comida": Comida' in content[0]["text"]
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_analyze_ticket_malformed_json_raises(fake_openai):
    fake_openai.content = "{esto no es json"

    with pytest.raises(TicketScanError, match="Error al analizar el ticket"):
        _scan()


def test_analyze_ticket_completion_timeout_raises(fake_openai):
    fake_openai.error = TimeoutError("upstream timeout")

    with pytest.raises(TicketScanError, match="Error al analizar el ticket"):
        _scan()


def test_analyze_ticket_null_content_is_invalid(fake_openai):
    fake_openai.content = None

    with pytest.raises(TicketScanError, match="no detectó el comercio"):
        _scan()


@pytest.mark.parametrize("content", ["[]", '"texto"', "123"])
def test_analyze_ticket_non_dict_json_raises(fake_openai, content):
    fake_openai.content = content

    with pytest.raises(TicketScanError, match="no es un objeto JSON"):
        _scan()


@pytest.mark.parametrize("merchant", ["", "   ", None])
def test_analyze_ticket_requires_merchant(fake_openai, merchant):
    fake_openai.content = _payload(merchant=merchant)

    with pytest.raises(TicketScanError, match="no detectó el comercio"):
        _scan()


@pytest.mark.parametrize("total", [None, "no-numero", -5, 0])
def test_analyze_ticket_rejects_invalid_total(fake_openai, total):
    fake_openai.content = _payload(total=total)

    with pytest.raises(TicketScanError, match="total|Total"):
        _scan()


def test_analyze_ticket_missing_total_raises(fake_openai):
    data = json.loads(_payload())
    del data["total"]
    fake_openai.content = json.dumps(data)

    with pytest.raises(TicketScanError, match="no detectó el total"):
        _scan()


def test_analyze_ticket_invalid_date_falls_back_to_today(fake_openai):
    fake_openai.content = _payload(date="31/12/2026")

    result = _scan()

    assert result["date"] == date.today()


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [(None, 0.5), ("alta", 0.5), (-1, 0.0), (5, 1.0), ("0.75", 0.75)],
)
def test_analyze_ticket_clamps_confidence(fake_openai, confidence, expected):
    payload = json.loads(_payload())
    if confidence is None:
        del payload["confidence"]
    else:
        payload["confidence"] = confidence
    fake_openai.content = json.dumps(payload)

    assert _scan()["confidence"] == expected


def test_analyze_ticket_unknown_category_falls_back_to_first(fake_openai):
    fake_openai.content = _payload(suggested_category_id="cat-inexistente", confidence=0.95)

    result = _scan()

    assert result["suggested_category_id"] == "cat-comida"
    assert result["confidence"] == 0.5


def test_normalize_image_converts_non_rgb_and_keeps_small_images():
    img = Image.new("P", (32, 16), color=1)
    raw = io.BytesIO()
    img.save(raw, format="PNG")

    result = normalize_image(raw.getvalue())

    normalized = Image.open(io.BytesIO(result))
    assert normalized.mode == "RGB"
    assert normalized.size == (32, 16)
