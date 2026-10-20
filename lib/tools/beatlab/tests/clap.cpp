#include <clap/clap.h>
#include <dlfcn.h>
#include <cstring>
#include <iostream>
#include <stdexcept>

void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
const void* extension(const clap_host_t*, const char*) { return nullptr; }
void request(const clap_host_t*) {}
uint32_t eventCount(const clap_input_events_t*) { return 0; }
const clap_event_header_t* eventAt(const clap_input_events_t*, uint32_t) { return nullptr; }
bool output(const clap_output_events_t*, const clap_event_header_t*) { return true; }
int main(int argc, char** argv) {
    require(argc == 2, "Pass CLAP binary path");
    void* library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) throw std::runtime_error(dlerror());
    auto* entry = static_cast<const clap_plugin_entry_t*>(dlsym(library, "clap_entry"));
    require(entry && entry->init(argv[1]), "CLAP entry init");
    auto* factory = static_cast<const clap_plugin_factory_t*>(entry->get_factory(CLAP_PLUGIN_FACTORY_ID));
    require(factory && factory->get_plugin_count(factory) == 1, "Single independent plugin");
    auto* descriptor = factory->get_plugin_descriptor(factory, 0);
    require(std::strcmp(descriptor->id, "org.utrp.beatlab") == 0, "Stable unique CLAP id");
    clap_host_t host{CLAP_VERSION, nullptr, "Beat Lab smoke", "UTRP", "", "0.1",
                     extension, request, request, request};
    auto* plugin = factory->create_plugin(factory, &host, descriptor->id);
    require(plugin && plugin->init(plugin), "CLAP instance init");
    auto* ports = static_cast<const clap_plugin_audio_ports_t*>(plugin->get_extension(plugin, CLAP_EXT_AUDIO_PORTS));
    require(ports && ports->count(plugin, true) == 1 && ports->count(plugin, false) == 1, "Audio ports");
    clap_audio_port_info_t port{};
    require(ports->get(plugin, 0, true, &port) && port.channel_count == 2, "Stereo input");
    require(plugin->activate(plugin, 48000, 1, 256), "Activate");
    require(plugin->start_processing(plugin), "Start processing");
    float left[256], right[256], outLeft[256], outRight[256];
    for (int i=0;i<256;++i) { left[i]=right[i]=0.5f; outLeft[i]=outRight[i]=1.0f; }
    float* in[]{left,right}; float* out[]{outLeft,outRight};
    clap_audio_buffer_t input{}, result{};
    input.data32=in; input.channel_count=2; result.data32=out; result.channel_count=2;
    clap_input_events_t events{nullptr,eventCount,eventAt};
    clap_output_events_t emitted{nullptr,output};
    clap_process_t process{};
    process.frames_count=256; process.audio_inputs=&input; process.audio_outputs=&result;
    process.audio_inputs_count=process.audio_outputs_count=1;
    process.in_events=&events; process.out_events=&emitted;
    require(plugin->process(plugin,&process) != CLAP_PROCESS_ERROR, "Process");
    for (int i=0;i<256;++i) require(outLeft[i]==0 && outRight[i]==0, "Microphone monitoring muted");
    plugin->stop_processing(plugin); plugin->deactivate(plugin); plugin->destroy(plugin);
    entry->deinit(); dlclose(library);
    std::cout << "CLAP discovery, init, audio ports, activate, processing, mute, shutdown PASS\n";
}
