import io

from PIL import Image

from app.services.vision import normalize_image


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
