from dataclasses import replace
import json
from pathlib import Path
import random

import pytest

from layout import (Config, Rect, Window, arrange, available, find_space, mapping,
                    overlaps, plugin_windows, signature)


def config() -> Config:
    return Config.read(Path(__file__).with_name('layout.toml'))


def window(number: int, width: int, height: int, title: str = 'Track / FX') -> Window:
    return Window(number, title, Rect(100, 100, width, height), 2,
                  Rect(0, 0, 3440, 1440), True, False)


def test_centered_pair_and_right_hand_effect() -> None:
    windows = (window(1, 920, 703, 'Shared / Chord Lab'), window(2, 600, 490),
               window(3, 920, 345))
    result = dict(arrange(windows, config()))
    assert result[1] == Rect(952, 368, 920, 703)
    assert result[2] == Rect(1888, 474, 600, 490)
    assert result[3] == Rect(2504, 547, 920, 345)


def test_centered_core_stays_put_when_an_extra_fits() -> None:
    chord = window(3, 920, 703, 'Shared / Chord Lab')
    synth = window(1, 1188, 742, 'Track / Surge XT')
    pair = dict(arrange((synth, chord), config()))
    more = dict(arrange((synth, window(2, 600, 490), chord), config()))
    assert pair[3] == more[3] == Rect(658, 368, 920, 703)
    assert pair[1] == more[1] == Rect(1594, 349, 1188, 742)
    assert more[2] is not None


def test_overflow_does_not_resize() -> None:
    assert arrange((window(1, 4000, 2000),), config()) == ((1, None),)


def test_offsets_and_workspace_isolation() -> None:
    a = replace(window(1, 920, 703), bounds=Rect(-3440, 40, 3440, 1440))
    b = replace(a, id=2, workspace=3)
    result = dict(arrange((a, b), config()))
    assert result[1] == result[2] == Rect(-2180, 408, 920, 703)


def test_manual_move_and_focus_do_not_repack() -> None:
    a = window(1, 920, 703)
    assert signature((a,)) == signature((replace(a, rect=replace(a.rect, x=300)),))
    assert signature((a,)) != signature((replace(a, rect=replace(a.rect, width=950)),))


def test_small_display() -> None:
    assert find_space(Rect(400, 80, 0, 0), 900, 500, (), 16) is None


def test_random_layout_invariants() -> None:
    rng = random.Random(918)
    for _ in range(300):
        windows = tuple(window(i, rng.randrange(200, 1400), rng.randrange(200, 900))
                        for i in range(rng.randrange(1, 12)))
        area = available(windows[0].bounds, config())
        placed: list[Rect] = []
        originals = {w.id: w.rect for w in windows}
        for ident, rect in arrange(windows, config()):
            if rect is None:
                continue
            assert rect.width == originals[ident].width
            assert rect.height == originals[ident].height
            assert area.x <= rect.x <= area.x + area.width - rect.width
            assert area.y <= rect.y <= area.y + area.height - rect.height
            assert not any(overlaps(rect, r, config().gap) for r in placed)
            placed.append(rect)


def tree() -> dict[str, object]:
    return {'type': 'root', 'nodes': [{'id': 2, 'type': 'workspace', 'name': '2',
        'rect': {'x': 0, 'y': 0, 'width': 3440, 'height': 1440}, 'nodes': [
            {'id': 10, 'window': 100, 'pid': 1, 'name': 'Bitwig Studio - Library',
             'window_properties': {'class': 'com.bitwig.BitwigStudio'}},
            {'id': 11, 'pid': 20, 'name': 'Track / FX', 'floating': 'auto_off',
             'fullscreen_mode': 0, 'window_properties': {'transient_for': 100},
             'rect': {'x': 0, 'y': 0, 'width': 600, 'height': 490}},
        ]}]}


def test_requires_host_process_and_main_transient_parent() -> None:
    data = mapping(json.loads(json.dumps(tree())))
    assert [w.id for w in plugin_windows(data, frozenset({20}))] == [11]
    assert plugin_windows(data, frozenset({1})) == ()
    assert plugin_windows(data, frozenset()) == ()
    text = json.dumps(tree()).replace('"transient_for": 100', '"transient_for": 999')
    assert plugin_windows(mapping(json.loads(text)), frozenset({20})) == ()


