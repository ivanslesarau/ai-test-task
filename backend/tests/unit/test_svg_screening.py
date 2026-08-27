import pytest

from app.services.svg_screening import UnsafeSvgError, screen_svg

_CLEAN_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" fill="#ff0000"/>
</svg>"""

_CLEAN_SVG_WITH_FRAGMENT_HREF = b"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink">
  <defs><linearGradient id="g"/></defs>
  <use xlink:href="#g"/>
</svg>"""


def test_clean_svg_passes() -> None:
    screen_svg(_CLEAN_SVG)


def test_clean_svg_with_fragment_reference_passes() -> None:
    screen_svg(_CLEAN_SVG_WITH_FRAGMENT_HREF)


def test_rejects_inline_script_element() -> None:
    payload = b"""<svg xmlns="http://www.w3.org/2000/svg">
      <script>alert(1)</script>
    </svg>"""
    with pytest.raises(UnsafeSvgError):
        screen_svg(payload)


def test_rejects_foreign_object() -> None:
    payload = b"""<svg xmlns="http://www.w3.org/2000/svg">
      <foreignObject><iframe src="https://evil.example"/></foreignObject>
    </svg>"""
    with pytest.raises(UnsafeSvgError):
        screen_svg(payload)


def test_rejects_event_handler_attribute() -> None:
    payload = b"""<svg xmlns="http://www.w3.org/2000/svg">
      <circle cx="1" cy="1" r="1" onload="alert(1)"/>
    </svg>"""
    with pytest.raises(UnsafeSvgError):
        screen_svg(payload)


def test_rejects_external_href_reference() -> None:
    payload = b"""<svg xmlns="http://www.w3.org/2000/svg"
         xmlns:xlink="http://www.w3.org/1999/xlink">
      <image xlink:href="https://evil.example/tracker.png"/>
    </svg>"""
    with pytest.raises(UnsafeSvgError):
        screen_svg(payload)


def test_rejects_doctype_with_entity_before_parsing() -> None:
    payload = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>'
    )
    with pytest.raises(UnsafeSvgError):
        screen_svg(payload)


def test_rejects_malformed_xml() -> None:
    with pytest.raises(UnsafeSvgError):
        screen_svg(b"<svg><unclosed></svg>")


def test_rejects_non_utf8_bytes() -> None:
    with pytest.raises(UnsafeSvgError):
        screen_svg(b"\xff\xfe\x00\x01")
