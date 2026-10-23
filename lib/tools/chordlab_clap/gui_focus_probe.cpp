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
    const auto pump=[&](int ticks = 20) {
        for (int i=0;i<ticks;++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
            plugin->on_main_thread(plugin); timer->on_timer(plugin,42);
        }
        XSync(display,False);
    };
    XSetWindowAttributes attributes{}; attributes.override_redirect=False;
    const auto window=[&] {
        return XCreateWindow(display,DefaultRootWindow(display),0,0,920,703,0,
            CopyFromParent,InputOutput,CopyFromParent,CWOverrideRedirect,&attributes);
    };
    const auto other=window(); XMapWindow(display,other); XSync(display,False); pump();
    for (int cycle=0;cycle<6;++cycle) {
        const auto parent=window();
        XStoreName(display, parent, "Chord Lab focus regression host");
        if (cycle % 2 == 1) { XMapWindow(display,parent); XSync(display,False); pump(); }
        XSetInputFocus(display,other,RevertToParent,CurrentTime); XSync(display,False);
        check(gui->create(plugin,CLAP_WINDOW_API_X11,false),"Create focus editor");
        clap_window_t host{}; host.api=CLAP_WINDOW_API_X11; host.x11=parent;
        check(gui->set_parent(plugin,&host) && gui->show(plugin),"Attach/show before parent map");
        if (cycle % 2 == 0) {
            pump(); check(!inside(display,parent),"Unmapped editor must not take focus");
            XMapWindow(display,parent); XSync(display,False);
        } else {
            pump(5);
            // The host finishes opening by focusing its container, not the peer.
            XSetInputFocus(display,parent,RevertToParent,CurrentTime); XSync(display,False);
        }
        pump();
        check(inside(display,parent),"Mapped editor automatically receives initial focus");
        Window focused{}; int revert{}; XGetInputFocus(display,&focused,&revert);
        check(focused != parent,"Keyboard peer, not just host wrapper, owns startup focus");
        // Bitwig's wrapper also owns an offscreen 1x1 InputOnly focus proxy.
        // This is a sibling of the embedded peer, not one of its ancestors.
        const auto proxy=XCreateWindow(display,parent,-1,-1,1,1,0,0,InputOnly,CopyFromParent,0,nullptr);
        XMapWindow(display,proxy); XSync(display,False);
        for(int handoff=0;handoff<3;++handoff) {
            XSetInputFocus(display,proxy,RevertToParent,CurrentTime);XSync(display,False);pump();
            Window actual{};XGetInputFocus(display,&actual,&revert);
            check(actual==focused,"Late Bitwig InputOnly sibling focus hands back to keyboard peer");
        }
        // A real sibling control is not a focus proxy: do not steal its input.
        const auto control=XCreateSimpleWindow(display,parent,0,0,100,30,0,0,0);
        XMapWindow(display,control);XSetInputFocus(display,control,RevertToParent,CurrentTime);
        XSync(display,False);pump();
        check(inside(display,control),"Visible sibling control keeps its own focus");
        XSetInputFocus(display,other,RevertToParent,CurrentTime); XSync(display,False); pump();
        check(inside(display,other),"Editor must not reclaim focus after user leaves");
        const auto otherProxy=XCreateWindow(display,other,-1,-1,1,1,0,0,InputOnly,CopyFromParent,0,nullptr);
        XMapWindow(display,otherProxy);XSetInputFocus(display,otherProxy,RevertToParent,CurrentTime);
        XSync(display,False);pump();
        check(inside(display,otherProxy),"Another editor's hidden proxy keeps its own focus");
        XDestroyWindow(display,otherProxy);
        gui->destroy(plugin); XDestroyWindow(display,parent); XSync(display,False);
    }
    XDestroyWindow(display,other); XCloseDisplay(display);
    std::cout << "X11 delayed map, late host/proxy focus, keyboard peer activation, sibling control isolation, no focus stealing, recreate: PASS\n";
}
