from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("chordlab_theme", SOURCE / "generate_theme.py")
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)



def test_theme_is_generated_consistently() -> None:
    assert module.make_theme(SOURCE) == (SOURCE / "theme.jsfx-inc").read_text()


def luminance(color: str) -> float:
    channels = tuple(int(color[index:index + 2], 16) / 255 for index in (1, 3, 5))
    linear = tuple(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
                   for value in channels)
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def test_race_palette_is_black_and_does_not_change_normal_renderer() -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())
    assert theme["game"]["background"] == "#000000"
    assert theme["background"] == "#585858"
    assert "game_" not in module.make_theme(SOURCE)
    header = module.make_controls_header(SOURCE)
    for role, color in theme["game"].items():
        assert f"game_{role} = 0xff{color[1:]};" in header
        if role not in ("background", "border"):
            assert (luminance(color) + 0.05) / 0.05 >= 7


@pytest.mark.parametrize("value", ['"#fff"', '"#GGGGGG"', "123"])
def test_race_palette_rejects_invalid_colors(tmp_path: Path, value: str) -> None:
    text = (SOURCE / "theme.toml").read_text().replace('key = "#68DCE8"', f'key = {value}')
    (tmp_path / "theme.toml").write_text(text)
    with pytest.raises(ValueError, match="game key"):
        module.make_controls_header(tmp_path)


def test_bitwig_neutrals_preserve_light_diagrams() -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())
    assert theme["background"] == "#585858"
    assert theme["button"] == "#494949"
    assert theme["diagram_background"] == "#E9EDF0"


def test_dark_palette_is_complete_and_generated() -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())
    assert theme["dark"]["diagram_background"] == theme["background"]
    generated = module.make_theme(SOURCE)
    for role, color in theme["dark"].items():
        assert f"{role}_color=dark ? $x{color[1:]} : $x{theme[role][1:]};" in generated


@pytest.mark.parametrize("role", ["notation", "octave_label", "note_text"])
def test_dark_diagram_foreground_contrast(role: str) -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())["dark"]
    assert (luminance(theme[role]) + 0.05) / (luminance(theme["diagram_background"]) + 0.05) >= 4.5


@pytest.mark.parametrize("value", ['"#fff"', '"#GGGGGG"', "123"])
def test_dark_palette_rejects_invalid_colors(tmp_path: Path, value: str) -> None:
    text = (SOURCE / "theme.toml").read_text().replace('notation = "#D1D5DA"', f'notation = {value}')
    (tmp_path / "theme.toml").write_text(text)
    with pytest.raises(ValueError, match="dark notation"):
        module.make_theme(tmp_path)


def test_appearance_parameter_is_appended_and_defaults_dark() -> None:
    source = (SOURCE / "chordlab.jsfx").read_text()
    assert 'slider18:1<0,1,1>-Sustain lock (read only)' in source
    assert 'slider19:0<0,1,1{Dark,Bright}>-Appearance' in source
    assert 'theme_dark=slider19<0.5;' in source


@pytest.mark.parametrize("foreground,background", [
    ("text", "button"), ("text", "button_hover"),
    ("text_muted", "button"), ("text_muted", "background"),
    ("text_selected", "button_selected"),
])
def test_dark_panel_label_contrast(foreground: str, background: str) -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())
    light, dark = sorted((luminance(theme[foreground]), luminance(theme[background])), reverse=True)
    assert (light + 0.05) / (dark + 0.05) >= 4.5


def test_shared_diagram_background_is_configurable(tmp_path: Path) -> None:
    text = (SOURCE / "theme.toml").read_text().replace(
        'diagram_background = "#E9EDF0"', 'diagram_background = "#fafafa"'
    )
    (tmp_path / "theme.toml").write_text(text)
    assert "diagram_background_color=$xFAFAFA;" in module.make_theme(tmp_path)


@pytest.mark.parametrize("value", ['"#fff"', '"#GGGGGG"', "123"])
def test_shared_diagram_background_rejects_invalid_colors(tmp_path: Path, value: str) -> None:
    text = (SOURCE / "theme.toml").read_text().replace(
        'diagram_background = "#E9EDF0"', f"diagram_background = {value}"
    )
    (tmp_path / "theme.toml").write_text(text)
    with pytest.raises(ValueError, match="diagram_background"):
        module.make_theme(tmp_path)


