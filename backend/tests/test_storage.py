"""Tests unitarios de la capa S3 (`app.services.storage`).

Todo se mockea: nunca se contacta un MinIO real. Cubren las rutas de éxito y,
sobre todo, las de error (S3Error) que antes quedaban sin ejecutar.
"""

import pytest
from minio.error import S3Error

from app.services import storage


@pytest.fixture(autouse=True)
def _reset_client_cache():
    """`_client()` cachea la instancia global; aislar tests entre sí."""
    storage._client_instance = None
    yield
    storage._client_instance = None


def _s3_error(code: str) -> S3Error:
    return S3Error(None, code, "mensaje", "recurso", "request-id", "host-id")


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.closed = False
        self.released = False

    def read(self) -> bytes:
        return self.payload

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class FakeClient:
    def __init__(
        self,
        *,
        bucket_exists: bool = True,
        bucket_exists_error: Exception | None = None,
        make_bucket_error: Exception | None = None,
        put_error: Exception | None = None,
        get_error: Exception | None = None,
        get_payload: bytes = b"contenido",
        remove_error: Exception | None = None,
    ):
        self._bucket_exists = bucket_exists
        self.bucket_exists_error = bucket_exists_error
        self.make_bucket_error = make_bucket_error
        self.put_error = put_error
        self.get_error = get_error
        self.get_payload = get_payload
        self.remove_error = remove_error
        self.bucket_exists_calls: list[str] = []
        self.make_bucket_calls: list[str] = []
        self.put_calls: list[dict] = []
        self.get_calls: list[tuple[str, str]] = []
        self.remove_calls: list[tuple[str, str]] = []
        self.response: FakeResponse | None = None

    def bucket_exists(self, bucket: str) -> bool:
        self.bucket_exists_calls.append(bucket)
        if self.bucket_exists_error is not None:
            raise self.bucket_exists_error
        return self._bucket_exists

    def make_bucket(self, bucket: str) -> None:
        self.make_bucket_calls.append(bucket)
        if self.make_bucket_error is not None:
            raise self.make_bucket_error

    def put_object(self, bucket, key, data, length, content_type):
        self.put_calls.append(
            {
                "bucket": bucket,
                "key": key,
                "data": data.read(),
                "length": length,
                "content_type": content_type,
            }
        )
        if self.put_error is not None:
            raise self.put_error

    def get_object(self, bucket: str, key: str) -> FakeResponse:
        self.get_calls.append((bucket, key))
        if self.get_error is not None:
            raise self.get_error
        self.response = FakeResponse(self.get_payload)
        return self.response

    def remove_object(self, bucket: str, key: str) -> None:
        self.remove_calls.append((bucket, key))
        if self.remove_error is not None:
            raise self.remove_error


def _patch_client(monkeypatch, client: FakeClient) -> None:
    monkeypatch.setattr(storage, "_client", lambda: client)


def test_client_builds_minio_from_settings_and_caches_it(monkeypatch):
    captured: list[dict] = []

    class FakeMinio:
        def __init__(self, endpoint, **kwargs):
            captured.append({"endpoint": endpoint, **kwargs})

    monkeypatch.setattr(storage, "Minio", FakeMinio)
    monkeypatch.setattr(storage.settings, "minio_endpoint", "minio:9000")
    monkeypatch.setattr(storage.settings, "minio_access_key", "access")
    monkeypatch.setattr(storage.settings, "minio_secret_key", "secret")
    monkeypatch.setattr(storage.settings, "minio_secure", False)

    first = storage._client()
    second = storage._client()

    assert first is second
    assert captured == [
        {
            "endpoint": "minio:9000",
            "access_key": "access",
            "secret_key": "secret",
            "secure": False,
        }
    ]


def test_put_attachment_creates_missing_bucket_and_uploads(monkeypatch):
    client = FakeClient(bucket_exists=False)
    _patch_client(monkeypatch, client)

    storage.put_attachment("h/1.png", b"abc", "image/png")

    assert client.bucket_exists_calls == [storage.settings.minio_bucket]
    assert client.make_bucket_calls == [storage.settings.minio_bucket]
    assert client.put_calls == [
        {
            "bucket": storage.settings.minio_bucket,
            "key": "h/1.png",
            "data": b"abc",
            "length": 3,
            "content_type": "image/png",
        }
    ]


def test_put_attachment_skips_make_bucket_when_it_exists(monkeypatch):
    client = FakeClient(bucket_exists=True)
    _patch_client(monkeypatch, client)

    storage.put_attachment("h/1.png", b"abc", "image/png")

    assert client.make_bucket_calls == []


