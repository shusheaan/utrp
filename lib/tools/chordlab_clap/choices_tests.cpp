// Real JSFX/LICE pixels and hit regions, not a second UI implementation.
#include "ysfx.h"
#include <array>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>
namespace {
void check(bool value, const char* why) { if (!value) throw std::runtime_error(why); }
void set(ysfx_t* fx, const char* name, double value) {
    auto* variable=ysfx_find_var(fx,name); check(variable,"probe variable exists"); *variable=value;
}
void verify(ysfx_t* fx, int width) {
    constexpr int height=80;
    std::vector<uint8_t> pixels(width*height*4);
    ysfx_gfx_config_t graphics{}; graphics.pixel_width=width; graphics.pixel_height=height;
    graphics.pixels=pixels.data(); graphics.scale_factor=1; ysfx_gfx_setup(fx,&graphics);
    const auto pixel=[&](int x,int y) {
        const auto* p=&pixels[4*(y*width+x)]; return std::array<int,3>{p[2],p[1],p[0]};
    };
    const std::array<unsigned,7> colors{0xB44352,0x267A50,0x267A50,0x986322,0x986322,0x3D68AF,0x3D68AF};
    set(fx,"pixel_enabled",0);set(fx,"game_count",3);
    set(fx,"game_signature",0);set(fx,"game_minor",0);
    set(fx,"mouse_x",-100); set(fx,"mouse_y",-100);
    set(fx,"game_root",0);set(fx,"game_root_letter",0);set(fx,"game_quality",0);
    for (int game:{0,1}) {
        set(fx,"game_on",game); ysfx_gfx_run(fx);
        for (int i=0;i<7;++i) {
            const int d=(i+5)%7, left=18+i*(width-36)/7, right=18+(i+1)*(width-36)/7;
            const int mid=(left+right)/2;
            const auto fill=pixel(mid,25);
            for (int c=0;c<3;++c) {
                const int base=(0x99999F>>(16-8*c))&255;
                const int color=(colors[d]>>(16-8*c))&255;
                const double expected=d==0 ? color : base*.2+color*.8;
                check(std::abs(fill[c]-expected)<=1.1,"seven capsule fills match scale-note palette in both modes");
            }
            if (d==0) check(pixel(mid,22)==std::array<int,3>{255,255,255},"target has visible white selection rim");
        }
    }
    // Every key/mode must render the SAME ordered seven fills, not a rotated
    // minor-scale array. Exercise all selection positions and external quality.
    set(fx,"pixel_enabled",1);
    for(int key=0;key<12;++key) for(int mode:{0,1}) for(int selected=0;selected<7;++selected) {
        set(fx,"pixel_signature",key);set(fx,"pixel_mode",mode);set(fx,"pixel_degree",selected);
        for(int external:{0,1}) {
            set(fx,"pixel_external",external);ysfx_gfx_run(fx);
            for(int i=0;i<7;++i) {
                const int d=(i+5)%7, left=18+i*(width-36)/7, right=18+(i+1)*(width-36)/7;
                const int mid=(left+right)/2;
                const auto fill=pixel(mid,25);const bool lit=!external && d==selected;
                for(int c=0;c<3;++c) {
                    const int base=(0x99999F>>(16-8*c))&255;
                    const int color=(colors[d]>>(16-8*c))&255;
                    check(std::abs(fill[c]-(lit ? color : base*.2+color*.8))<=1.1,
                          "all 24 keys keep blue blue red green green gold gold");
                }
                check((pixel(mid,22)==std::array<int,3>{255,255,255})==lit,
                      "only exact diatonic targets receive a selection rim");
            }
        }
    }
    set(fx,"pixel_enabled",0);
    // Game row remains visible but clicking it cannot change normal voicing.
    set(fx,"ui_write",0);set(fx,"ui_read",0);set(fx,"clicked",1);
    set(fx,"mouse_x",40);set(fx,"mouse_y",34);ysfx_gfx_run(fx);
    check(ysfx_read_var(fx,"ui_write")==0,"game labels are read-only");
    set(fx,"game_on",0);ysfx_gfx_run(fx);
    check(ysfx_read_var(fx,"ui_write")==1,"normal row still accepts its original command");
    set(fx,"clicked",0);
}
}
int main(int argc,char** argv) {
    if (argc!=2) return 2;
    ysfx_config_u config{ysfx_config_new()}; ysfx_u effect{ysfx_new(config.get())};
    try {
        check(ysfx_load_file(effect.get(),argv[1],0)&&ysfx_compile(effect.get(),0),"compile real UI probe");
        ysfx_init(effect.get());check(ysfx_read_var(effect.get(),"failures")==0,"label regression");
        for (int width:{700,884,1600}) verify(effect.get(),width);
        std::cout<<"fixed chord choices: 24 keys x 7 targets, external rejection, three widths, normal/game parity and locked clicks: PASS\n";
    } catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
