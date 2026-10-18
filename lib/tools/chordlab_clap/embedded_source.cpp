#include "embedded_source.h"
#include "BinaryData.h"

EmbeddedSource::EmbeddedSource()
    : directory(juce::File::getSpecialLocation(juce::File::tempDirectory)
        .getChildFile("chordlab-" + juce::Uuid().toString()))
{
    auto result = directory.createDirectory();
    if (result.wasOk()) {
        juce::MemoryInputStream input(BinaryData::chordlab_zip, BinaryData::chordlab_zipSize, false);
        juce::ZipFile bundle(input);
        result = bundle.uncompressTo(directory, false);
    }
    if (result.failed()) failure = result.getErrorMessage();
}

EmbeddedSource::~EmbeddedSource()
{
    if (!directory.deleteRecursively())
        juce::Logger::writeToLog("Chord Lab: cannot remove private assets " + directory.getFullPathName());
}
