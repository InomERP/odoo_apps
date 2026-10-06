# -*- coding: utf-8 -*-
"""Small compatibility helpers for Odoo 20 binary values."""

import base64


def binary_content(value):
    """Return raw bytes from an Odoo 20 BinaryValue or legacy/base64 value."""
    if not value:
        return b""
    content = getattr(value, "content", None)
    if content is not None:
        return bytes(content)
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, bytes):
        # Binary fields read from Odoo 19 used base64 bytes. Odoo 20 BinaryValue
        # is handled above; keep this fallback tolerant for old/custom callers.
        try:
            return base64.b64decode(value, validate=True)
        except Exception:
            return value
    if isinstance(value, str):
        try:
            return base64.b64decode(value, validate=True)
        except Exception:
            return value.encode()
    return bytes(value)
