#include "game_layout.h"
#include <array>
#include <cstring>
#if JUCE_LINUX
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#endif

juce::var GameLayout::request(uint32_t type,const juce::String& command)
{
#if JUCE_LINUX
    const auto path=juce::SystemStats::getEnvironmentVariable("SWAYSOCK",{});
    if(path.isEmpty()) {error="Sway layout unavailable: no SWAYSOCK";return {};}
    sockaddr_un addr{};addr.sun_family=AF_UNIX;
    if(size_t(path.getNumBytesAsUTF8())>=sizeof addr.sun_path) {error="Sway socket path too long";return {};}
    std::strcpy(addr.sun_path,path.toRawUTF8());
    const int fd=socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);
    if(fd<0) {error="Cannot open Sway IPC";return {};}
    struct Close {int fd;~Close(){close(fd);}} closeSocket{fd};
    timeval timeout{0,200000};
    if(setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof timeout)<0
        || setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof timeout)<0
        || connect(fd,reinterpret_cast<sockaddr*>(&addr),sizeof addr)<0) {error="Cannot connect to test/window Sway";return {};}
    std::array<char,14> header{};std::memcpy(header.data(),"i3-ipc",6);
    const uint32_t len=uint32_t(command.getNumBytesAsUTF8());
    std::memcpy(header.data()+6,&len,4);std::memcpy(header.data()+10,&type,4);
    const auto sendAll=[fd](const char* p,size_t n){while(n){auto k=send(fd,p,n,MSG_NOSIGNAL);if(k<=0)return false;p+=k;n-=size_t(k);}return true;};
    const auto readAll=[fd](char* p,size_t n){while(n){auto k=recv(fd,p,n,0);if(k<=0)return false;p+=k;n-=size_t(k);}return true;};
    if(!sendAll(header.data(),header.size())||!sendAll(command.toRawUTF8(),len)||!readAll(header.data(),header.size())) {error="Sway IPC timed out";return {};}
    uint32_t size{},responseType{};std::memcpy(&size,header.data()+6,4);std::memcpy(&responseType,header.data()+10,4);
    if(std::memcmp(header.data(),"i3-ipc",6)||size>1048576||responseType!=type) {error="Invalid Sway IPC response";return {};}
    juce::MemoryBlock data(size+1,true);
    if(!readAll(static_cast<char*>(data.getData()),size)){error="Incomplete Sway response";return {};}
    juce::var result;
    if(juce::JSON::parse(juce::String::fromUTF8(static_cast<const char*>(data.getData()),int(size)),result).failed()) {error="Invalid Sway JSON";return {};}
    return result;
#else
    juce::ignoreUnused(type,command);error="Floating arrangement requires Sway";return {};
