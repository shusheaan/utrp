#include "ysfx.h"
#include <cstdio>

int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    ysfx_config_t* config = ysfx_config_new();
    ysfx_set_log_reporter(config, [](intptr_t, ysfx_log_level, const char* message) {
        std::fprintf(stderr, "%s\n", message);
    });
    ysfx_t* effect = ysfx_new(config);
    const bool compiled = ysfx_load_file(effect, argv[1], 0) && ysfx_compile(effect, 0);
    if (compiled) ysfx_init(effect);
    const bool passed = compiled && ysfx_read_var(effect, "failures") == 0;
    ysfx_free(effect);
    ysfx_config_free(config);
    return passed ? 0 : 1;
}
