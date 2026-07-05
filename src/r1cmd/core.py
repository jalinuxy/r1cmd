"""Core client for ArvanCloud Object Storage."""

from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import IO, Any, BinaryIO, Iterator, Mapping, MutableMapping, Optional, Sequence, Union

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

from r1cmd.constants import APP_NAME, ARVAN_STORAGE_ENDPOINT, ARVAN_STORAGE_REGION

PathLike = Union[str, Path]


@dataclass(frozen=True)
class RemoteFile:
    """A file stored in Arvan Storage."""

    path: str
    name: str
    size: int
    modified: datetime


class ArvanStorageError(Exception):
    """Raised when an Arvan Storage operation fails."""


@dataclass(frozen=True)
class ArvanStorageConfig:
    """Connection settings for ArvanCloud Object Storage."""

    access_key: str
    secret_key: str
    endpoint_url: str = ARVAN_STORAGE_ENDPOINT
    region_name: str = ARVAN_STORAGE_REGION
    default_bucket: Optional[str] = None

    @classmethod
    def from_env(
        cls,
        *,
        env_file: Optional[PathLike] = None,
        override: bool = False,
    ) -> "ArvanStorageConfig":
        """Load configuration from environment variables and optional .env file."""
        if env_file is not None:
            load_dotenv(dotenv_path=env_file, override=override)
        else:
            load_dotenv(override=override)

        access_key = os.getenv("ARVAN_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("ARVAN_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
        endpoint_url = (
            os.getenv("ARVAN_ENDPOINT_URL")
            or os.getenv("AWS_ENDPOINT_URL")
            or ARVAN_STORAGE_ENDPOINT
        )
        region_name = (
            os.getenv("ARVAN_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or ARVAN_STORAGE_REGION
        )
        default_bucket = (
            os.getenv("ARVAN_SPACE")
            or os.getenv("ARVAN_BUCKET")
            or os.getenv("AWS_BUCKET")
        )

        missing = [
            name
            for name, value in (
                ("ARVAN_ACCESS_KEY_ID", access_key),
                ("ARVAN_SECRET_ACCESS_KEY", secret_key),
            )
            if not value
        ]
        if missing:
            raise ArvanStorageError(
                "Missing credentials: "
                + ", ".join(missing)
                + f". Run '{APP_NAME} setup' or set them in your environment."
            )

        return cls(
            access_key=access_key,
            secret_key=secret_key,
            endpoint_url=endpoint_url,
            region_name=region_name,
            default_bucket=default_bucket,
        )


class ArvanStorage:
    """Client for ArvanCloud Object Storage."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        endpoint_url: str = ARVAN_STORAGE_ENDPOINT,
        *,
        region_name: str = ARVAN_STORAGE_REGION,
        default_bucket: Optional[str] = None,
        session: Optional[boto3.session.Session] = None,
        client_config: Optional[Config] = None,
    ) -> None:
        if not access_key or not secret_key:
            raise ArvanStorageError("Access key and secret key are required.")

        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint_url = endpoint_url.rstrip("/")
        self.region_name = region_name
        self.default_bucket = default_bucket

        self._session = session or boto3.session.Session()
        self._client_config = client_config or Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )
        self._client: Optional[BaseClient] = None

    @property
    def default_space(self) -> Optional[str]:
        """User-facing name for the default storage space (bucket)."""
        return self.default_bucket

    @classmethod
    def from_credentials(
        cls,
        access_key: str,
        secret_key: str,
        *,
        space: Optional[str] = None,
        **kwargs: Any,
    ) -> "ArvanStorage":
        """Connect with only an access key and secret key."""
        return cls(
            access_key=access_key,
            secret_key=secret_key,
            default_bucket=space,
            **kwargs,
        )

    @classmethod
    def connect(cls, *, space: Optional[str] = None, **kwargs: Any) -> "ArvanStorage":
        """Connect using credentials saved by the interactive setup wizard."""
        from r1cmd.config import UserConfig

        if not UserConfig.exists():
            raise ArvanStorageError(
                f"No saved credentials found. Run '{APP_NAME} setup' first."
            )

        config = UserConfig.load()
        return cls(
            access_key=config.access_key,
            secret_key=config.secret_key,
            default_bucket=space or config.default_space,
            **kwargs,
        )

    @classmethod
    def from_config(cls, config: ArvanStorageConfig, **kwargs: Any) -> "ArvanStorage":
        """Create a client from an :class:`ArvanStorageConfig` instance."""
        return cls(
            access_key=config.access_key,
            secret_key=config.secret_key,
            endpoint_url=config.endpoint_url,
            region_name=config.region_name,
            default_bucket=config.default_bucket,
            **kwargs,
        )

    @classmethod
    def from_env(
        cls,
        *,
        env_file: Optional[PathLike] = None,
        override: bool = False,
        **kwargs: Any,
    ) -> "ArvanStorage":
        """Create a client using environment variables and an optional .env file."""
        return cls.from_config(ArvanStorageConfig.from_env(env_file=env_file, override=override), **kwargs)

    @property
    def client(self) -> BaseClient:
        """Lazy-initialized boto3 S3 client."""
        if self._client is None:
            self._client = self._session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region_name,
                config=self._client_config,
            )
        return self._client

    def _resolve_bucket(self, bucket: Optional[str]) -> str:
        resolved = bucket or self.default_bucket
        if not resolved:
            raise ArvanStorageError(
                f"No storage space selected. Run '{APP_NAME} setup' or pass a space name."
            )
        return resolved

    @staticmethod
    def _wrap_error(action: str, error: Exception) -> ArvanStorageError:
        if isinstance(error, ClientError):
            code = error.response.get("Error", {}).get("Code", "ClientError")
            message = error.response.get("Error", {}).get("Message", str(error))
            friendly = {
                "NoSuchBucket": "That storage space does not exist.",
                "NoSuchKey": "That file was not found.",
                "InvalidAccessKeyId": "Your Access Key looks wrong. Check Arvan panel credentials.",
                "SignatureDoesNotMatch": "Your Secret Key looks wrong. Check Arvan panel credentials.",
                "AccessDenied": "Access denied. Your keys may not have permission for this action.",
            }.get(code, message)
            return ArvanStorageError(f"{action} failed: {friendly}")
        if isinstance(error, BotoCoreError):
            return ArvanStorageError(
                f"{action} failed: Could not reach Arvan Storage. Check your internet connection."
            )
        return ArvanStorageError(f"{action} failed: {error}")

    # -- Friendly API (no S3 jargon) ----------------------------------------

    def upload(
        self,
        local_path: PathLike,
        remote_path: Optional[str] = None,
        *,
        space: Optional[str] = None,
    ) -> str:
        """Upload a file from your computer to Arvan Storage."""
        path = Path(local_path)
        target = remote_path or path.name
        return self.upload_file(path, target, bucket=space)

    def download(
        self,
        remote_path: str,
        local_path: Optional[PathLike] = None,
        *,
        space: Optional[str] = None,
    ) -> Path:
        """Download a file from Arvan Storage to your computer."""
        destination = Path(local_path) if local_path else Path(Path(remote_path).name)
        return self.download_file(remote_path, destination, bucket=space)

    def browse(
        self,
        *,
        folder: str = "",
        space: Optional[str] = None,
    ) -> list[RemoteFile]:
        """List files inside a folder in your storage space."""
        prefix = folder.strip("/")
        if prefix:
            prefix += "/"

        response = self.list_objects(bucket=space, prefix=prefix, delimiter="/")
        files: list[RemoteFile] = []

        for item in response.get("Contents", []):
            key = item["Key"]
            if key == prefix or key.endswith("/"):
                continue
            name = key[len(prefix):] if prefix else key
            if "/" in name:
                continue
            modified = item.get("LastModified")
            if not isinstance(modified, datetime):
                modified = datetime.now()
            files.append(
                RemoteFile(
                    path=key,
                    name=name,
                    size=int(item.get("Size", 0)),
                    modified=modified,
                )
            )

        return sorted(files, key=lambda item: item.name.lower())

    def list_folders(
        self,
        *,
        folder: str = "",
        space: Optional[str] = None,
    ) -> list[str]:
        """List sub-folders inside a folder."""
        prefix = folder.strip("/")
        if prefix:
            prefix += "/"

        response = self.list_objects(bucket=space, prefix=prefix, delimiter="/")
        folders: list[str] = []
        for entry in response.get("CommonPrefixes", []):
            full = entry["Prefix"]
            name = full[len(prefix):].rstrip("/") if prefix else full.rstrip("/")
            if name:
                folders.append(name)
        return sorted(folders, key=str.lower)

    def list_spaces(self) -> list[str]:
        """List storage spaces available on your account."""
        return [bucket["Name"] for bucket in self.list_buckets()]

    def remove(self, remote_path: str, *, space: Optional[str] = None) -> None:
        """Delete a file from Arvan Storage."""
        self.delete_object(remote_path, bucket=space)

    def share_link(
        self,
        remote_path: str,
        *,
        space: Optional[str] = None,
        expires_in: int = 3600,
    ) -> str:
        """Create a temporary download link for a file."""
        return self.generate_presigned_url(
            remote_path,
            bucket=space,
            expiration=expires_in,
            method="get_object",
        )

    def upload_file(
        self,
        local_path: PathLike,
        key: str,
        *,
        bucket: Optional[str] = None,
        extra_args: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """Upload a local file to object storage."""
        path = Path(local_path)
        if not path.is_file():
            raise ArvanStorageError(f"Local file not found: {path}")

        resolved_bucket = self._resolve_bucket(bucket)
        upload_args: MutableMapping[str, Any] = dict(extra_args or {})
        if "ContentType" not in upload_args:
            content_type, _ = mimetypes.guess_type(path.name)
            if content_type:
                upload_args["ContentType"] = content_type

        try:
            self.client.upload_file(
                str(path),
                resolved_bucket,
                key,
                ExtraArgs=upload_args or None,
            )
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Upload", exc) from exc

        return key

    def upload_fileobj(
        self,
        fileobj: BinaryIO,
        key: str,
        *,
        bucket: Optional[str] = None,
        extra_args: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """Upload a file-like object to object storage."""
        resolved_bucket = self._resolve_bucket(bucket)
        try:
            self.client.upload_fileobj(
                fileobj,
                resolved_bucket,
                key,
                ExtraArgs=dict(extra_args or {}) or None,
            )
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Upload", exc) from exc
        return key

    def download_file(
        self,
        key: str,
        local_path: PathLike,
        *,
        bucket: Optional[str] = None,
    ) -> Path:
        """Download an object to a local file path."""
        path = Path(local_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        resolved_bucket = self._resolve_bucket(bucket)

        try:
            self.client.download_file(resolved_bucket, key, str(path))
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Download", exc) from exc

        return path

    def download_fileobj(
        self,
        key: str,
        fileobj: IO[bytes],
        *,
        bucket: Optional[str] = None,
    ) -> None:
        """Download an object into a writable binary file-like object."""
        resolved_bucket = self._resolve_bucket(bucket)
        try:
            self.client.download_fileobj(resolved_bucket, key, fileobj)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Download", exc) from exc

    def list_objects(
        self,
        *,
        bucket: Optional[str] = None,
        prefix: str = "",
        delimiter: str = "",
        max_keys: Optional[int] = None,
        continuation_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """List objects (and common prefixes) in a bucket."""
        resolved_bucket = self._resolve_bucket(bucket)
        params: dict[str, Any] = {
            "Bucket": resolved_bucket,
            "Prefix": prefix,
        }
        if delimiter:
            params["Delimiter"] = delimiter
        if max_keys is not None:
            params["MaxKeys"] = max_keys
        if continuation_token:
            params["ContinuationToken"] = continuation_token

        try:
            return self.client.list_objects_v2(**params)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("List objects", exc) from exc

    def iter_objects(
        self,
        *,
        bucket: Optional[str] = None,
        prefix: str = "",
    ) -> Iterator[dict[str, Any]]:
        """Iterate over all objects in a bucket under an optional prefix."""
        token: Optional[str] = None
        while True:
            response = self.list_objects(
                bucket=bucket,
                prefix=prefix,
                continuation_token=token,
            )
            for item in response.get("Contents", []):
                yield item
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")

    def head_object(
        self,
        key: str,
        *,
        bucket: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return metadata for an object without downloading its body."""
        resolved_bucket = self._resolve_bucket(bucket)
        try:
            return self.client.head_object(Bucket=resolved_bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Head object", exc) from exc

    def object_exists(
        self,
        key: str,
        *,
        bucket: Optional[str] = None,
    ) -> bool:
        """Return True if the object exists."""
        try:
            self.head_object(key, bucket=bucket)
            return True
        except ArvanStorageError as exc:
            if "404" in str(exc) or "Not Found" in str(exc) or "NoSuchKey" in str(exc):
                return False
            raise

    def delete_object(
        self,
        key: str,
        *,
        bucket: Optional[str] = None,
    ) -> None:
        """Delete a single object."""
        resolved_bucket = self._resolve_bucket(bucket)
        try:
            self.client.delete_object(Bucket=resolved_bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Delete object", exc) from exc

    def delete_objects(
        self,
        keys: Sequence[str],
        *,
        bucket: Optional[str] = None,
    ) -> dict[str, Any]:
        """Delete multiple objects in one request."""
        if not keys:
            return {"Deleted": [], "Errors": []}

        resolved_bucket = self._resolve_bucket(bucket)
        payload = {"Objects": [{"Key": key} for key in keys], "Quiet": False}
        try:
            return self.client.delete_objects(Bucket=resolved_bucket, Delete=payload)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Delete objects", exc) from exc

    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        *,
        source_bucket: Optional[str] = None,
        dest_bucket: Optional[str] = None,
        extra_args: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        """Copy an object within or across buckets."""
        resolved_source_bucket = self._resolve_bucket(source_bucket)
        resolved_dest_bucket = self._resolve_bucket(dest_bucket)
        copy_source = {"Bucket": resolved_source_bucket, "Key": source_key}
        params: dict[str, Any] = {
            "Bucket": resolved_dest_bucket,
            "Key": dest_key,
            "CopySource": copy_source,
        }
        if extra_args:
            params.update(extra_args)

        try:
            return self.client.copy_object(**params)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Copy object", exc) from exc

    def list_buckets(self) -> list[dict[str, Any]]:
        """List all buckets accessible to the credentials."""
        try:
            response = self.client.list_buckets()
            return response.get("Buckets", [])
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("List buckets", exc) from exc

    def create_bucket(
        self,
        bucket: str,
        *,
        region: Optional[str] = None,
    ) -> None:
        """Create a new bucket."""
        params: dict[str, Any] = {"Bucket": bucket}
        bucket_region = region or self.region_name
        if bucket_region and bucket_region != "default":
            params["CreateBucketConfiguration"] = {"LocationConstraint": bucket_region}

        try:
            self.client.create_bucket(**params)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Create bucket", exc) from exc

    def delete_bucket(
        self,
        bucket: str,
        *,
        force: bool = False,
    ) -> None:
        """Delete a bucket. When force=True, empties the bucket first."""
        if force:
            for item in self.iter_objects(bucket=bucket):
                self.delete_object(item["Key"], bucket=bucket)

        try:
            self.client.delete_bucket(Bucket=bucket)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Delete bucket", exc) from exc

    def generate_presigned_url(
        self,
        key: str,
        *,
        bucket: Optional[str] = None,
        expiration: int = 3600,
        method: str = "get_object",
        params: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """Generate a presigned URL for an object."""
        resolved_bucket = self._resolve_bucket(bucket)
        client_params = {"Bucket": resolved_bucket, "Key": key}
        if params:
            client_params.update(params)

        try:
            return self.client.generate_presigned_url(
                ClientMethod=method,
                Params=client_params,
                ExpiresIn=expiration,
            )
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Generate presigned URL", exc) from exc

    def put_object(
        self,
        key: str,
        body: Union[bytes, str],
        *,
        bucket: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> dict[str, Any]:
        """Upload raw bytes or text as an object."""
        resolved_bucket = self._resolve_bucket(bucket)
        payload = body.encode("utf-8") if isinstance(body, str) else body
        params: dict[str, Any] = {
            "Bucket": resolved_bucket,
            "Key": key,
            "Body": payload,
        }
        if content_type:
            params["ContentType"] = content_type
        if metadata:
            params["Metadata"] = dict(metadata)

        try:
            return self.client.put_object(**params)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Put object", exc) from exc

    def get_object(
        self,
        key: str,
        *,
        bucket: Optional[str] = None,
    ) -> dict[str, Any]:
        """Download an object's body and metadata."""
        resolved_bucket = self._resolve_bucket(bucket)
        try:
            return self.client.get_object(Bucket=resolved_bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise self._wrap_error("Get object", exc) from exc
