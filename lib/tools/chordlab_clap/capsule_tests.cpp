#include "ysfx.h"
#include <array>
#include <cstdio>

// Exercise the actual JSFX/LICE renderer, not a geometry reimplementation.
int main(int argc, char** argv)
{
    if (argc != 2) return 2;
    auto* config = ysfx_config_new();
    ysfx_set_log_reporter(config, [](intptr_t, ysfx_log_level, const char* text) {
        std::fprintf(stderr, "%s\n", text);
    });
    auto* effect = ysfx_new(config);
    bool passed = ysfx_load_file(effect, argv[1], 0) && ysfx_compile(effect, 0);
    if (passed) {
        ysfx_init(effect);
        constexpr int width=220, height=80;
        std::array<uint8_t,width*height*4> pixels{};
        ysfx_gfx_config_t graphics{};
        graphics.pixel_width=width; graphics.pixel_height=height;
        graphics.pixels=pixels.data(); graphics.scale_factor=1;
        ysfx_gfx_setup(effect,&graphics);
        const auto pixel=[&](int x,int y){return pixels[4*(y*width+x)];};
        for (int h:{23,29}) for (int w:{h,40,61,160}) {
            *ysfx_find_var(effect,"shape_width")=w;
            *ysfx_find_var(effect,"shape_height")=h;
            ysfx_gfx_run(effect);
            for (int y=0;y<height;++y) for (int x=0;x<width;++x) {
                if (x<20 || x>=20+w || y<20 || y>=20+h) {
                    if (pixel(x,y)!=0) passed=false;
                } else {
                    if (pixel(x,y)!=pixel(x,40+h-1-y)) passed=false;
                    if (pixel(x,y)!=pixel(40+w-1-x,y)) passed=false;
                }
            }
            const int mid=20+w/2;
            if (pixel(mid,20)!=255 || pixel(mid,20+h-1)!=255) passed=false;
            std::printf("capsule %dx%d: %s\n",w,h,passed?"PASS":"FAIL");
        }
    }
    ysfx_free(effect); ysfx_config_free(config);
    return passed?0:1;
}