@pytest.mark.parametrize(
    ("failing_call", "kwargs"),
    [
        ("bucket_exists", {"bucket_exists_error": _s3_error("InternalError")}),
        (
            "make_bucket",
            {"bucket_exists": False, "make_bucket_error": _s3_error("InternalError")},
        ),
        (
            "put_object",
            {"bucket_exists": True, "put_error": _s3_error("InternalError")},
        ),
    ],
)
def test_put_attachment_wraps_s3_errors(monkeypatch, failing_call, kwargs):
    client = FakeClient(**kwargs)
    _patch_client(monkeypatch, client)

    with pytest.raises(storage.StorageError, match="No se pudo guardar el objeto h/1.png"):
        storage.put_attachment("h/1.png", b"abc", "image/png")


def test_get_attachment_reads_and_releases_response(monkeypatch):
    client = FakeClient(get_payload=b"bytes-del-objeto")
    _patch_client(monkeypatch, client)

    assert storage.get_attachment("h/1.png") == b"bytes-del-objeto"
    assert client.get_calls == [(storage.settings.minio_bucket, "h/1.png")]
    assert client.response is not None
    assert client.response.closed is True
    assert client.response.released is True


@pytest.mark.parametrize("code", ["NoSuchKey", "NoSuchObject", "NoSuchBucket"])
def test_get_attachment_maps_missing_objects_to_not_found(monkeypatch, code):
    _patch_client(monkeypatch, FakeClient(get_error=_s3_error(code)))

    with pytest.raises(storage.StorageNotFoundError, match="No existe el objeto h/1.png"):
        storage.get_attachment("h/1.png")


def test_get_attachment_wraps_other_s3_errors(monkeypatch):
    _patch_client(monkeypatch, FakeClient(get_error=_s3_error("AccessDenied")))

    with pytest.raises(storage.StorageError, match="No se pudo leer el objeto h/1.png"):
        storage.get_attachment("h/1.png")


def test_get_attachment_closes_response_even_if_read_fails(monkeypatch):
    class BrokenResponse(FakeResponse):
        def read(self) -> bytes:
            raise RuntimeError("conexión cortada")

    client = FakeClient(get_payload=b"x")
    response = BrokenResponse(b"x")
    client.get_object = lambda bucket, key: response  # type: ignore[method-assign]
    _patch_client(monkeypatch, client)

    with pytest.raises(RuntimeError, match="conexión cortada"):
        storage.get_attachment("h/1.png")

    assert response.closed is True
    assert response.released is True


def test_delete_attachment_removes_object(monkeypatch):
    client = FakeClient()
    _patch_client(monkeypatch, client)

    storage.delete_attachment("h/1.png")

    assert client.remove_calls == [(storage.settings.minio_bucket, "h/1.png")]


@pytest.mark.parametrize("code", ["NoSuchKey", "NoSuchObject"])
def test_delete_attachment_is_idempotent_for_missing_objects(monkeypatch, code):
    _patch_client(monkeypatch, FakeClient(remove_error=_s3_error(code)))

    storage.delete_attachment("h/1.png")  # no debe lanzar


def test_delete_attachment_wraps_other_s3_errors(monkeypatch):
    _patch_client(monkeypatch, FakeClient(remove_error=_s3_error("AccessDenied")))

    with pytest.raises(storage.StorageError, match="No se pudo borrar el objeto h/1.png"):
        storage.delete_attachment("h/1.png")


def test_avatar_helpers_delegate_with_webp_content_type(monkeypatch):
    client = FakeClient(bucket_exists=True, get_payload=b"avatar")
    _patch_client(monkeypatch, client)

    storage.put_avatar("avatars/1.webp", b"img")
    assert storage.get_avatar("avatars/1.webp") == b"avatar"
    storage.delete_avatar("avatars/1.webp")

    assert client.put_calls[0]["content_type"] == "image/webp"
    assert client.get_calls == [(storage.settings.minio_bucket, "avatars/1.webp")]
    assert client.remove_calls == [(storage.settings.minio_bucket, "avatars/1.webp")]


def test_put_attachment_uses_bytesio_with_exact_length(monkeypatch):
    """Regresión: el objeto subido no debe consumir el buffer antes de MinIO."""
    client = FakeClient(bucket_exists=True)
    _patch_client(monkeypatch, client)

    storage.put_attachment("h/1.png", b"0123456789", "image/png")

    put = client.put_calls[0]
    assert isinstance(put["data"], bytes)
    assert put["length"] == len(b"0123456789")
    assert put["data"] == b"0123456789"