import unittest
import winreg

from registry_codec import (
    REGISTRY_TYPE_NAMES,
    SUPPORTED_REGISTRY_TYPES,
    RegistryCodecError,
    format_registry_value,
    parse_registry_value,
    registry_type_name,
)


class TestRegistryCodec(unittest.TestCase):
    def assert_round_trip(self, value, value_type):
        formatted = format_registry_value(value, value_type)
        self.assertEqual(parse_registry_value(formatted, value_type), value)

    def test_supported_type_names(self):
        expected = {
            winreg.REG_SZ: "REG_SZ",
            winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
            winreg.REG_MULTI_SZ: "REG_MULTI_SZ",
            winreg.REG_BINARY: "REG_BINARY",
            winreg.REG_DWORD: "REG_DWORD",
            winreg.REG_QWORD: "REG_QWORD",
        }
        self.assertEqual(REGISTRY_TYPE_NAMES, expected)
        self.assertEqual(set(SUPPORTED_REGISTRY_TYPES), set(expected))
        for value_type, name in expected.items():
            self.assertEqual(registry_type_name(value_type), name)

    def test_string_types_preserve_text_exactly(self):
        values = ["", "  surrounding whitespace  ", "Unicode: caf\u00e9 \U0001f680", "line 1\nline 2"]
        for value_type in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
            for value in values:
                with self.subTest(value_type=value_type, value=value):
                    self.assert_round_trip(value, value_type)

        expand_value = r"%SystemRoot%\System32;%TEMP%"
        self.assert_round_trip(expand_value, winreg.REG_EXPAND_SZ)

    def test_string_format_rejects_non_text_data(self):
        for value_type in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
            with self.subTest(value_type=value_type):
                with self.assertRaises(RegistryCodecError):
                    format_registry_value(123, value_type)

    def test_multi_string_uses_one_item_per_line(self):
        value = ["first", r"C:\Program Files\Example", "third", ""]
        formatted = format_registry_value(value, winreg.REG_MULTI_SZ)
        self.assertEqual(formatted, "first\nC:\\Program Files\\Example\nthird\n")
        self.assertEqual(parse_registry_value(formatted, winreg.REG_MULTI_SZ), value)

    def test_multi_string_normalizes_textbox_newlines(self):
        self.assertEqual(
            parse_registry_value("one\r\ntwo\rthree", winreg.REG_MULTI_SZ),
            ["one", "two", "three"],
        )
        self.assertEqual(parse_registry_value("", winreg.REG_MULTI_SZ), [])

    def test_multi_string_format_rejects_invalid_shapes(self):
        invalid_values = ["not-a-list", b"bytes", ["valid", 2]]
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(RegistryCodecError):
                    format_registry_value(value, winreg.REG_MULTI_SZ)

    def test_binary_formats_as_spaced_uppercase_hex(self):
        value = bytes([0x00, 0x01, 0x0A, 0x7F, 0xA2, 0xFF])
        self.assertEqual(
            format_registry_value(value, winreg.REG_BINARY),
            "00 01 0A 7F A2 FF",
        )
        self.assert_round_trip(value, winreg.REG_BINARY)
        self.assertEqual(format_registry_value(b"", winreg.REG_BINARY), "")
        self.assertEqual(parse_registry_value("", winreg.REG_BINARY), b"")

    def test_binary_parser_accepts_whitespace_and_contiguous_pairs(self):
        expected = bytes([0x00, 0x7F, 0xA2, 0xFF])
        self.assertEqual(
            parse_registry_value("00 7f\nA2\tff", winreg.REG_BINARY), expected
        )
        self.assertEqual(
            parse_registry_value("007fa2ff", winreg.REG_BINARY), expected
        )

    def test_binary_rejects_invalid_hex(self):
        for text in ("0", "GG", "00 1Z", "0x10"):
            with self.subTest(text=text):
                with self.assertRaises(RegistryCodecError):
                    parse_registry_value(text, winreg.REG_BINARY)
        with self.assertRaises(RegistryCodecError):
            format_registry_value("00 FF", winreg.REG_BINARY)

    def test_dword_parses_base_zero_and_round_trips_bounds(self):
        cases = {
            "0": 0,
            "42": 42,
            "0x2A": 42,
            "0o52": 42,
            "0b101010": 42,
            "  +42  ": 42,
            "0xFFFFFFFF": (1 << 32) - 1,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(
                    parse_registry_value(text, winreg.REG_DWORD), expected
                )
        self.assert_round_trip(0, winreg.REG_DWORD)
        self.assert_round_trip((1 << 32) - 1, winreg.REG_DWORD)

    def test_qword_parses_base_zero_and_round_trips_bounds(self):
        cases = {
            "0": 0,
            "18446744073709551615": (1 << 64) - 1,
            "0xFFFFFFFFFFFFFFFF": (1 << 64) - 1,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(
                    parse_registry_value(text, winreg.REG_QWORD), expected
                )
        self.assert_round_trip(0, winreg.REG_QWORD)
        self.assert_round_trip((1 << 64) - 1, winreg.REG_QWORD)

    def test_integer_types_reject_invalid_or_out_of_range_values(self):
        cases = (
            (winreg.REG_DWORD, "", None),
            (winreg.REG_DWORD, "not-a-number", None),
            (winreg.REG_DWORD, "-1", -1),
            (winreg.REG_DWORD, str(1 << 32), 1 << 32),
            (winreg.REG_QWORD, "-1", -1),
            (winreg.REG_QWORD, str(1 << 64), 1 << 64),
        )
        for value_type, text, value in cases:
            with self.subTest(value_type=value_type, text=text):
                with self.assertRaises(RegistryCodecError):
                    parse_registry_value(text, value_type)
                if value is not None:
                    with self.assertRaises(RegistryCodecError):
                        format_registry_value(value, value_type)

        for value_type in (winreg.REG_DWORD, winreg.REG_QWORD):
            with self.subTest(value_type=value_type):
                with self.assertRaises(RegistryCodecError):
                    format_registry_value(True, value_type)
                with self.assertRaises(RegistryCodecError):
                    format_registry_value("1", value_type)

    def test_unsupported_types_are_rejected(self):
        for operation in (
            lambda: registry_type_name(winreg.REG_NONE),
            lambda: format_registry_value(b"", winreg.REG_NONE),
            lambda: parse_registry_value("", winreg.REG_NONE),
        ):
            with self.assertRaises(RegistryCodecError):
                operation()

    def test_parser_requires_text_input(self):
        with self.assertRaises(RegistryCodecError):
            parse_registry_value(123, winreg.REG_SZ)


if __name__ == "__main__":
    unittest.main()
