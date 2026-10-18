#pragma once
#include <juce_core/juce_core.h>

// Per-instance private scratch files. Saved state never references this path.
class EmbeddedSource final {
public:
    EmbeddedSource();
    ~EmbeddedSource();
    juce::String path() const { return directory.getChildFile("chordlab.jsfx").getFullPathName(); }
    const juce::String& error() const { return failure; }
private:
    const juce::File directory;
    juce::String failure;
    JUCE_DECLARE_NON_COPYABLE(EmbeddedSource)
};
