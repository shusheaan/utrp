cmake_minimum_required(VERSION 3.22)
project(ChordLab VERSION 0.3.10 LANGUAGES C CXX ASM)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CHORDLAB_DEPS "" CACHE PATH "Verified sources created by prepare_build.py")
if(NOT EXISTS "${CHORDLAB_DEPS}/chordlab.zip")
    message(FATAL_ERROR "Run prepare_build.py and set CHORDLAB_DEPS")
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS keyboard-map.txt prepare_build.py)
execute_process(COMMAND "${Python3_EXECUTABLE}" -c
    "from pathlib import Path; from prepare_build import keyboard_map; keyboard_map(Path('keyboard-map.txt'), Path(r'${CHORDLAB_DEPS}/keyboard_map.h'))"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" COMMAND_ERROR_IS_FATAL ANY)
# Generate both renderers from one theme, then embed the current engine assets.
file(GLOB CHORDLAB_THEME_INPUTS CONFIGURE_DEPENDS "../chordlab/*.jsfx" "../chordlab/*.jsfx-inc" "../chordlab/*.png")
list(FILTER CHORDLAB_THEME_INPUTS EXCLUDE REGEX "/(theme|guitar_table)[.]jsfx-inc$")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${CHORDLAB_THEME_INPUTS}
    ../chordlab/theme.toml ../chordlab/generate_theme.py ../chordlab/guitar.toml ../chordlab/generate_guitar.py prototype.toml)