@pytest.mark.parametrize("name", ["piano_height_ratio", "guitar_height_ratio", "staff_clef_scale", "staff_accidental_scale"])
@pytest.mark.parametrize("value", ["0.24", "1.01", "true", '"small"', "nan", "inf"])
def test_diagram_scales_reject_invalid_values(tmp_path: Path, name: str, value: str) -> None:
    lines = (SOURCE / "theme.toml").read_text().splitlines()
    (tmp_path / "theme.toml").write_text("\n".join(
        f"{name} = {value}" if line.startswith(f"{name} =") else line for line in lines
    ))
    with pytest.raises(ValueError, match=name):
        module.make_theme(tmp_path)


def test_diagram_scales_are_generated() -> None:
    theme = module.make_theme(SOURCE)
    assert "piano_height_ratio=0.5;" in theme
    assert "guitar_height_ratio=0.5;" in theme
    assert "staff_clef_scale=0.56;" in theme
    assert "staff_accidental_scale=0.75;" in theme
    assert "staff_accidental_gap=34;" in theme


@pytest.mark.parametrize("name", ["note_radius", "note_font_size"])
@pytest.mark.parametrize("value", ["0", "16", "true", '\"small\"', "nan", "inf"])
def test_note_sizes_reject_invalid_values(tmp_path: Path, name: str, value: str) -> None:
    lines = (SOURCE / "theme.toml").read_text().splitlines()
    (tmp_path / "theme.toml").write_text("\n".join(
        f"{name} = {value}" if line.startswith(f"{name} =") else line for line in lines
    ))
    with pytest.raises(ValueError, match=name):
        module.make_theme(tmp_path)


@pytest.mark.parametrize("value", ["19", "41", "true", '\"left\"', "nan", "inf"])
def test_accidental_gap_rejects_invalid_values(tmp_path: Path, value: str) -> None:
    text = (SOURCE / "theme.toml").read_text().replace(
        "staff_accidental_gap = 34", f"staff_accidental_gap = {value}"
    )
    (tmp_path / "theme.toml").write_text(text)
    with pytest.raises(ValueError, match="staff_accidental_gap"):
        module.make_theme(tmp_path)


def test_dark_black_keys_are_solid_black() -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())["dark"]
    for role in ("key_black", "key_black_inner"):
        color = theme[role]
        assert color == "#000000"
        assert luminance(color) < luminance(theme["key_white"])


def test_dark_white_keys_match_background_with_clear_borders() -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())
    dark = theme["dark"]
    assert dark["key_white"] == dark["diagram_background"] == theme["background"]
    assert theme["key_white"] == theme["diagram_background"] == "#E9EDF0"
    assert dark["diagram_background"] == "#585858"
    assert (luminance(dark["key_divider"]) + 0.05) / (luminance(dark["key_white"]) + 0.05) >= 3
    for role in ("octave_label",):
        assert (luminance(dark[role]) + 0.05) / (luminance(dark["key_white"]) + 0.05) >= 4.5
    ui = (SOURCE / "ui.jsfx-inc").read_text()
    assert "ink(key_white_color,1); gfx_rect(left,y,right-left,h);" in ui
    assert "gfx_rect(left,y,dark_diagram_line_width,h)" in ui


@pytest.mark.parametrize("value", ['"#fff"', '"#GGGGGG"', "123"])
def test_dark_white_key_rejects_invalid_color(tmp_path: Path, value: str) -> None:
    text = (SOURCE / "theme.toml").read_text().replace('key_white = "#585858"', f'key_white = {value}')
    (tmp_path / "theme.toml").write_text(text)
    with pytest.raises(ValueError, match="dark key_white"):
        module.make_theme(tmp_path)


@pytest.mark.parametrize("role", ["root", "third", "fifth", "seventh", "ninth", "external"])
def test_note_fills_keep_white_labels_legible_in_both_modes(role: str) -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())
    for palette in (theme, theme["dark"]):
        assert palette["note_text"] == "#FFFFFF"
        active = luminance(palette[role])
        assert 1.05 / (active + 0.05) >= 4.5
        if role != "external":
            idle = "#" + "".join(f"{round((1-theme['note_idle_mix']) * int(theme['note_idle_base'][i:i+2],16) + theme['note_idle_mix'] * int(palette[role][i:i+2],16)):02X}" for i in (1,3,5))
            assert 1.05 / (luminance(idle) + .05) >= 4.5
            assert 1 < luminance(idle) / active < 1.3
            idle_channels = tuple(int(idle[i:i+2],16) for i in (1,3,5))
            active_channels = tuple(int(palette[role][i:i+2],16) for i in (1,3,5))
            assert max(idle_channels)-min(idle_channels) < max(active_channels)-min(active_channels)


