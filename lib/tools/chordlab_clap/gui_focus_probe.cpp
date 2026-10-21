// Real embedded X11 editor: delayed parent mapping and one-shot focus acquisition.
#include <clap/clap.h>
#include <X11/Xlib.h>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <thread>

namespace {
void check(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
bool inside(Display* display, Window parent)
{
    Window focus{}; int revert{};
    XGetInputFocus(display,&focus,&revert);
    while (focus!=None && focus!=PointerRoot) {
        if (focus==parent) return true;
        Window root{}, ancestor{}, *children{}; unsigned count{};
        if (!XQueryTree(display,focus,&root,&ancestor,&children,&count)) return false;
        if (children) XFree(children);
        focus=ancestor;
    }
    return false;
}
}

void gui_focus_probe(const clap_plugin_t* plugin)
{
    auto* display=XOpenDisplay(nullptr); check(display,"Focus probe requires X11 DISPLAY");
    const auto* gui=static_cast<const clap_plugin_gui_t*>(plugin->get_extension(plugin,CLAP_EXT_GUI));
    const auto* timer=static_cast<const clap_plugin_timer_support_t*>(plugin->get_extension(plugin,CLAP_EXT_TIMER_SUPPORT));
    check(gui && timer,"Focus probe GUI/timer extensions");
    const auto pump=[&] {
        for (int i=0;i<20;++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
            plugin->on_main_thread(plugin); timer->on_timer(plugin,42);
        }
        XSync(display,False);
    };
    XSetWindowAttributes attributes{}; attributes.override_redirect=True;
    const auto window=[&] {
        return XCreateWindow(display,DefaultRootWindow(display),0,0,920,703,0,
            CopyFromParent,InputOutput,CopyFromParent,CWOverrideRedirect,&attributes);
    };
    const auto other=window(); XMapWindow(display,other); XSync(display,False);
    for (int cycle=0;cycle<2;++cycle) {
        const auto parent=window();
        XSetInputFocus(display,other,RevertToParent,CurrentTime); XSync(display,False);
        check(gui->create(plugin,CLAP_WINDOW_API_X11,false),"Create focus editor");
        clap_window_t host{}; host.api=CLAP_WINDOW_API_X11; host.x11=parent;
        check(gui->set_parent(plugin,&host) && gui->show(plugin),"Attach/show before parent map");
        pump(); check(!inside(display,parent),"Unmapped editor must not take focus");
        XMapWindow(display,parent); XSync(display,False); pump();
        check(inside(display,parent),"Mapped editor automatically receives initial focus");
        XSetInputFocus(display,other,RevertToParent,CurrentTime); XSync(display,False); pump();
        check(inside(display,other),"Editor must not reclaim focus after user leaves");
        gui->destroy(plugin); XDestroyWindow(display,parent); XSync(display,False);
    }
    XDestroyWindow(display,other); XCloseDisplay(display);
    std::cout << "X11 delayed map, startup focus, no focus stealing, close/recreate: PASS\n";
}