execute_process(COMMAND "${Python3_EXECUTABLE}" -c
    "import sys; from pathlib import Path; sys.path.insert(0, '../chordlab'); from generate_theme import make_theme, make_controls_header; from generate_guitar import make_guitar; from prepare_build import assets; source=Path('../chordlab'); (source/'guitar_table.jsfx-inc').write_text(make_guitar(source)); (source/'theme.jsfx-inc').write_text(make_theme(source)); Path(r'${CHORDLAB_DEPS}/control_style.h').write_text(make_controls_header(source)); assets(source, Path(r'${CHORDLAB_DEPS}/chordlab.zip'), Path('prototype.toml'))"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" COMMAND_ERROR_IS_FATAL ANY)
# processor.cpp includes its sibling editor.h. Keep it identical on every incremental
# build: a stale copy changes sizeof(YsfxEditor) and corrupts allocation at GUI creation.
configure_file(editor.h "${CHORDLAB_DEPS}/ysfx/plugin/editor.h" COPYONLY)
set(YSFX_PLUGIN OFF CACHE BOOL "" FORCE)
set(YSFX_TESTS OFF CACHE BOOL "" FORCE)
set(YSFX_TOOLS OFF CACHE BOOL "" FORCE)
add_subdirectory("${CHORDLAB_DEPS}/ysfx" ysfx EXCLUDE_FROM_ALL)
add_subdirectory("${CHORDLAB_DEPS}/juce" juce EXCLUDE_FROM_ALL)
add_subdirectory("${CHORDLAB_DEPS}/clap-juce" clap-juce EXCLUDE_FROM_ALL)
juce_add_binary_data(ChordLabAssets SOURCES "${CHORDLAB_DEPS}/chordlab.zip")
juce_add_plugin(ChordLab
    COMPANY_NAME "UTRP" BUNDLE_ID "org.utrp.chordlab"
    PLUGIN_MANUFACTURER_CODE Utrp PLUGIN_CODE ChLb
    PRODUCT_NAME "Chord Lab" DESCRIPTION "Chord Lab JSFX engine with portable keyboard control"
    FORMATS Standalone IS_SYNTH FALSE IS_MIDI_EFFECT TRUE
    NEEDS_MIDI_INPUT TRUE NEEDS_MIDI_OUTPUT TRUE
    EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    COPY_PLUGIN_AFTER_BUILD FALSE)
target_sources(ChordLab PRIVATE embedded_source.cpp control.cpp game_control.cpp game_panel.cpp game_view.cpp game_layout.cpp editor.cpp physical_keys.cpp
    "${CHORDLAB_DEPS}/ysfx/plugin/processor.cpp"
    "${CHORDLAB_DEPS}/ysfx/plugin/parameter.cpp"
    "${CHORDLAB_DEPS}/ysfx/plugin/info.cpp"
    "${CHORDLAB_DEPS}/ysfx/plugin/bank_io.cpp"
    "${CHORDLAB_DEPS}/ysfx/plugin/components/graphics_view.cpp"
    "${CHORDLAB_DEPS}/ysfx/plugin/utility/async_updater.cpp"
    "${CHORDLAB_DEPS}/ysfx/plugin/utility/rt_semaphore.cpp")
target_include_directories(ChordLab PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CHORDLAB_DEPS}" "${CHORDLAB_DEPS}/ysfx/plugin")
target_compile_definitions(ChordLab PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(ChordLab PRIVATE ChordLabAssets ysfx::ysfx
    json juce::juce_audio_utils juce::juce_gui_extra juce::juce_recommended_config_flags)
if(UNIX AND NOT APPLE)
    find_package(X11 REQUIRED)
    target_link_libraries(ChordLab PRIVATE X11::X11)
endif()
clap_juce_extensions_plugin(TARGET ChordLab
    CLAP_ID "org.utrp.chordlab" CLAP_FEATURES "note-effect" "utility"
    CLAP_PROCESS_EVENTS_RESOLUTION_SAMPLES 1
    CLAP_USE_JUCE_PARAMETER_RANGES ALL
    CLAP_CHECKING_LEVEL Minimal CLAP_MISBEHAVIOUR_HANDLER_LEVEL Ignore)
# Compile the existing Rust harmony planner into the plugin, never spawn a service.
find_program(CARGO_EXECUTABLE cargo REQUIRED)
get_filename_component(GAME_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab_game" ABSOLUTE)
file(GLOB_RECURSE GAME_RUST_INPUTS CONFIGURE_DEPENDS "${GAME_SOURCE}/*.rs" "${CMAKE_CURRENT_SOURCE_DIR}/../../../src/*.rs")
list(FILTER GAME_RUST_INPUTS EXCLUDE REGEX "/target/")
set(GAME_LIB "${CMAKE_CURRENT_BINARY_DIR}/game-rust/release/libchordlab_game.a")
add_custom_command(OUTPUT "${GAME_LIB}"
    COMMAND "${CARGO_EXECUTABLE}" build --release --locked --offline --manifest-path "${GAME_SOURCE}/Cargo.toml" --target-dir "${CMAKE_CURRENT_BINARY_DIR}/game-rust"
    DEPENDS ${GAME_RUST_INPUTS} "${GAME_SOURCE}/Cargo.toml" "${GAME_SOURCE}/Cargo.lock" "${GAME_SOURCE}/game.toml"
        "${CMAKE_CURRENT_SOURCE_DIR}/../../../config/simulate.toml" "${CMAKE_CURRENT_SOURCE_DIR}/../../../config/progressions.toml")
add_custom_target(chordlab_game_build DEPENDS "${GAME_LIB}")
add_dependencies(ChordLab chordlab_game_build)
target_link_libraries(ChordLab PRIVATE "${GAME_LIB}" pthread ${CMAKE_DL_LIBS})
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${GAME_SOURCE}/game.toml" "${CMAKE_CURRENT_SOURCE_DIR}/../../../config/simulate.toml")
execute_process(COMMAND "${Python3_EXECUTABLE}" -c
    "import tomllib; from pathlib import Path; c=tomllib.loads(Path(r'${GAME_SOURCE}/game.toml').read_text()); Path(r'${CHORDLAB_DEPS}/game_settings.h').write_text('#pragma once\\nnamespace gameSettings { constexpr int panelWidth = %d; constexpr int answerSeconds = %d; constexpr int demoSeconds = %d; constexpr int modulationPercent = %d; }\\n' % (c['panel_width'], c['answer_seconds'], c['demo_seconds'], round(tomllib.loads(Path(r'${CMAKE_CURRENT_SOURCE_DIR}/../../../config/simulate.toml').read_text())['simulation']['modulation_probability']*100)))"
    COMMAND_ERROR_IS_FATAL ANY)
enable_testing()
add_executable(keyboard_tests keyboard_tests.cpp)
target_include_directories(keyboard_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${CHORDLAB_DEPS}")
add_test(NAME keyboard COMMAND keyboard_tests)
add_executable(clap_probe clap_probe.cpp gui_focus_probe.cpp)
target_include_directories(clap_probe PRIVATE "${CHORDLAB_DEPS}/clap-juce/clap-libs/clap/include")
target_link_libraries(clap_probe PRIVATE ${CMAKE_DL_LIBS} X11::X11)
add_executable(control_tests control_tests.cpp control.cpp)
target_include_directories(control_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${CHORDLAB_DEPS}/ysfx/include")
add_test(NAME control_queue COMMAND control_tests)
add_executable(control_tap_tests control_tap_tests.cpp)
target_include_directories(control_tap_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
add_test(NAME control_tap COMMAND control_tap_tests)
add_executable(harmony_tests harmony_tests.cpp)
target_link_libraries(harmony_tests PRIVATE ysfx::ysfx)
add_test(NAME relative_minor_labels COMMAND harmony_tests "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab/tests/key_labels_probe.jsfx")
add_test(NAME guitar_catalog COMMAND harmony_tests "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab/tests/guitar_probe.jsfx")
add_executable(voicing_tests voicing_tests.cpp)
target_link_libraries(voicing_tests PRIVATE ysfx::ysfx)
add_test(NAME voicing_engine COMMAND voicing_tests "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab/chordlab.jsfx")
add_executable(capsule_tests capsule_tests.cpp)
target_link_libraries(capsule_tests PRIVATE ysfx::ysfx)
add_test(NAME capsule_pixels COMMAND capsule_tests "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab/tests/capsule_probe.jsfx")
add_executable(retrigger_tests retrigger_tests.cpp)
target_link_libraries(retrigger_tests PRIVATE ysfx::ysfx)
add_test(NAME mixed_retrigger COMMAND retrigger_tests "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab/chordlab.jsfx")
add_executable(sustain_tests sustain_tests.cpp)
target_link_libraries(sustain_tests PRIVATE ysfx::ysfx)
add_test(NAME pedal_baseline COMMAND sustain_tests "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab/chordlab.jsfx")
add_executable(game_tests game_tests.cpp game_control.cpp)
add_dependencies(game_tests chordlab_game_build)
target_link_libraries(game_tests PRIVATE ysfx::ysfx "${GAME_LIB}" pthread ${CMAKE_DL_LIBS})
add_test(NAME game_isolation COMMAND game_tests "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab/chordlab.jsfx")
add_executable(game_preview game_preview.cpp)
target_include_directories(game_preview PRIVATE "${CHORDLAB_DEPS}/clap-juce/clap-libs/clap/include")
target_link_libraries(game_preview PRIVATE ${CMAKE_DL_LIBS} X11::X11 pthread)

# Explicit GUI regression executable: run in a disposable X11/Sway session.
add_executable(game_render_tests game_render_tests.cpp)
target_include_directories(game_render_tests PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CHORDLAB_DEPS}" "${CHORDLAB_DEPS}/ysfx/include" "${CHORDLAB_DEPS}/juce/modules")
target_compile_definitions(game_render_tests PRIVATE JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1)
target_link_libraries(game_render_tests PRIVATE ChordLab)

add_test(NAME chord_choice_labels COMMAND harmony_tests "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab/tests/chord_choices_probe.jsfx")
add_executable(choices_tests choices_tests.cpp)
target_link_libraries(choices_tests PRIVATE ysfx::ysfx)
add_test(NAME chord_choice_pixels COMMAND choices_tests "${CMAKE_CURRENT_SOURCE_DIR}/../chordlab/tests/chord_choices_probe.jsfx")