def test_note_labels_never_change_color_or_size_on_press() -> None:
    ui = (SOURCE / "ui.jsfx-inc").read_text()
    renderer = ui[ui.index("function note_dot("):ui.index("function keyboard_black_width(")]
    assert "ink(note_text_color,1);" in renderer
    assert "$x111111" not in renderer
    assert "radius-=" not in renderer and "radius+=" not in renderer
    assert "size=note_font_size*radius/note_radius;" in renderer
    assert "lit ? active_note_halo(x,y,radius,role,ring);" in renderer


def test_dark_diagram_lines_match_staff_weight() -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())
    assert theme["dark_diagram_line_width"] == 2
    assert theme["dark"]["key_divider"] == theme["dark"]["guitar_fret"] == theme["dark"]["staff_line"]
    assert "dark_diagram_line_width=2;" in module.make_theme(SOURCE)
    ui = (SOURCE / "ui.jsfx-inc").read_text()
    assert "gfx_rect(left,y,dark_diagram_line_width,h)" in ui
    assert "gfx_rect(x+w-dark_diagram_line_width,y,dark_diagram_line_width,h)" in ui
    assert "fret==0 ? 3 : theme_dark ? dark_diagram_line_width : 1" in ui


@pytest.mark.parametrize("value", ["0", "4", "2.5", "true", "nan", "inf", '\"thick\"'])
def test_dark_diagram_line_width_is_bounded(tmp_path: Path, value: str) -> None:
    text = (SOURCE / "theme.toml").read_text().replace("dark_diagram_line_width = 2", f"dark_diagram_line_width = {value}")
    (tmp_path / "theme.toml").write_text(text)
    with pytest.raises(ValueError, match="dark_diagram_line_width"):
        module.make_theme(tmp_path)


def test_editor_has_no_fake_rounded_corner_surround() -> None:
    source = (SOURCE.parent / "chordlab_clap/editor.cpp").read_text()
    assert "paintOverChildren" not in source
    assert "panelSurround" not in source


def test_circular_controls_share_config_and_header_geometry() -> None:
    config = module.controls(SOURCE)
    assert config['gap'] == config['key_gap'] == 0
    header = module.make_controls_header(SOURCE)
    assert f"font_size = {config['font_size']};" in header
    assert "foreground = 0xffFFFFFF;" in header
    assert f"off = 0xff{config['off'][1:]};" in header
    assert f"on = 0xff{config['on'][1:]};" in header
    reserve = 2 * config['margin'] + 2 * config['size'] + config['gap'] + config['key_gap']
    assert f"key_choices_reserve={reserve};" in module.make_theme(SOURCE)
    for width in range(700, 1601):
        start = config['margin']
        end = start + width - reserve
        capture = width - config['margin'] - config['size']
        sustain = capture - config['gap'] - config['size']
        assert sustain - end == config['key_gap']
        assert capture - (sustain + config['size']) == config['gap']
        assert end == sustain
        assert sustain + config['size'] == capture
        assert (end - start) / 12 > 45
    button = (SOURCE.parent / 'chordlab_clap/state_button.h').read_text()
    assert 'fillEllipse(bounds.toFloat().reduced(float(chordlabStyle::selection_inset) + 0.5f))' in button
    assert 'fillRect' not in button and 'addRoundedRectangle' not in button
    assert 'drawText(getButtonText(), bounds, juce::Justification::centred, false)' in button
    assert config['size'] == 29  # Matches the adjacent key buttons in draw_key_choices.
    ui = (SOURCE / 'ui.jsfx-inc').read_text()
    assert 'choice_button(x,y,w,#text' in ui
    editor = (SOURCE.parent / 'chordlab_clap/editor.h').read_text()
    assert 'StateButton game{"G"}, sustain{"S"}, capture{"A"}' in editor
    for state in ('off', 'on'):
        assert (luminance(config['foreground']) + .05) / (luminance(config[state]) + .05) >= 4.5


