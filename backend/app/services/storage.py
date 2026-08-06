"""Capa de almacenamiento de comprobantes en S3 (MinIO)."""

import io

from minio import Minio
from minio.error import S3Error

from app.config import settings


class StorageError(Exception):
    """Error al interactuar con el almacenamiento de objetos."""


class StorageNotFoundError(StorageError):
    """El objeto solicitado no existe en el almacenamiento."""


_client_instance: Minio | None = None


def _client() -> Minio:
    global _client_instance
    if _client_instance is None:
        _client_instance = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client_instance


def _ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def put_attachment(object_key: str, data: bytes, content_type: str) -> None:
    try:
        client = _client()
        _ensure_bucket(client)
        client.put_object(
            settings.minio_bucket,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
    except S3Error as exc:
        raise StorageError(f"No se pudo guardar el objeto {object_key}") from exc


def get_attachment(object_key: str) -> bytes:
    try:
        client = _client()
        response = client.get_object(settings.minio_bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error as exc:
        if exc.code in ("NoSuchKey", "NoSuchObject", "NoSuchBucket"):
            raise StorageNotFoundError(f"No existe el objeto {object_key}") from exc
        raise StorageError(f"No se pudo leer el objeto {object_key}") from exc


def delete_attachment(object_key: str) -> None:
    try:
        client = _client()
        client.remove_object(settings.minio_bucket, object_key)
    except S3Error as exc:
        # remove_object es idempotente en S3; ignoramos "no existe".
        if exc.code not in ("NoSuchKey", "NoSuchObject"):
            raise StorageError(f"No se pudo borrar el objeto {object_key}") from exc


def put_avatar(object_key: str, data: bytes) -> None:
    put_attachment(object_key, data, "image/webp")


def get_avatar(object_key: str) -> bytes:
    return get_attachment(object_key)


def delete_avatar(object_key: str) -> None:
    delete_attachment(object_key)
