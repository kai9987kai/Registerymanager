"""Lossless text formatting and parsing for editable Windows registry values."""

from __future__ import annotations

from collections.abc import Sequence
import winreg


class RegistryCodecError(ValueError):
    """Raised when registry data cannot be represented by the selected type."""


REGISTRY_TYPE_NAMES = {
    winreg.REG_SZ: "REG_SZ",
    winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
    winreg.REG_MULTI_SZ: "REG_MULTI_SZ",
    winreg.REG_BINARY: "REG_BINARY",
    winreg.REG_DWORD: "REG_DWORD",
    winreg.REG_QWORD: "REG_QWORD",
}

SUPPORTED_REGISTRY_TYPES = tuple(REGISTRY_TYPE_NAMES)

_INTEGER_LIMITS = {
    winreg.REG_DWORD: (1 << 32) - 1,
    winreg.REG_QWORD: (1 << 64) - 1,
}


def registry_type_name(value_type: int) -> str:
    """Return the familiar Windows name for a supported registry type."""
    try:
        return REGISTRY_TYPE_NAMES[value_type]
    except KeyError as exc:
        raise RegistryCodecError(
            f"Unsupported registry value type: {value_type}"
        ) from exc


def _validate_unsigned_integer(value: object, value_type: int) -> int:
    type_name = registry_type_name(value_type)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RegistryCodecError(f"{type_name} data must be an integer.")

    maximum = _INTEGER_LIMITS[value_type]
    if not 0 <= value <= maximum:
        bits = 32 if value_type == winreg.REG_DWORD else 64
        raise RegistryCodecError(
            f"{type_name} must be an unsigned {bits}-bit integer "
            f"(0 to {maximum})."
        )
    return value


def format_registry_value(value: object, value_type: int) -> str:
    """Format registry data as editable text without changing its meaning."""
    type_name = registry_type_name(value_type)

    if value_type in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
        if not isinstance(value, str):
            raise RegistryCodecError(f"{type_name} data must be text.")
        return value

    if value_type == winreg.REG_MULTI_SZ:
        if (
            isinstance(value, (str, bytes, bytearray))
            or not isinstance(value, Sequence)
            or any(not isinstance(item, str) for item in value)
        ):
            raise RegistryCodecError("REG_MULTI_SZ data must be a sequence of strings.")
        return "\n".join(value)

    if value_type == winreg.REG_BINARY:
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise RegistryCodecError("REG_BINARY data must be bytes.")
        return " ".join(f"{byte:02X}" for byte in bytes(value))

    if value_type in _INTEGER_LIMITS:
        return str(_validate_unsigned_integer(value, value_type))

    # registry_type_name above rejects unsupported types. This is defensive.
    raise RegistryCodecError(f"Unsupported registry value type: {value_type}")


def parse_registry_value(text: str, value_type: int) -> object:
    """Parse editor text into the exact Python shape expected by ``winreg``."""
    type_name = registry_type_name(value_type)
    if not isinstance(text, str):
        raise RegistryCodecError("Registry editor input must be text.")

    if value_type in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
        return text

    if value_type == winreg.REG_MULTI_SZ:
        if text == "":
            return []
        # A textbox may supply platform newlines. Registry items remain one per
        # logical line, including intentional empty items between lines.
        return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    if value_type == winreg.REG_BINARY:
        try:
            return bytes.fromhex(text)
        except ValueError as exc:
            raise RegistryCodecError(
                "REG_BINARY must contain hexadecimal byte pairs, for example "
                "00 7F A2 FF."
            ) from exc

    if value_type in _INTEGER_LIMITS:
        stripped = text.strip()
        if not stripped:
            raise RegistryCodecError(f"{type_name} requires an integer value.")
        try:
            value = int(stripped, 0)
        except ValueError as exc:
            raise RegistryCodecError(
                f"{type_name} must be a decimal integer or use a prefix such as "
                "0x for hexadecimal."
            ) from exc
        return _validate_unsigned_integer(value, value_type)

    # registry_type_name above rejects unsupported types. This is defensive.
    raise RegistryCodecError(f"Unsupported registry value type: {value_type}")