def test_state_letters_are_smaller_and_regular_weight() -> None:
    config = module.controls(SOURCE)
    button = (SOURCE.parent / 'chordlab_clap/state_button.h').read_text()
    assert config['font_size'] == 14
    assert 'juce::Font::plain' in button
    assert 'juce::Font::bold' not in button
    assert 'colour.brighter(0.04f)' in button


@pytest.mark.parametrize("state,previous", [('off', '#9B3542'), ('on', '#267044')])
def test_state_fills_are_softer_but_labels_remain_readable(state: str, previous: str) -> None:
    config = module.controls(SOURCE)
    colour = config[state]
    assert luminance(colour) > luminance(previous)
    channels = tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))
    # Lower chroma than the previous saturated red/green; preserve white small-label contrast.
    assert max(channels) - min(channels) < 55
    hover = '#' + ''.join(f'{int(255 - (255 - value) / 1.04):02X}' for value in channels)
    assert (luminance(config['foreground']) + .05) / (luminance(hover) + .05) >= 4.5


@pytest.mark.parametrize("name,value", [("font_size", "100"), ("size", "true"), ("size", "24"),
                                       ("gap", "-1"), ("key_gap", "-1"), ("off", '\"#GGGGGG\"'), ("foreground", '\"white\"')])
def test_square_controls_validate_boundaries(tmp_path: Path, name: str, value: str) -> None:
    text = (SOURCE / 'theme.toml').read_text()
    lines = [f"{name} = {value}" if line.startswith(f"{name} =") else line for line in text.splitlines()]
    (tmp_path / 'theme.toml').write_text('\n'.join(lines))
    with pytest.raises(ValueError, match=f"controls {name}"):
        module.make_controls_header(tmp_path)


@pytest.mark.parametrize("value", ["0.19", "0.9", "true", "nan"])
def test_idle_brightness_is_bounded(tmp_path: Path, value: str) -> None:
    text = (SOURCE / 'theme.toml').read_text().replace('note_idle_mix = 0.8', f'note_idle_mix = {value}')
    (tmp_path / 'theme.toml').write_text(text)
    with pytest.raises(ValueError, match='note_idle_mix'):
        module.make_theme(tmp_path)


def test_idle_notes_have_no_preselected_region_style() -> None:
    ui = (SOURCE / "ui.jsfx-inc").read_text()
    renderer = ui[ui.index("function note_dot("):ui.index("function keyboard_black_width(")]
    for removed in ("candidate", "guitar_current", "guitar_region_contains", "voicing_mode"):
        assert removed not in renderer
    assert "role_ink(role,lit)" in renderer
    assert "guitar_candidate_mix" not in module.make_theme(SOURCE)
    assert "guitar_candidate_mix" not in (SOURCE / "theme.toml").read_text()


def test_white_ring_marks_sounding_scale_notes_not_static_grips() -> None:
    ui = (SOURCE / "ui.jsfx-inc").read_text()
    assert "lit=(sounding && own[note]) || hw>0" in ui
    assert "ring=lit && display_role(note,1)>=0" in ui
    assert "note_circle(x,y,radius+active_note_ring_width);" in ui
    assert "note_circle(x,y,radius+active_note_ring_width+active_note_glow_width);" in ui
    assert "shape[6-string]" not in ui
    theme = module.make_theme(SOURCE)
    assert "active_note_ring_color=$xFFFFFF;" in theme
    assert "active_note_ring_width=0.8;" in theme


@pytest.mark.parametrize("value", ["0", "3", "true", "nan", "inf"])
def test_ring_width_is_bounded(tmp_path: Path, value: str) -> None:
    text = (SOURCE / "theme.toml").read_text().replace(
        "active_note_ring_width = 0.8", f"active_note_ring_width = {value}")
    (tmp_path / "theme.toml").write_text(text)
    with pytest.raises(ValueError, match="active_note_ring_width"):
        module.make_theme(tmp_path)


@pytest.mark.parametrize("name", ["active_note_glow_width", "active_note_glow_mix", "active_note_glow_inner_alpha", "active_note_glow_outer_alpha"])
@pytest.mark.parametrize("value", ["-1", "4", "true", "nan", "inf"])
def test_halo_parameters_are_bounded(tmp_path: Path, name: str, value: str) -> None:
    lines = (SOURCE / "theme.toml").read_text().splitlines()
    (tmp_path / "theme.toml").write_text("\n".join(
        f"{name} = {value}" if line.startswith(f"{name} =") else line for line in lines))
    with pytest.raises(ValueError, match=name):
        module.make_theme(tmp_path)


