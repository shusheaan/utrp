// Diagnostic only: records file payloads offered by the DAW; no audio or project edits.
#include <juce_gui_extra/juce_gui_extra.h>
#include <iostream>
class DropProbe final : public juce::Component, public juce::FileDragAndDropTarget {
public:
    explicit DropProbe(juce::String source) : sourceFile(std::move(source)) {}
    void mouseDrag(const juce::MouseEvent& event) override {
        if (event.getDistanceFromDragStart()>8 && !dragging && sourceFile.isNotEmpty()) {
            dragging=true;
            juce::DragAndDropContainer::performExternalDragDropOfFiles(
                {sourceFile},false,this,[this] { dragging=false; });
        }
    }
    bool isInterestedInFileDrag(const juce::StringArray& files) override {
        const auto offered=files.joinIntoString(" | ");
        if (offered!=last) { last=offered; std::cout << "OFFER " << offered << std::endl; }
        return true;
    }
    void filesDropped(const juce::StringArray& files,int,int) override {
        last="DROP: "+files.joinIntoString(" | ");
        std::cout << last << std::endl; repaint();
    }
    void paint(juce::Graphics& g) override {
        g.fillAll(juce::Colour(0xff454545)); g.setColour(juce::Colours::white); g.setFont(18.0f);
        g.drawFittedText(last.isEmpty() ? "Drop a Bitwig clip here\nDiagnostic only / no audio" : last,
            getLocalBounds().reduced(24),juce::Justification::centred,8);
    }
private:
    juce::String sourceFile;
    bool dragging=false;
    juce::String last;
};
class ProbeWindow final : public juce::DocumentWindow {
public:
    explicit ProbeWindow(juce::String source) : DocumentWindow("Beat Lab Drop Probe",juce::Colour(0xff454545),allButtons) {
        setUsingNativeTitleBar(true); setContentOwned(new DropProbe(std::move(source)),false);
        centreWithSize(640,300); setVisible(true);
    }
    void closeButtonPressed() override { juce::MessageManager::getInstance()->stopDispatchLoop(); }
};
int main(int argc,char** argv) {
    if (argc>2 || (argc==2 && !juce::File(argv[1]).existsAsFile())) {
        std::cerr << "Usage: drop_probe [existing-audio-file]\n";
        return 1;
    }
    juce::ScopedJuceInitialiser_GUI init;
    ProbeWindow window(argc==2 ? juce::String(argv[1]) : juce::String{});
    juce::MessageManager::getInstance()->runDispatchLoop();
}