def test_excludes_dialogs_and_scratchpad() -> None:
    text = json.dumps(tree()).replace('Track / FX', 'Choose a preset')
    assert plugin_windows(mapping(json.loads(text)), frozenset({20})) == ()
    text = json.dumps(tree()).replace('"name": "2"', '"name": "__i3_scratch"')
    assert plugin_windows(mapping(json.loads(text)), frozenset({20})) == ()


@pytest.mark.parametrize('value', [None, {}, {'x': 0, 'y': 0, 'width': -1, 'height': 2},
                                  {'x': '0', 'y': 0, 'width': 1, 'height': 2}])
def test_invalid_rect(value: object) -> None:
    with pytest.raises(ValueError):
        Rect.parse(json.loads(json.dumps(value)))


def instrument_orders() -> tuple[tuple[str, ...], ...]:
    from itertools import permutations
    combinations = ('CP', 'CS', 'CFH', 'CFFH', 'CPS', 'CPSH', 'CSFH',
                    'CPFH', 'CSFFH', 'CPFFH', 'CPSFH')
    return tuple(order for combination in combinations for order in sorted(set(permutations(combination))))


@pytest.mark.parametrize('order', instrument_orders(), ids=lambda order: ''.join(order))
@pytest.mark.parametrize('chord_width', [920, 1252], ids=['normal', 'game'])
def test_real_instrument_combinations_fit_in_every_opening_order(order: tuple[str, ...],
                                                                chord_width: int) -> None:
    dimensions = {'C': (chord_width, 703), 'S': (1141, 711), 'P': (775, 515),
                  'F': (600, 490), 'H': (920, 345)}
    windows = tuple(window(index, *dimensions[kind],
                           title='Track / ' + {'C': 'Chord Lab', 'S': 'Surge XT', 'P': 'sfizz', 'F': 'Surge XT Effects', 'H': 'Dragonfly Hall Reverb'}[kind])
                    for index, kind in enumerate(order))
    results = dict(arrange(windows, config()))
    occupied: list[Rect] = []
    area = available(windows[0].bounds, config())
    for win in windows:
        rect = results[win.id]
        assert rect is not None, f'False overflow for opening order {order}'
        assert (rect.width, rect.height) == (win.rect.width, win.rect.height)
        assert area.x <= rect.x <= area.x + area.width - rect.width
        assert area.y <= rect.y <= area.y + area.height - rect.height
        assert not any(overlaps(rect, previous, config().gap) for previous in occupied)
        occupied.append(rect)


def test_fx_remembered_tiling_size_is_reset_but_synth_zoom_is_not() -> None:
    from layout import needs_effect_size_reset
    fx = window(1, 1763, 1440, 'Track / Surge XT Effects')
    assert needs_effect_size_reset(fx, True, config())
    assert needs_effect_size_reset(fx, False, config())
    assert not needs_effect_size_reset(replace(fx, title='Track / Surge XT'), True, config())
    normal = replace(fx, rect=Rect(0, 0, 600, 490))
    assert not needs_effect_size_reset(normal, True, config())
    manual = replace(fx, rect=Rect(0, 0, 700, 550))
    assert not needs_effect_size_reset(manual, False, config())
    assert needs_effect_size_reset(manual, True, config())


def test_chord_alone_is_screen_centered_and_pair_recenters_on_close() -> None:
    chord = window(1, 920, 703, 'Shared / Chord Lab')
    assert dict(arrange((chord,), config()))[1] == Rect(1260, 368, 920, 703)
    pair = dict(arrange((chord, window(2, 775, 515, 'Track / sfizz')), config()))
    assert pair[1] == Rect(864, 368, 920, 703)
    assert pair[2] == Rect(1800, 462, 775, 515)


def test_instrument_takes_core_priority_over_old_effect() -> None:
    chord = window(1, 920, 703, 'Shared / Chord Lab')
    effect = window(2, 600, 490)
    synth = window(3, 1141, 711, 'Track / Surge XT')
    pair = dict(arrange((chord, synth), config()))
    mixed = dict(arrange((chord, effect, synth), config()))
    assert mixed[1] == pair[1]
    assert mixed[3] == pair[3]
    assert mixed[2] is not None


@pytest.mark.parametrize('primary', [(775, 515, 'sfizz'), (1141, 711, 'Surge XT'),
                                     (600, 490, 'Surge XT Effects')])
