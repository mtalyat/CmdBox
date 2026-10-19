from __future__ import annotations

import json
from pathlib import Path

import wx

from app.models.config_models import CommandButtonConfig
from app.services.runtime_paths import app_root, icons_dir


ICON_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".ico", ".gif")
ICON_DEFAULTS_FILE = "icon-default-colors.json"
_DEFAULT_ICON_COLORS_CACHE: dict[str, str] | None = None


def _parse_hex_color(value: str) -> tuple[int, int, int] | None:
    raw = value.strip()
    if not raw:
        return None

    if raw.startswith("#"):
        raw = raw[1:]

    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)

    if len(raw) != 6:
        return None

    try:
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except ValueError:
        return None


def normalize_hex_color(value: str, fallback: str = "#FFFFFF") -> str:
    parsed = _parse_hex_color(value)
    if parsed is None:
        return fallback
    r, g, b = parsed
    return f"#{r:02X}{g:02X}{b:02X}"


def button_icon_color(button_cfg: CommandButtonConfig) -> str:
    custom = normalize_hex_color(button_cfg.icon_custom_color, "")
    if custom:
        return custom
    default_color = configured_icon_default_color(button_cfg.icon_value)
    if default_color:
        return default_color
    return normalize_hex_color(button_cfg.icon_default_color, "#FFFFFF")


def _icon_default_colors_path() -> Path:
    return app_root() / "icons" / ICON_DEFAULTS_FILE


def _normalize_color_map(data: object) -> dict[str, str]:
    if not isinstance(data, dict):
        return {}

    out: dict[str, str] = {}
    for raw_key, raw_value in data.items():
        key = str(raw_key).strip().lower()
        if not key:
            continue
        normalized_color = normalize_hex_color(str(raw_value), "")
        if normalized_color:
            out[key] = normalized_color
    return out


def _icon_lookup_keys(icon_value: str) -> list[str]:
    raw = icon_value.strip()
    if not raw:
        return []

    keys = [raw.lower()]
    p = Path(raw)
    keys.append(p.name.lower())
    keys.append(p.stem.lower())
    return [k for i, k in enumerate(keys) if k and k not in keys[:i]]


def _load_configured_icon_default_colors() -> dict[str, str]:
    global _DEFAULT_ICON_COLORS_CACHE
    if _DEFAULT_ICON_COLORS_CACHE is not None:
        return _DEFAULT_ICON_COLORS_CACHE

    path = _icon_default_colors_path()
    if not path.exists() or not path.is_file():
        _DEFAULT_ICON_COLORS_CACHE = {}
        return _DEFAULT_ICON_COLORS_CACHE

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _DEFAULT_ICON_COLORS_CACHE = {}
        return _DEFAULT_ICON_COLORS_CACHE

    _DEFAULT_ICON_COLORS_CACHE = _normalize_color_map(payload)
    return _DEFAULT_ICON_COLORS_CACHE


def configured_icon_default_color(icon_value: str) -> str:
    color_map = _load_configured_icon_default_colors()
    for key in _icon_lookup_keys(icon_value):
        if key in color_map:
            return color_map[key]
    return ""


def discover_icons() -> list[tuple[str, Path]]:
    root = icons_dir()
    if not root.exists() or not root.is_dir():
        return []

    out: list[tuple[str, Path]] = []
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if p.is_file() and p.suffix.lower() in ICON_EXTENSIONS:
            out.append((p.stem, p))
    return out


def resolve_icon_image(icon_value: str) -> wx.Image | None:
    raw = icon_value.strip()
    if not raw:
        return None

    p = Path(raw)
    if p.exists() and p.is_file():
        img = wx.Image(str(p))
        if img.IsOk():
            return img

    icon_root = icons_dir()
    if not p.is_absolute() and icon_root.exists() and icon_root.is_dir():
        if p.suffix:
            candidate = icon_root / p.name
            if candidate.exists() and candidate.is_file():
                img = wx.Image(str(candidate))
                if img.IsOk():
                    return img
        else:
            for ext in ICON_EXTENSIONS:
                candidate = icon_root / f"{raw}{ext}"
                if candidate.exists() and candidate.is_file():
                    img = wx.Image(str(candidate))
                    if img.IsOk():
                        return img

    return None


def tint_grayscale_image(image: wx.Image, color_hex: str) -> wx.Image:
    target = _parse_hex_color(color_hex)
    if target is None:
        return image

    target_r, target_g, target_b = target
    tinted = image.Copy()
    data = bytearray(tinted.GetData())
    alpha_data = bytearray(tinted.GetAlpha()) if tinted.HasAlpha() else None
    has_mask = tinted.HasMask()
    mask_rgb: tuple[int, int, int] | None = None
    if has_mask:
        mask_rgb = (tinted.GetMaskRed(), tinted.GetMaskGreen(), tinted.GetMaskBlue())

    for i in range(0, len(data), 3):
        r = data[i]
        g = data[i + 1]
        b = data[i + 2]
        pixel_index = i // 3

        if alpha_data is not None and alpha_data[pixel_index] == 0:
            continue

        if mask_rgb is not None and (r, g, b) == mask_rgb:
            continue

        if not (r == g == b):
            continue

        gray = max(0, min(255, int((r + g + b) / 3)))
        data[i] = int((target_r * gray) / 255)
        data[i + 1] = int((target_g * gray) / 255)
        data[i + 2] = int((target_b * gray) / 255)

    tinted.SetData(bytes(data))
    if alpha_data is not None:
        tinted.SetAlpha(bytes(alpha_data))
    return tinted


def resolve_button_bitmap(
    button_cfg: CommandButtonConfig,
    size: tuple[int, int],
    art_client: str = wx.ART_BUTTON,
) -> wx.Bitmap | None:
    icon_value = button_cfg.icon_value.strip()
    if not icon_value:
        return None

    image = resolve_icon_image(icon_value)
    if image and image.IsOk():
        scaled = image.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH)
        colored = tint_grayscale_image(scaled, button_icon_color(button_cfg))
        return wx.Bitmap(colored)

    art_id = getattr(wx, icon_value, None)
    if art_id:
        bmp = wx.ArtProvider.GetBitmap(art_id, art_client, size)
        if bmp and bmp.IsOk():
            return bmp

    return None