#endif
}
bool GameLayout::scan()
{
    windows.clear(); const auto tree=request(4,{});if(tree.isVoid()) return false;
    const auto rectangle=[](const juce::var& node){auto r=node["rect"];return juce::Rectangle<int>(int(r["x"]),int(r["y"]),int(r["width"]),int(r["height"]));};
    // Find the focused workspace first; do not touch other workspaces or outputs.
    juce::var workspace;
    std::vector<juce::int64> bitwigParents;
    std::function<void(const juce::var&)> findParents=[&](const juce::var& n){
        if(n["window_properties"]["class"].toString()=="com.bitwig.BitwigStudio")
            bitwigParents.push_back(juce::int64(n["window"]));
        for(auto key:{"nodes","floating_nodes"})if(auto* a=n[key].getArray())
            for(const auto& child:*a)findParents(child);
    };
    findParents(tree);
    std::function<bool(const juce::var&)> focused=[&](const juce::var& n){
        if(bool(n["focused"]))return true;
        for(auto key:{"nodes","floating_nodes"})if(auto* a=n[key].getArray())for(const auto& c:*a)if(focused(c))return true;
        return false;
    };
    std::function<void(const juce::var&)> locate=[&](const juce::var& n){
        if(n["type"].toString()=="workspace"&&focused(n))workspace=n;
        if(auto* a=n["nodes"].getArray())for(const auto& c:*a)locate(c);
    };
    locate(tree);if(workspace.isVoid()){error="No focused Sway workspace";return false;}
    bounds=rectangle(workspace);
    std::function<void(const juce::var&)> gather=[&](const juce::var& n){
        if(!n["window"].isVoid()&&!n["window"].isUndefined()&&int(n["fullscreen_mode"])==0) {
            auto props=n["window_properties"];
            const auto parent=juce::int64(props["transient_for"]);
            // The existing Bitwig layout service is the SOLE position owner.
            // A CLAP must not compete with it or try to undo its centering.
            const bool bitwigOwned=parent>0 && n["name"].toString().endsWith(" / Chord Lab")
                && std::find(bitwigParents.begin(),bitwigParents.end(),parent)!=bitwigParents.end();
            windows.push_back({juce::int64(n["id"]),juce::int64(n["pid"]),n["name"].toString(),props["class"].toString(),rectangle(n),bool(n["focused"]),bitwigOwned});
        }
        for(auto key:{"nodes","floating_nodes"})if(auto* a=n[key].getArray())for(const auto& c:*a)gather(c);
    };
    if(auto* a=workspace["floating_nodes"].getArray())for(const auto& c:*a)gather(c);
    return true;
}
bool GameLayout::move(int64_t id,juce::Point<int> point)
{
    const auto response=request(0,"[con_id="+juce::String(id)+"] move position "+juce::String(point.x)+" "+juce::String(point.y));
    if(auto* a=response.getArray();a&&!a->isEmpty()&&bool(a->getFirst()["success"]))return true;
    error="Sway rejected window placement";return false;
}
void GameLayout::remember()
{
    error.clear();moved.clear();armed=false;restoreOwn=false;noSpace=false;
    original={};
    if(!scan())return;
    for(const auto& w:windows)if(w.focused&&w.title.containsIgnoreCase("Chord Lab")) {
        original=w;
        if(w.bitwigOwned)return; // Size changes trigger the existing centered-group policy.
        armed=true;break;
    }
    if(!armed)error="Game layout: focused floating Chord Lab not found";
}
void GameLayout::notifyOwner()
{
    // A complete close/open can happen between layout.py polls. A bounded,
    // persistent Sway mark forces re-layout even when final dimensions match.
    // This requests placement; it never takes position ownership from Bitwig's policy.
    const auto tree=request(4,{});
    const juce::String prefix="utrp-chordlab-layout-";
    const auto selector="[con_id="+juce::String(original.id)+"] ";
    juce::String command=selector+"mark --add "+prefix+juce::String(juce::Time::getHighResolutionTicks());
    bool found=false;
    std::function<void(const juce::var&)> visit=[&](const juce::var& node){
        if(juce::int64(node["id"])==original.id) {
            found=true;
            if(auto* marks=node["marks"].getArray())for(const auto& mark:*marks) {
                const auto value=mark.toString(), suffix=value.substring(prefix.length());
                if(value.startsWith(prefix)&&suffix.isNotEmpty()&&suffix.containsOnly("0123456789"))
                    command+="; "+selector+"unmark "+value;
            }
        }
        for(auto key:{"nodes","floating_nodes"})if(auto* children=node[key].getArray())
            for(const auto& child:*children)visit(child);
    };
    visit(tree);
    if(!found){error="Bitwig editor disappeared before layout notification";return;}
    const auto reply=request(0,command);
    if(auto* entries=reply.getArray();entries&&!entries->isEmpty()) {
        for(const auto& entry:*entries)if(!bool(entry["success"])) {error="Sway rejected layout notification";return;}
    } else error="Missing Sway layout notification response";
}
void GameLayout::arrange()
{
    if(original.bitwigOwned){notifyOwner();return;}
    if(!armed||!scan())return;
    const auto own=std::find_if(windows.begin(),windows.end(),[this](const auto& w){return w.id==original.id;});
    if(own==windows.end())return;
    auto rect=own->rect;
    if(rect.getWidth()>bounds.getWidth()||rect.getHeight()>bounds.getHeight()){error="Screen too small for full game panel";noSpace=true;return;}
    rect.setPosition(std::clamp(original.rect.getX(),bounds.getX(),bounds.getRight()-rect.getWidth()),
                     std::clamp(original.rect.getY(),bounds.getY(),bounds.getBottom()-rect.getHeight()));
    const auto eligible=[this](const Window& w){return w.app.containsIgnoreCase("bitwig") || (w.pid>0&&w.pid==original.pid);};
    const auto freeOfFixed=[&](juce::Rectangle<int> candidate){
        return bounds.contains(candidate) && std::none_of(windows.begin(),windows.end(),[&](const auto& w){
            return w.id!=original.id && !eligible(w) && w.rect.intersects(candidate);
        });
    };
    if(!freeOfFixed(rect)) {
        std::vector<juce::Rectangle<int>> candidates;
        for(const auto& w:windows)if(w.id!=original.id&&!eligible(w)) {
            for(auto point:{juce::Point<int>(w.rect.getRight()+16,rect.getY()),
                            juce::Point<int>(w.rect.getX()-rect.getWidth()-16,rect.getY()),
                            juce::Point<int>(rect.getX(),w.rect.getBottom()+16),
                            juce::Point<int>(rect.getX(),w.rect.getY()-rect.getHeight()-16)}) {
                const auto candidate=rect.withPosition(point);
                if(freeOfFixed(candidate))candidates.push_back(candidate);
            }
        }
        if(candidates.empty()){error="No free screen area for game panel";noSpace=true;return;}
        rect=*std::min_element(candidates.begin(),candidates.end(),[&](auto a,auto b){
            return a.getPosition().getDistanceSquaredFrom(original.rect.getPosition())
                 < b.getPosition().getDistanceSquaredFrom(original.rect.getPosition());
        });
    }
    if(!move(own->id,rect.getPosition()))return;
    moved.push_back({original,rect});
    std::vector<std::pair<int64_t,juce::Rectangle<int>>> occupied{{original.id,rect}};
    for(const auto& w:windows)if(w.id!=original.id)occupied.push_back({w.id,w.rect});
    for(const auto& w:windows)if(w.id!=original.id) {
        if(!w.app.containsIgnoreCase("bitwig")&&!(w.pid>0&&w.pid==original.pid)) {continue;}
        if(!w.rect.intersects(rect)){continue;}
        bool placed=false;
        for(auto point:{juce::Point<int>(rect.getRight()+16,w.rect.getY()),juce::Point<int>(rect.getX()-w.rect.getWidth()-16,w.rect.getY()),
                        juce::Point<int>(w.rect.getX(),rect.getBottom()+16),juce::Point<int>(w.rect.getX(),rect.getY()-w.rect.getHeight()-16)}) {
            auto candidate=w.rect.withPosition(point);
            if(bounds.contains(candidate)&&std::none_of(occupied.begin(),occupied.end(),[&](auto r){return r.first!=w.id && r.second.intersects(candidate);})) {
                if(move(w.id,point)){moved.push_back({w,candidate});for(auto& entry:occupied)if(entry.first==w.id)entry.second=candidate;placed=true;}break;
            }
        }
        if(!placed){error="Not enough space to separate all plugin windows";noSpace=true;}
    }
}
void GameLayout::prepareRestore()
{
    if(!armed||!scan())return;
    for(const auto& w:windows)if(w.id==original.id) {
        ownRestorePoint=noSpace ? original.rect.getPosition() : w.rect.getPosition();restoreOwn=true;
        for(const auto& change:moved)if(change.original.id==w.id && w.rect.getPosition()==change.placed.getPosition())
            ownRestorePoint=original.rect.getPosition();
    }
}
void GameLayout::restore()
{
    if(original.bitwigOwned){notifyOwner();original={};return;}
    if(!armed||!scan())return;
    // Host resizing may auto-center the parent. Compare manual movement BEFORE
    // shrinking, not the recentered position observed after the host resize.
    if(restoreOwn)for(const auto& w:windows)if(w.id==original.id)move(w.id,ownRestorePoint);
    for(const auto& change:moved)for(const auto& w:windows)if(w.id==change.original.id && !(restoreOwn&&w.id==original.id)) {
        // Respect manual movement made during the game. Size may already have shrunk.
        if(w.rect.getPosition()==change.placed.getPosition())move(w.id,change.original.rect.getPosition());
    }
    moved.clear();armed=false;restoreOwn=false;
}