@pytest.mark.parametrize('origin', [(0, 0), (-3440, 40), (3440, -200)])
def test_game_panel_cycle_has_one_centered_group(primary: tuple[int, int, str],
                                                origin: tuple[int, int]) -> None:
    """Resize uses the existing center policy, never a competing left-edge anchor."""
    chord = replace(window(1, 920, 703, 'Shared / Chord Lab'),
                    bounds=Rect(*origin, 3440, 1440))
    synth = replace(window(2, primary[0], primary[1], 'Track / ' + primary[2]),
                    bounds=chord.bounds)
    closed = (chord, synth)
    expected = dict(arrange(closed, config()))
    current = closed
    for _ in range(30):
        opened = tuple(replace(w, rect=replace(w.rect, width=1252)) if w.id == 1 else w
                       for w in current)
        assert signature(opened) != signature(current)
        positions = dict(arrange(opened, config()))
        left, right = positions[1], positions[2]
        assert left is not None and right is not None
        assert right.x == left.x + left.width + config().gap
        assert not overlaps(left, right, config().gap)
        assert left.width == 1252 and left.height == 703
        group_width = left.width + config().gap + right.width
        assert left.x == origin[0] + (3440 - group_width) // 2
        # Emulate host recentering/random drag during the resize. Positions must
        # not become policy input; the final signature contains dimensions only.
        current = tuple(replace(w, rect=replace(w.rect, x=999, y=123)) for w in closed)
        assert dict(arrange(current, config())) == expected


def test_panel_resize_not_misidentified_as_new_window_or_fx_reset() -> None:
    from layout import needs_effect_size_reset
    closed = window(1, 920, 703, 'Shared / Chord Lab')
    opened = replace(closed, rect=replace(closed.rect, width=1252))
    assert not needs_effect_size_reset(opened, False, config())
    assert not needs_effect_size_reset(opened, True, config())
    assert signature((closed,)) != signature((opened,))


def test_complete_game_cycle_between_polls_still_requests_centering() -> None:
    """Same final dimensions cannot hide a host's resize-induced recentering."""
    before = replace(window(1, 1252, 703, 'Shared / Chord Lab'),
                     layout_revision=('utrp-chordlab-layout-100',))
    after = replace(before, rect=replace(before.rect, x=1092),
                    layout_revision=('utrp-chordlab-layout-102',))
    assert signature((before,)) != signature((after,))
    assert dict(arrange((before,), config())) == dict(arrange((after,), config()))
    # A genuine user drag without a G transition must not cause a layout fight.
    dragged = replace(after, rect=replace(after.rect, x=333, y=222))
    assert signature((after,)) == signature((dragged,))


def test_resize_notification_preserves_user_marks_and_filters_invalid_names() -> None:
    from layout import layout_revision
    node = mapping(json.loads('{"marks": ["user-bookmark", "utrp-chordlab-layout-123", '
                              '"utrp-chordlab-layout-", "utrp-chordlab-layout-bad", '
                              '"utrp-chordlab-layout-１２３", 123]}'))
    assert layout_revision(node) == ('utrp-chordlab-layout-123',)
    assert layout_revision({}) == ()
    with pytest.raises(ValueError, match='marks'):
        layout_revision({'marks': 'invalid'})


def test_library_focus_is_one_shot_and_scoped() -> None:
    from layout import library_focus_target
    parent = {'id': 1, 'window': 101, 'name': 'Bitwig Studio - Library', 'focused': True,
              'window_properties': {'class': 'com.bitwig.BitwigStudio'}}
    plugin = {'id': 2, 'window': 102, 'focused': False,
              'name': 'CHORD LAB - shared MIDI input / Chord Lab',
              'window_properties': {'transient_for': 101}}
    tree = {'nodes': [parent, plugin]}
    assert library_focus_target(tree, frozenset({2})) == 2
    assert library_focus_target(tree, frozenset()) is None
    parent['name'] = 'Bitwig Studio - Recording'
    assert library_focus_target(tree, frozenset({2})) is None
    parent['name'] = 'Bitwig Studio - Library'
    parent['focused'] = False
    tree['nodes'].append({'id': 3, 'window': 103, 'focused': True, 'name': 'Terminal'})
    assert library_focus_target(tree, frozenset({2})) is None
    tree['nodes'].pop(); parent['focused'] = True
    plugin['name'] = 'GUITAR - raw detection / Chord Lab'
    assert library_focus_target(tree, frozenset({2})) is None
    plugin['name'] = 'CHORD LAB - shared MIDI input / Chord Lab'
    plugin['window_properties']['transient_for'] = 999
    assert library_focus_target(tree, frozenset({2})) is None