def test_fractional_marker_alpha_is_applied_once_at_blit() -> None:
    ui = (SOURCE / "ui.jsfx-inc").read_text()
    circle = ui[ui.index("function note_circle("):ui.index("function active_note_halo(")]
    assert "alpha=gfx_a; gfx_a=1;" in circle
    assert "gfx_dest=destination; gfx_a=alpha;" in circle


def test_editor_background_matches_generated_theme() -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())
    header = module.make_controls_header(SOURCE)
    assert f"inline constexpr unsigned background = 0xff{theme['background'][1:]};" in header
    editor = (SOURCE.parent / "chordlab_clap/editor.cpp").read_text()
    assert "g.fillAll(juce::Colour(chordlabStyle::background))" in editor


@pytest.mark.parametrize("role", ["key_divider", "staff_line", "guitar_fret", "guitar_string"])
def test_lighter_panel_keeps_diagram_lines_distinct(role: str) -> None:
    dark = tomllib.loads((SOURCE / "theme.toml").read_text())["dark"]
    assert (luminance(dark[role]) + 0.05) / (luminance(dark["diagram_background"]) + 0.05) >= 3


@pytest.mark.parametrize("value", ['"#fff"', '"#GGGGGG"', "123"])
def test_editor_background_rejects_invalid_colors(tmp_path: Path, value: str) -> None:
    text = (SOURCE / "theme.toml").read_text().replace('background = "#585858"', f'background = {value}', 1)
    (tmp_path / "theme.toml").write_text(text)
    with pytest.raises(ValueError, match="Invalid background color"):
        module.make_controls_header(tmp_path)


def test_idle_notes_keep_saturated_color_with_white_labels() -> None:
    theme = tomllib.loads((SOURCE / "theme.toml").read_text())
    assert theme["note_idle_mix"] == 0.8
    assert theme["note_idle_base"] == "#99999F"
    assert theme["active_note_glow_width"] == 3.5
    for role in ("root", "third", "fifth", "seventh", "ninth"):
        active = tuple(int(theme[role][i:i+2], 16) for i in (1,3,5))
        base = tuple(int(theme["note_idle_base"][i:i+2], 16) for i in (1,3,5))
        idle = tuple(round(a*.8+b*.2) for a,b in zip(active,base))
        assert max(idle)-min(idle) >= .75*(max(active)-min(active))


def test_choice_rows_share_pill_geometry_and_font() -> None:
    theme = tomllib.loads((SOURCE / 'theme.toml').read_text())
    choices = theme['choices']
    assert choices['height'] == theme['controls']['size'] == 29
    assert choices['inset'] == 3
    ui = (SOURCE / 'ui.jsfx-inc').read_text()
    assert ui.count('capsule(18,y,gfx_w-36,choices_height)') == 2
    assert 'capsule(18,y,gfx_w-36,choices_height)' in ui
    assert 'capsule(x+pad,y+pad,w-2*pad,choices_height-2*pad)' in ui
    assert 'choices_text_size=choices_font_size*fit' in ui
    assert 'hover(x,y,w,choices_height)' in ui
    renderer = ui[ui.index('function choice_button'):ui.index('function role_color')]
    assert 'choices_text_size' in renderer and 'centered_style' not in renderer
    assert 'choice_button(x,y,w,#text,display_key()==i,locked)' in ui
    assert 'chord_choice_button(x,y,w,#text,selected,game_on,chord_choice_role(d))' in ui


@pytest.mark.parametrize('name,value', [('height', '25'), ('height', 'true'),
                                      ('font_size', '7'), ('inset', '0'), ('inset', 'nan')])
def test_choice_geometry_rejects_invalid_values(tmp_path: Path, name: str, value: str) -> None:
    text = (SOURCE / 'theme.toml').read_text()
    head, choices = text.split('[choices]')
    lines = choices.splitlines()
    choices = '\n'.join(f'{name} = {value}' if line.startswith(f'{name} =') else line for line in lines)
    (tmp_path / 'theme.toml').write_text(head + '[choices]' + choices)
    with pytest.raises(ValueError, match=f'Invalid choices {name}'):
        module.make_theme(tmp_path)


