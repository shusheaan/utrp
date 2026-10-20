cmake_minimum_required(VERSION 3.22)
project(BeatLab VERSION 0.3.1 LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(BEATLAB_DEPS "" CACHE PATH "Existing verified JUCE / clap-juce source cache")
if(NOT EXISTS "${BEATLAB_DEPS}/juce/CMakeLists.txt" OR NOT EXISTS "${BEATLAB_DEPS}/clap-juce/CMakeLists.txt")
    message(FATAL_ERROR "Set BEATLAB_DEPS to verified JUCE 8.0.6 + clap-juce sources; see README")
endif()
find_program(CARGO cargo REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS theme.toml configure.py)
execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/configure.py"
    "${CMAKE_CURRENT_BINARY_DIR}/style.h" COMMAND_ERROR_IS_FATAL ANY)
file(GLOB RUST_SOURCES CONFIGURE_DEPENDS "engine/src/*.rs")
add_custom_command(OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/rust/release/libbeatlab_engine.a"
    COMMAND ${CMAKE_COMMAND} -E env "CARGO_TARGET_DIR=${CMAKE_CURRENT_BINARY_DIR}/rust"
        "${CARGO}" build --release --locked --offline --manifest-path "${CMAKE_CURRENT_SOURCE_DIR}/Cargo.toml"
    DEPENDS ${RUST_SOURCES} Cargo.lock engine/Cargo.toml VERBATIM)
add_custom_target(beatlab_rust DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/rust/release/libbeatlab_engine.a")
add_subdirectory("${BEATLAB_DEPS}/juce" juce EXCLUDE_FROM_ALL)
add_subdirectory("${BEATLAB_DEPS}/clap-juce" clap-juce EXCLUDE_FROM_ALL)
juce_add_plugin(BeatLab
    COMPANY_NAME "UTRP" BUNDLE_ID "org.utrp.beatlab"
    PLUGIN_MANUFACTURER_CODE Utrp PLUGIN_CODE BtLb
    PRODUCT_NAME "Beat Lab" DESCRIPTION "Offline beatbox to editable MIDI rhythm"
    FORMATS Standalone IS_SYNTH FALSE IS_MIDI_EFFECT FALSE
    NEEDS_MIDI_INPUT FALSE NEEDS_MIDI_OUTPUT FALSE EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    COPY_PLUGIN_AFTER_BUILD FALSE)
add_dependencies(BeatLab beatlab_rust)
target_sources(BeatLab PRIVATE plugin/processor.cpp plugin/editor.cpp plugin/grid.cpp plugin/recorder.cpp)
target_include_directories(BeatLab PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_compile_definitions(BeatLab PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_VST3_CAN_REPLACE_VST2=0)
target_link_libraries(BeatLab PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/rust/release/libbeatlab_engine.a"
    juce::juce_audio_utils juce::juce_gui_extra juce::juce_recommended_config_flags ${CMAKE_DL_LIBS})
clap_juce_extensions_plugin(TARGET BeatLab CLAP_ID "org.utrp.beatlab"
    CLAP_FEATURES "audio-effect" "utility" CLAP_CHECKING_LEVEL Minimal CLAP_MISBEHAVIOUR_HANDLER_LEVEL Ignore)
enable_testing()
add_executable(gui_test tests/gui.cpp)
target_include_directories(gui_test PRIVATE "${BEATLAB_DEPS}/juce/modules" "${CMAKE_CURRENT_BINARY_DIR}")
target_compile_definitions(gui_test PRIVATE JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1 JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)
target_link_libraries(gui_test PRIVATE BeatLab)
add_executable(clap_test tests/clap.cpp)
target_include_directories(clap_test PRIVATE "${BEATLAB_DEPS}/clap-juce/clap-libs/clap/include")
target_link_libraries(clap_test PRIVATE ${CMAKE_DL_LIBS})
add_test(NAME clap COMMAND clap_test $<TARGET_FILE:BeatLab_CLAP>)
# Manual host-integration diagnostic; never installed or added to unattended CTest.
add_executable(drop_probe EXCLUDE_FROM_ALL tests/drop_probe.cpp)
target_include_directories(drop_probe PRIVATE "${BEATLAB_DEPS}/juce/modules")
target_compile_definitions(drop_probe PRIVATE JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1 JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)
target_link_libraries(drop_probe PRIVATE BeatLab)
add_executable(recorder_test tests/recorder.cpp plugin/recorder.cpp)
add_test(NAME recorder COMMAND recorder_test)
