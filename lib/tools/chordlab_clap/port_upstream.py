"""Small, checked adaptations of the pinned ysfx host, not the JSFX core."""
from pathlib import Path


def replace_once(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise ValueError(f"Pinned source mismatch: {before[:100]}")
    return text.replace(before, after)


def processor_source(text: str) -> str:
    start = text.index('    : AudioProcessor(BusesProperties()')
    end = text.index('    m_impl(new Impl)', start)
    text = text[:start] + '    : AudioProcessor(BusesProperties()),\n' + text[end:]
    text = text.replace('ysfx_max_sliders', '21')
    text = replace_once(text, '    addListener(m_impl.get());', '''    addListener(m_impl.get());
    const uint8_t empty = 0;
    ysfx_state_slider_t mode{13, 1};
    ysfx_state_t initial{&mode, 1, const_cast<uint8_t*>(&empty), 0};
    if (m_embeddedSource.error().isEmpty())
        loadJsfxFile(m_embeddedSource.path(), &initial, false, false);''')
    text = replace_once(text, '    updateTimeInfo();', """    // The CLAP adapter defers parameter-listener callbacks to the main thread.
    // Consume pending host writes before JSFX readback can overwrite their values.
    for (int i = 0; i < 21; ++i)
        if (m_self->getYsfxParameter(i)->hasPendingHostUpdate()) syncParameterToSlider(i);
    updateTimeInfo();""")
    text = replace_once(text, '    processMidiInput(midiMessages);',
                        '    m_self->m_keyboardControl.process(fx);\n    processMidiInput(midiMessages);')
    text = replace_once(text, 'bool YsfxProcessor::isMidiEffect() const\n{\n    return false;',
                        'bool YsfxProcessor::isMidiEffect() const\n{\n    return true;')
    text = text.replace('juce::ValueTree root("ysfx");', 'juce::ValueTree root("chordlab");')
    text = text.replace('juce::CharPointer_UTF8("ysfx")', 'juce::CharPointer_UTF8("chordlab")')
    text = replace_once(text, 'root.setProperty("path", path.getFullPathName(), nullptr);',
                        'root.setProperty("engine", "ysfx-0.0.47", nullptr);')
    text = replace_once(text, 'path = root.getProperty("path").toString();',
                        'path = juce::File(m_embeddedSource.path());')
    text = replace_once(text, '    juce::MemoryInputStream stream(data, (size_t)sizeInBytes, false);',
                        '    if (!data || sizeInBytes <= 0 || sizeInBytes > 1048576) return;\n'
                        '    juce::MemoryInputStream stream(data, (size_t)sizeInBytes, false);')
    text = replace_once(text, '                    item.value = (double)*v;',
                        '                    item.value = (double)*v;\n'
                        '                    if (!std::isfinite(item.value)) return;')
    text = replace_once(text,
        '            juce::Base64::convertFromBase64(base64Result, stateTree.getProperty("data").toString());',
        '            if (!juce::Base64::convertFromBase64(base64Result, stateTree.getProperty("data").toString())) return;')
    for action in ('beginChangeGesture()', 'endChangeGesture()',
                   'sendValueChangedMessageToListeners(param->getValue())'):
        text = text.replace(f'                param->{action};', f'                if (param) param->{action};')
    text = replace_once(text,
        '                if (param) param->sendValueChangedMessageToListeners(param->getValue());',
        '                if (param) {\n'
        '                    const bool keyGesture = i + group_offset == 0 && !(currentTouchMask & (uint64_t{1} << i));\n'
        '                    if (keyGesture) param->beginChangeGesture();\n'
        '                    param->sendValueChangedMessageToListeners(param->getValue());\n'
        '                    if (keyGesture) param->endChangeGesture();\n'
        '                }')
    text = replace_once(text, '    ysfx_delayed_init(fx);',
                        '    m_keyboardControl.release();\n    ysfx_delayed_init(fx);')
    return text


def font_source(text: str) -> str:
    """Backport SWELL positive-height pixel metrics; retain negative em sizing."""
    text = replace_once(text, '  if (lfHeight<0) lfHeight=-lfHeight;\n', '')
    return replace_once(text,
        '      FT_Set_Char_Size(face,lfWidth*64, lfHeight*64,0,0); // 72dpi',
        '      // Match current REAPER/SWELL: positive height includes line metrics.\n'
        '      const int height64 = lfHeight > 0\n'
        '          ? static_cast<int>(lfHeight * static_cast<double>(face->units_per_EM) / face->height * 64.0 + 0.5)\n'
        '          : -lfHeight * 64;\n'
        '      FT_Set_Char_Size(face,lfWidth*64, height64,0,0);')


def port(source: Path, here: Path) -> None:
    font = source / "thirdparty/WDL/source/WDL/swell/swell-gdi-lice.cpp"
    font.write_text(font_source(font.read_text()))
    cmake = source / 'cmake.wdl.txt'
    cmake.write_text(cmake.read_text().replace('${CMAKE_SOURCE_DIR}/', '${CMAKE_CURRENT_SOURCE_DIR}/'))
    plugin = source / 'plugin'
    path = plugin / 'processor.cpp'
    path.write_text(processor_source(path.read_text()))
    path = plugin / 'processor.h'
    text = path.read_text().replace('#include "info.h"',
        '#include "info.h"\n#include "control.h"\n#include "embedded_source.h"')
    text = replace_once(text, '    YsfxProcessor();',
        '    YsfxProcessor();\n'
        '    ChordLabControl& keyboardControl() { return m_keyboardControl; }\n'
        '    const EmbeddedSource& embeddedSource() const { return m_embeddedSource; }')
    text = replace_once(text, '    struct Impl;',
        '    EmbeddedSource m_embeddedSource;\n    ChordLabControl m_keyboardControl;\n    struct Impl;')
    path.write_text(text)
    (plugin / 'editor.h').write_bytes((here / 'editor.h').read_bytes())
    # Chord Lab has no gfx_getchar controls. Only our editor owns key routing;
    # the generic ysfx view must not swallow keys after Keyboard OFF / Escape.
    path = plugin / 'components/graphics_view.cpp'
    text = path.read_text()
    start = text.index('bool YsfxGraphicsView::keyPressed(')
    end = text.index('void YsfxGraphicsView::mouseMove(', start)
    text = text[:start] + "bool YsfxGraphicsView::keyPressed(const juce::KeyPress&) { return false; }\n\n" + \
        "bool YsfxGraphicsView::keyStateChanged(bool) { return false; }\n\n" + text[end:]
    path.write_text(text)
    path = plugin / 'parameter.h'
    text = replace_once(path.read_text(), '    float m_value = 0.0f;',
                        '    std::atomic<float> m_value{0.0f};')
    text = replace_once(text, '    bool wasUpdatedByHost();',
        '    bool wasUpdatedByHost();\n    bool hasPendingHostUpdate() const { return m_hostUpdated.load(); }')
    path.write_text(text)
    path = plugin / 'parameter.cpp'
    text = path.read_text()
    text = replace_once(text, '    if (isEnumSlider())\n        actualValue = juce::roundToInt(actualValue);\n\n    return actualValue;',
        '    const auto range = getSliderRange();\n'
        '    if (range.inc > 0)\n'
        '        actualValue = range.min + std::floor((actualValue - range.min) / range.inc + 0.5) * range.inc;\n\n    return actualValue;')
    text = replace_once(text, '    m_value = newValue;\n    m_hostUpdated = true;',
        '    if (!std::isfinite(newValue)) return;\n'
        '    m_value = juce::jlimit(0.0f, 1.0f, newValue);\n    m_hostUpdated = true;')
    path.write_text(text)
