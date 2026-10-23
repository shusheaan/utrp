"""Generate the current CLAP embedded theme, without installing a JSFX product.

The historical generated-file comment is retained for byte-identical assets.
"""
from pathlib import Path
import re
import tomllib


def controls(source: Path) -> dict[str, int | str]:
    raw = tomllib.loads((source / "theme.toml").read_text())["controls"]
    result: dict[str, int | str] = {}
    for name in ("off", "on", "foreground"):
        value = raw[name]
        if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            raise ValueError(f"Invalid controls {name}")
        result[name] = value
    for name, low, high in (("font_size", 12, 20), ("size", 29, 29), ("gap", 0, 10),
                            ("margin", 18, 18), ("key_gap", 0, 12)):
        value = raw[name]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"Invalid controls {name}")
        result[name] = value
    return result


def make_controls_header(source: Path) -> str:
    values = controls(source)
    raw = tomllib.loads((source / "theme.toml").read_text())
    background = raw["background"]
    if not isinstance(background, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", background):
        raise ValueError("Invalid background color")
    values["background"] = background
    for role in ("root", "third", "fifth", "seventh"):
        color = raw[role]
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ValueError(f"Invalid capsule {role} color")
        values[f"capsule_{role}"] = color
    for role in ("background", "border", "text", "muted", "key", "chord", "reason", "demo", "error"):
        color = raw["game"][role]
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ValueError(f"Invalid game {role} color")
        values[f"game_{role}"] = color
    for role in ("button_selected", "text_selected"):
        color = raw[role]
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ValueError(f"Invalid {role} color")
        values[f"choice_{role}"] = color
    for name, low, high in (("height", 29, 29), ("font_size", 8, 12)):
        value = raw["choices"][name]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"Invalid choices {name}")
        values[f"choice_{name}"] = value
    inset = raw["choices"]["inset"]
    if isinstance(inset, bool) or not isinstance(inset, int) or not 2 <= inset <= 4:
        raise ValueError("Invalid choices inset")
    values["selection_inset"] = inset
    for axis in ("x", "y"):
        name = f"padding_{axis}"
        value = raw["editor"][name]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 64:
            raise ValueError(f"Invalid editor {name}")
        values[name] = value
    for name, low, high in (("outer_margin", 20, 40), ("score_top", 12, 32),
                            ("score_height", 48, 64), ("score_bottom_gap", 12, 32),
                            ("key_gap", 8, 24), ("step_gap", 4, 12), ("group_gap", 8, 24),
                            ("dense_key_gap", 4, 8), ("dense_step_gap", 1, 4),
                            ("dense_group_gap", 2, 8), ("method_height", 16, 22),
                            ("dense_method_height", 14, 18)):
        value = raw["game_layout"][name]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"Invalid game_layout {name}")
        values[f"game_{name}"] = value
    settle = raw["interaction"]["focus_settle_ms"]
    if isinstance(settle, bool) or not isinstance(settle, int) or not 0 <= settle <= 2000:
        raise ValueError("Invalid focus_settle_ms")
    values["focus_settle_ms"] = settle
    lines = ["#pragma once", "// Generated from chordlab/theme.toml.", "namespace chordlabStyle {"]
    for name, value in values.items():
        if isinstance(value, str):
            lines.append(f"inline constexpr unsigned {name} = 0xff{value[1:]};")
        else:
            lines.append(f"inline constexpr int {name} = {value};")
    return "\n".join(lines + ["}", ""])


def make_theme(source: Path) -> str:
    raw = tomllib.loads((source / "theme.toml").read_text())
    lines = ["// Generated from theme.toml by install.py. Do not edit independently.", "@init"]
    for role in ("root", "third", "fifth", "seventh", "ninth", "external", "background", "diagram_background", "button",
                 "button_hover", "button_selected", "text", "text_muted", "text_selected",
                 "key_white", "key_black", "key_black_inner", "key_divider", "octave_label", "staff_line", "notation",
                 "guitar_nut", "guitar_fret", "guitar_string", "note_text", "active_note_ring", "note_idle_base"):
        color = raw[role]
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ValueError(f"Invalid {role} color")
        lines.append(f"{role}_color=$x{color[1:].upper()};")
    palette = raw["dark"]
    roles = ("root", "third", "fifth", "seventh", "ninth", "external", "diagram_background", "key_white", "key_black", "key_black_inner", "key_divider", "octave_label",
             "staff_line", "notation", "guitar_nut", "guitar_fret", "guitar_string", "note_text")
    if set(palette) != set(roles):
        raise ValueError("Dark palette must contain exactly the diagram and note color roles")
    lines.append("function apply_theme(dark) (")
    for role in roles:
        color = palette[role]
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ValueError(f"Invalid dark {role} color")
        lines.append(f"  {role}_color=dark ? $x{color[1:].upper()} : $x{raw[role][1:].upper()};")
    lines.append(");")
    line_width = raw["dark_diagram_line_width"]
    if isinstance(line_width, bool) or not isinstance(line_width, int) or not 1 <= line_width <= 3:
        raise ValueError("dark_diagram_line_width must be an integer in 1..3")
    lines.append(f"dark_diagram_line_width={line_width};")
    for name, lower, upper in (("note_idle_mix", 0.2, 0.85),
                               ("active_note_glow_mix", 0.2, 0.7),
                               ("active_note_glow_outer_alpha", 0.05, 0.25),
                               ("active_note_glow_inner_alpha", 0.2, 0.5)):
        value = raw[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= value <= upper:
            raise ValueError(f"{name} must be in {lower}..{upper}")
        lines.append(f"{name}={value};")
    for name, low, high in (("height", 29, 29), ("font_size", 8, 12), ("inset", 2, 4)):
        value = raw["choices"][name]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"Invalid choices {name}")
        lines.append(f"choices_{name}={value};")
    layout = controls(source)
    reserve = sum(int(layout[name]) * count for name, count in
                  (("margin", 2), ("size", 2), ("gap", 1), ("key_gap", 1)))
    lines.append(f"key_choices_reserve={reserve};")
    scale = raw["font_scale"]
    if not isinstance(scale, (int, float)) or not 1 <= scale <= 2:
        raise ValueError("font_scale must be in 1..2")
    lines.append(f"font_scale={scale};")
    for name in ("piano_height_ratio", "guitar_height_ratio", "staff_clef_scale", "staff_accidental_scale"):
        value = raw[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.25 <= value <= 1:
            raise ValueError(f"{name} must be in 0.25..1")
        lines.append(f"{name}={value};")
    for name, lower, upper in (("active_note_ring_width", 0.4, 1.5), ("active_note_glow_width", 1, 3.5), ("note_radius", 5, 9), ("note_font_size", 9, 15), ("staff_accidental_gap", 20, 40)):
        value = raw[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= value <= upper:
            raise ValueError(f"{name} must be in {lower}..{upper}")
        lines.append(f"{name}={value};")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    source = Path(__file__).resolve().parent
    (source / "theme.jsfx-inc").write_text(make_theme(source))
