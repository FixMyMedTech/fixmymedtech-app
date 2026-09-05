"""MinIO object storage via boto3 (S3-compatible API).

Configuration (environment variables, see docker-compose.yml / .env):

* ``MINIO_ENDPOINT``   — host:port of the MinIO server as seen from this
  container (e.g. ``minio:9000``). A scheme is added if missing.
* ``MINIO_ROOT_USER`` / ``MINIO_ROOT_PASSWORD`` — credentials.
* ``MINIO_BUCKET``     — bucket name, default ``fixmymedtech``.

The bucket is created on first use and made public-read so objects can also
be served straight from MinIO if desired; the app still prefers streaming
them through the backend / frontend.

Keys are namespaced by collection so different entities can store files
without colliding. The pattern used by application code is:

    f"{collection}/{item_id}/{uuid}{ext}"

For example: ``devices/{device_id}/<uuid>.png`` for device photos,
``faults/{report_id}/<uuid>.jpg`` for fault-report photos, and
``profiles/{profile_id}/<uuid>.jpg`` for user avatars. Call sites pass an
arbitrary ``collection`` (and any extra path segments they want), so new
entity types only need to pick a path.
"""

import os
import uuid
import mimetypes

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT  = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET     = os.getenv("MINIO_BUCKET", "fixmymedtech")

_endpoint = MINIO_ENDPOINT if "://" in MINIO_ENDPOINT else f"http://{MINIO_ENDPOINT}"

_client: "S3Client | None" = None


def get_client():
    """Return a cached boto3 S3 client pointed at MinIO."""
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=_endpoint,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )
        _ensure_bucket(_client)
    return _client


def _ensure_bucket(client) -> None:
    """Create the bucket if it doesn't exist and set a public-read policy."""
    try:
        client.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=MINIO_BUCKET)

    try:
        client.put_bucket_policy(
            Bucket=MINIO_BUCKET,
            Policy=(
                '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",'
                '"Principal":"*","Action":["s3:GetObject"],'
                f'"Resource":"arn:aws:s3:::{MINIO_BUCKET}/*"}}]}}'
            ),
        )
    except ClientError:
        pass


def default_content_type(filename: str) -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or "application/octet-stream"


async def upload_file(collection: str, item_id: str, filename: str, content: bytes,
                      content_type: str = None, object_id: str = None) -> str:
    """Upload a file to MinIO and return its object key.

    ``collection`` is the path segment for the entity type (e.g. ``devices``,
    ``faults``, ``profiles``). ``item_id`` is the owning entity's ID.

    Object path: ``{collection}/{item_id}/{id}{ext}`` where ``id`` is a fresh
    UUID by default — or an explicit ``object_id`` (including its extension)
    when callers need to coordinate related keys themselves (e.g. paired
    ``raw_<uid>.jpg`` / ``processed_<uid>.jpg`` photos).
    """
    ext = os.path.splitext(filename or "")[1].lower() or ".bin"
    if object_id:
        key = f"{collection}/{item_id}/{object_id}"
    else:
        key = f"{collection}/{item_id}/{uuid.uuid4().hex}{ext}"

    client = get_client()
    client.put_object(
        Bucket=MINIO_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type or default_content_type(filename or "file.bin"),
    )
    return key


async def get_file(key: str) -> tuple[bytes, str] | None:
    """Fetch an object from MinIO. Returns ``(bytes, content_type)`` or None."""
    try:
        client = get_client()
        obj = client.get_object(Bucket=MINIO_BUCKET, Key=key)
    except ClientError:
        return None
    content = obj["Body"].read()
    ctype = obj.get("ContentType") or default_content_type(key)
    return content, ctype


def delete_file(key: str) -> None:
    """Remove an object from MinIO. Safe to call for nonexistent keys."""
    try:
        client = get_client()
        client.delete_object(Bucket=MINIO_BUCKET, Key=key)
    except ClientError:
        pass


def public_url(key: str) -> str:
    return f"{_endpoint}/{MINIO_BUCKET}/{key}"