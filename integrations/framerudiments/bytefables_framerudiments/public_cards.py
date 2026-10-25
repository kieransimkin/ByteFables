"""PUBLIC QR recovery-card source generator for FrameRudiments (NOT wallet backups).

Renders exact black/white QR modules with white quiet zone, pinned host font and
human-transcribable public frame text. No filters, scaling or embedded effects.
FrameRudiments owns the registered renderer and downstream composition/export.
"""
from __future__ import annotations

import re
from PIL import Image, ImageDraw, ImageFont

BRIDGE = "bytefables.framerudiments.layer.v1"
FINGERPRINT = re.compile(r"bfrec1-[0-9a-f]{64}\Z")
SAFE = re.compile(r"[a-zA-Z0-9 _.:/+-]+\Z")


def _font(path, size):
    return ImageFont.truetype(path, size)


class PublicRecoveryCardRenderer:
    """Native generator with optical-safe crisp modules; requires a pinned font."""

    def __init__(self, size, style):
        if (not isinstance(size, (tuple, list)) or len(size) != 2 or
                any(type(v) is not int for v in size) or
                not 640 <= size[0] <= 4096 or not 960 <= size[1] <= 4096 or
                size[0] * size[1] > 12_000_000):
            raise ValueError("Public recovery cards require 640x960..4096x4096 bounds")
        self.size = tuple(size)
        expected = {"bridge_version", "format_id", "width", "height", "quiet_zone",
                    "modules", "caption", "fingerprint", "kind", "manual_text"}
        if type(style) is not dict or set(style) != expected or style.get("bridge_version") != BRIDGE:
            raise ValueError("Public card requires an exact known style schema")
        if style["format_id"] != "symbol/qr-model2":
            raise ValueError("Public card only supports QR Model 2")
        w, h, q = style["width"], style["height"], style["quiet_zone"]
        if (type(w) is not int or type(h) is not int or type(q) is not int or
                w != h or not 21 <= w <= 177 or (w - 21) % 4 or q < 4 or q > 32):
            raise ValueError("Invalid public QR geometry or quiet zone")
        modules = style["modules"]
        if type(modules) is not str or len(modules) != w * h or set(modules) - {"0", "1"}:
            raise ValueError("Invalid public QR modules")
        if type(style["fingerprint"]) is not str or not FINGERPRINT.fullmatch(style["fingerprint"]):
            raise ValueError("Full public record fingerprint required")
        for field in ("caption", "kind", "manual_text"):
            value = style[field]
            if (type(value) is not str or not 1 <= len(value) <= (3000 if field == "manual_text" else 180)
                    or SAFE.fullmatch(value) is None):
                raise ValueError(f"Invalid public card {field}")
        self.modules, self.width, self.quiet = modules, w, q
        self.kind = style["kind"]
        self.caption = style["caption"]
        self.fingerprint = style["fingerprint"]
        self.manual = style["manual_text"]
        self.font_path = None

    def prepare(self, project):
        font = getattr(project, "font_ref", None)
        if not isinstance(font, dict) or not font.get("path") or not font.get("sha256"):
            raise ValueError("A project-pinned SHA-256 font is required for a public card")
        self.font_path = font["path"]
        # Font loading is done via the FrameRudiments-verified font reference.
        _font(self.font_path, 14)

    def render(self, frame):
        if self.font_path is None:
            raise ValueError("Call prepare(project) with a SHA-256-pinned host font")
        width, height = self.size
        size = self.width + 2 * self.quiet
        # Ensure 1:1 integer-pitched black and white modules, no image resampling.
        pitch = min((width - 64) // size, (height - 460) // size)
        if pitch < 2:
            raise ValueError("Printed QR would have fewer than two pixels per module")
        qr_size = size * pitch
        start_x = (width - qr_size) // 2
        start_y = 135
        image = Image.new("RGBA", self.size, (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        scale = min(width / 1024, height / 1440)
        heading = _font(self.font_path, max(14, int(round(29 * scale))))
        body = _font(self.font_path, max(12, int(round(20 * scale))))
        foot = _font(self.font_path, max(11, int(round(15 * scale))))
        draw.text((32, 22), "BYTEFABLES / PUBLIC RECORD", font=heading, fill=(0, 0, 0, 255))
        draw.text((32, 72), self.caption, font=body, fill=(0, 0, 0, 255))
        for y in range(self.width):
            for x in range(self.width):
                if self.modules[y * self.width + x] == "1":
                    x0 = start_x + (x + self.quiet) * pitch
                    y0 = start_y + (y + self.quiet) * pitch
                    draw.rectangle((x0, y0, x0 + pitch - 1, y0 + pitch - 1), fill=(0, 0, 0, 255))
        footer = start_y + qr_size + 18
        draw.text((32, footer), "Type: " + self.kind, font=body, fill=(0, 0, 0, 255))
        footer += max(25, int(28 * scale))
        draw.text((32, footer), "Full typed public fingerprint:", font=body, fill=(0, 0, 0, 255))
        footer += max(25, int(28 * scale))
        for fragment in (self.fingerprint[:37], self.fingerprint[37:]):
            draw.text((32, footer), fragment, font=foot, fill=(0, 0, 0, 255))
            footer += max(19, int(20 * scale))
        footer += 8
        draw.text((32, footer), "Public frame text (manual transcription):", font=body, fill=(0, 0, 0, 255))
        footer += max(24, int(26 * scale))
        # Printable text wraps without deleting any data; reject if it cannot fit.
        char_width = max(1, draw.textbbox((0, 0), "M", font=foot)[2])
        wrap = max(8, (width - 64) // char_width)
        row_height = max(16, int(18 * scale))
        for offset in range(0, len(self.manual), wrap):
            if footer + row_height > height - 38:
                raise ValueError("Public frame text does not fit on this sheet; enlarge the print page")
            draw.text((32, footer), self.manual[offset:offset+wrap], font=foot, fill=(0, 0, 0, 255))
            footer += row_height
        # Safety text remains outside QR. No graphics or gradients touch its modules.
        draw.text((32, height - 30), "PUBLIC DATA ONLY - NOT AUTHENTICATION OR A WALLET BACKUP",
                  font=foot, fill=(0, 0, 0, 255))
        return image
