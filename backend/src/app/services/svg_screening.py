"""SVG upload screening for portal logos (FR-095, research.md R-27).

Three-layer defence, none of which is a new dependency (the constitution's
stack rule forbids adding one without an amendment):

1. This module — refuse a DOCTYPE before parsing at all, then reject any
   script element, event-handler attribute, or non-fragment reference.
2. media_router serves the result with `X-Content-Type-Options: nosniff`
   and a `default-src 'none'` content-security-policy header.
3. The frontend renders every logo through `<img>` only — never `<object>`,
   `<embed>`, or inline SVG — which is the layer that holds even if this
   one is wrong.

Refusing a DOCTYPE outright, rather than configuring the parser to ignore
it, forecloses the entity-expansion class of attack before xml.etree ever
sees the payload — see research.md R-27's CPython documentation citations.
"""

import xml.etree.ElementTree as ET

_SCRIPT_LIKE_TAGS = {"script", "foreignObject"}


class UnsafeSvgError(Exception):
    pass


def _local_name(tag: str) -> str:
    # ElementTree returns namespaced tags as "{uri}localname".
    return tag.rsplit("}", 1)[-1]


def screen_svg(data: bytes) -> None:
    """Raises UnsafeSvgError if `data` is not safe to store and serve as
    an SVG. Does not modify or return the input — a refused upload is
    refused outright (FR-095), not silently stripped."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsafeSvgError("Not valid UTF-8 SVG.") from exc

    if "<!doctype" in text.lower():
        raise UnsafeSvgError("SVG files with a DOCTYPE declaration are not accepted.")

    try:
        root = ET.fromstring(text)  # noqa: S314 -- DOCTYPE already refused above
    except ET.ParseError as exc:
        raise UnsafeSvgError("Not a well-formed SVG document.") from exc

    for element in root.iter():
        if _local_name(element.tag) in _SCRIPT_LIKE_TAGS:
            raise UnsafeSvgError(
                f"SVG elements of type <{_local_name(element.tag)}> are not accepted."
            )

        for attr_name, attr_value in element.attrib.items():
            local_attr = _local_name(attr_name)
            if local_attr.lower().startswith("on"):
                raise UnsafeSvgError(f"SVG attribute {local_attr!r} is not accepted.")
            if local_attr in ("href", "xlink:href") and not attr_value.startswith("#"):
                raise UnsafeSvgError(
                    "SVG href/xlink:href attributes must reference an in-document fragment."
                )
