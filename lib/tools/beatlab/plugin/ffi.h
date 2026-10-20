#pragma once
#include <cstddef>
#include <cstdint>
extern "C" {
char* beatlab_analyze(const float*, std::size_t, std::uint32_t, const char*);
char* beatlab_midi(const char*);
void beatlab_free(char*);
}
