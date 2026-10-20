// Mock-only: no Google account mutations or real player control.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
const songs=Array.from({length:100},(_,i)=>({kind:'track',id:String(i).padStart(11,'0'),title:`Song ${i}`,subtitle:'Artist',section:''}));
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
 try {
  for(const width of [320,390,768]){
   const page=await browser.newPage({viewport:{width,height:844},isMobile:true,hasTouch:true});
   const errors=[],writes=[],browses=[],liked=new Set();let fail=false,delayRead=null,delayWrite=null,delayLiked=null;
   let current={status:'paused',track_id:songs[0].id,title:'Song 0',artist:'Artist',position:2,duration:200,repeat:'one',shuffle:false};
   page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>localStorage.setItem('portal-source','stream'));
   await page.route('http://portal.test/**',async route=>{
    const glowFixture=require('./soft-glow-fixture.cjs')(route);if(glowFixture)return glowFixture;
    const req=route.request(),url=new URL(req.url());
    if(url.pathname==='/api/library')return route.fulfill({json:[]});
    if(url.pathname.endsWith('/status'))return route.fulfill({json:current});
    if(url.pathname==='/api/stream/like'){
     const body=req.method()==='POST'?req.postDataJSON():null,id=body?.id || url.searchParams.get('id');
     if(body){
      writes.push(body);assert.equal(req.headers()['x-portal-request'],'1');
      if(delayWrite){const wait=delayWrite;delayWrite=null;await wait;}
      if(fail)return route.fulfill({status:502,json:{error:'Rating not confirmed'}});
      body.liked?liked.add(id):liked.delete(id);
     }else if(delayRead){const wait=delayRead;delayRead=null;await wait;}
     return route.fulfill({json:{id,liked:liked.has(id)}});
    }
    if(url.pathname==='/api/stream/browse'){
     const view=url.searchParams.get('view');browses.push(view);
     const items=view==='liked'?songs.filter(s=>liked.has(s.id)):view==='playlists'?[{kind:'playlist',id:'PLtest',title:'Test playlist',subtitle:''},...songs]:songs;
     if(view==='liked' && delayLiked){const wait=delayLiked;delayLiked=null;await wait;}
     return route.fulfill({json:{account:'Example',items,next_cursor:null}});
    }
    const file=url.pathname==='/'?'index.html':url.pathname.slice(1);
    assert(['index.html','app.js','style.css'].includes(file));
    return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
   });
   const idle=()=>page.waitForFunction(()=>!document.querySelector('#stream-refresh').disabled);
   const heart=value=>page.waitForFunction(v=>document.querySelector('#like').getAttribute('aria-pressed')===String(v)&&!document.querySelector('#like').disabled,value);
   await page.goto('http://portal.test/');await heart(false);
   assert(await page.locator('#like').isVisible()); // actual playback source, not selected tab
   await page.locator('#stream').click();await idle();
   for(const view of ['recommended','playlists','search']){
    await page.locator(`[data-view=${view}]`).click();
    if(view==='search'){await page.locator('#stream-search').fill('song');await page.locator('#stream-search').press('Enter');}
    await idle();
    if(view==='playlists'){await page.locator('#stream-list .row').first().click();await idle();}
    await page.evaluate(()=>document.querySelector('#stream-scroll').scrollTo(0,1200));await page.waitForTimeout(80);
    const geometry=await page.evaluate(()=>{
     const h=document.querySelector('header').getBoundingClientRect(),t=document.querySelector('#stream-toolbar').getBoundingClientRect(),r=document.querySelector('#stream-refresh').getBoundingClientRect();
     return {top:t.top,header:h.bottom,refresh:r.top,overflow:document.documentElement.scrollWidth>innerWidth};
    });
    assert(Math.abs(geometry.top-geometry.header-32)<1);if(view!=='search')assert(geometry.refresh>=geometry.header);else assert(await page.locator('#stream-refresh').isHidden());assert(!geometry.overflow);
    if(view==='playlists')assert(await page.locator('#stream-back').isVisible());
    if(width===390 && view==='recommended')await page.screenshot({path:'/tmp/portal-sticky-stream-390.png'});
    const count=browses.length;if(view==='search')await page.locator('#stream-search').press('Enter');else await page.locator('#stream-refresh').click();await idle();assert.equal(browses.length,count+1);
   }
   // No optimistic heart: wait for server confirmation, then silently refresh Liked.
   let release;delayWrite=new Promise(resolve=>release=resolve);
   await page.locator('#like').click();await page.waitForFunction(()=>document.querySelector('#like').disabled);
   assert.equal(await page.locator('#like').getAttribute('aria-pressed'),'false');release();await heart(true);
   assert(await page.locator('#notice').isHidden());assert.deepEqual(writes[0],{id:songs[0].id,liked:true});
   await page.locator('[data-view=liked]').click();await idle();assert.equal(await page.locator('#stream-list .rowtitle').textContent(),'Song 0');
   await page.reload();await heart(true); // restored from upstream, not browser memory
   await page.locator('#stream').click();await idle();await page.locator('[data-view=liked]').click();await idle();
   await page.locator('#like').click();await heart(false);await idle();assert.equal(await page.locator('#stream-list .row').count(),0);
   // In-flight first pages are discarded and retried if a rating changes.
   let releaseLiked;delayLiked=new Promise(resolve=>releaseLiked=resolve);
   await page.locator('#stream-refresh').click();
   await page.waitForFunction(()=>document.querySelector('#stream-refresh').disabled);
   await page.locator('#like').click();await heart(true);releaseLiked();await idle();
   assert.equal(await page.locator('#stream-list .rowtitle').textContent(),'Song 0');
   await page.locator('#like').click();await heart(false);await idle();
   fail=true;await page.locator('#like').click();await page.waitForFunction(()=>document.querySelector('#notice').textContent==='Rating not confirmed');
   assert.equal(await page.locator('#like').getAttribute('aria-pressed'),null);
   fail=false;const before=writes.length;await page.locator('#like').click();await heart(false);assert.equal(writes.length,before); // unknown reloads, never toggles blindly
   // Late reads cannot paint the next track or Local playback.
   let releaseRead;delayRead=new Promise(resolve=>releaseRead=resolve);
   await page.evaluate(id=>update({track_id:id,title:'Other',artist:'Artist',status:'paused',position:0,duration:200,repeat:'one'}),songs[1].id);
   await page.waitForTimeout(40);
   await page.evaluate(()=>{setSource('local');update({track_id:'local.flac',title:'Local',artist:'Artist',status:'paused',position:0,duration:200,repeat:'one'});});
   releaseRead();await page.waitForTimeout(100);assert(await page.locator('#like').isHidden());
   current={...current,status:'playing'};
   await page.evaluate(s=>{setSource('stream');update(s);},current);await heart(false);
   await page.screenshot({path:`/tmp/portal-rating-${width}.png`});
   assert.deepEqual(errors,[]);await page.close();
   console.log(`PASS ${width}px: sticky Stream controls/search/detail, confirmed Like/Unlike, Liked refresh, reload, failure recovery, Local hidden, stale read ignored`);
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
