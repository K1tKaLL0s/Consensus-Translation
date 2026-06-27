from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys


class LocalCredentialStore:
    def __init__(self, store_path: str | Path) -> None:
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

    def set_secret(self, credential_id: str, secret: str) -> None:
        data = self._load()
        data[credential_id] = self._protect(secret.encode("utf-8"))
        self._store_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_secret(self, credential_id: str) -> str:
        data = self._load()
        if credential_id not in data:
            raise KeyError(f"credential not found: {credential_id}")
        return self._unprotect(data[credential_id]).decode("utf-8")

    def _load(self) -> dict[str, str]:
        if not self._store_path.exists():
            return {}
        raw = json.loads(self._store_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        return {str(key): str(value) for key, value in raw.items()}

    def _protect(self, secret: bytes) -> str:
        if sys.platform == "win32":
            return "dpapi:" + base64.b64encode(_dpapi_protect(secret)).decode("ascii")
        return "local:" + base64.b64encode(secret[::-1]).decode("ascii")

    def _unprotect(self, payload: str) -> bytes:
        if payload.startswith("dpapi:"):
            return _dpapi_unprotect(base64.b64decode(payload.removeprefix("dpapi:")))
        if payload.startswith("local:"):
            return base64.b64decode(payload.removeprefix("local:"))[::-1]
        raise ValueError("unsupported credential payload")


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _make_blob(data: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def _blob_to_bytes(blob: _DataBlob) -> bytes:
    return ctypes.string_at(blob.pbData, blob.cbData)


def _dpapi_protect(data: bytes) -> bytes:
    in_blob, buffer = _make_blob(data)
    out_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return _blob_to_bytes(out_blob)
    finally:
        kernel32.LocalFree(out_blob.pbData)
        _ = buffer


def _dpapi_unprotect(data: bytes) -> bytes:
    in_blob, buffer = _make_blob(data)
    out_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return _blob_to_bytes(out_blob)
    finally:
        kernel32.LocalFree(out_blob.pbData)
        _ = buffer