def test_saved_marker_belongs_to_measured_label() -> None:
    ui = (SOURCE / 'ui.jsfx-inc').read_text()
    text = ui[ui.index('function normal_chord_choice_text'):ui.index('function measure_choice_text')]
    assert 'index[0] ? strcat(#text," *")' in text
    row = ui[ui.index('function draw_chord_choices'):ui.index('function ui_begin')]
    assert 'gfx_circle' not in row
    assert 'chord_choice_text(d)' in row


def test_capsule_pixel_centres_use_inclusive_circle_diameter() -> None:
    ui = (SOURCE / 'ui.jsfx-inc').read_text()
    shape = ui[ui.index('function capsule'):ui.index('function choice_button')]
    assert 'r=(min(w,h)-1)/2' in shape
    assert 'x+w-1-r,y+r' in shape
    assert 'w-2*r-1,h' in shape


@pytest.mark.parametrize('inset', [2, 3, 4])
def test_state_circles_share_selection_inset(tmp_path: Path, inset: int) -> None:
    text = (SOURCE / 'theme.toml').read_text().replace('inset = 3', f'inset = {inset}')
    (tmp_path / 'theme.toml').write_text(text)
    assert f'choices_inset={inset};' in module.make_theme(tmp_path)
    assert f'inline constexpr int selection_inset = {inset};' in module.make_controls_header(tmp_path)
    height = tomllib.loads(text)['controls']['size']
    diameter = height - 2 * (inset + 0.5)
    assert diameter / 2 == (height - 2 * inset - 1) / 2
    assert height - diameter >= 5  # Visible gap between adjacent indicators.


@pytest.mark.parametrize('value', ['true', '0', '5', 'nan', '"3"'])
def test_state_circle_inset_validation(tmp_path: Path, value: str) -> None:
    text = (SOURCE / 'theme.toml').read_text().replace('inset = 3', f'inset = {value}')
    (tmp_path / 'theme.toml').write_text(text)
    with pytest.raises(ValueError, match='Invalid choices inset'):
        module.make_controls_header(tmp_path)


def test_editor_padding_preserves_canvas_and_overlay_alignment() -> None:
    theme = tomllib.loads((SOURCE / 'theme.toml').read_text())
    assert theme['editor'] == {'padding_x': 18, 'padding_y': 10}
    header = module.make_controls_header(SOURCE)
    assert 'padding_x = 18;' in header and 'padding_y = 10;' in header
    editor = (SOURCE.parent / 'chordlab_clap/editor.cpp').read_text()
    assert 'setSize(884 + 2 * padding_x, 683 + 2 * padding_y)' in editor
    assert '700 + 2 * padding_x, 560 + 2 * padding_y' in editor
    assert '1600 + 2 * padding_x, 1200 + 2 * padding_y' in editor
    assert 'auto canvas = getLocalBounds().reduced(padding_x, padding_y)' in editor
    assert 'view.setBounds(canvas)' in editor
    assert 'canvas.getRight() - margin - size, canvas.getY() + 10' in editor
    assert 'capture.getX() - gap - size, capture.getY()' in editor
    assert 'canvas.getX() + 18, canvas.getY() + 40, canvas.getWidth() - 36' in editor


@pytest.mark.parametrize('axis', ['x', 'y'])
@pytest.mark.parametrize('value', ['-1', '65', 'true', '1.5', 'nan', '"18"'])
def test_editor_padding_rejects_invalid_values(tmp_path: Path, axis: str, value: str) -> None:
    text = (SOURCE / 'theme.toml').read_text()
    current = 18 if axis == 'x' else 10
    (tmp_path / 'theme.toml').write_text(text.replace(f'padding_{axis} = {current}', f'padding_{axis} = {value}'))
    with pytest.raises(ValueError, match=f'Invalid editor padding_{axis}'):
        module.make_controls_header(tmp_path)


@pytest.mark.parametrize('value', [0, 12, 64])
def test_editor_padding_is_generated_from_config(tmp_path: Path, value: int) -> None:
    text = (SOURCE / 'theme.toml').read_text().replace('padding_x = 18', f'padding_x = {value}')
    (tmp_path / 'theme.toml').write_text(text)
    assert f'padding_x = {value};' in module.make_controls_header(tmp_path)
    assert module.make_theme(tmp_path) == module.make_theme(SOURCE)
