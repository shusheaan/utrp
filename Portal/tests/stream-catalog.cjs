// Mock-only mobile checks: never authenticate or control real players.
const {chromium}=require('playwright');
const fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
const item=(kind,id,title,section='')=>({kind,id,title,subtitle:kind==='track'?'Singer':'',section});
const songs=Array.from({length:30},(_,i)=>item('track',String(i).padStart(11,'0'),`Song ${i}`,'Listen again'));
const search=[item('track','00000000001','Matching song','Songs'),item('artist','UCartist','Matching artist','Artists'),item('album','MPREalbum','Matching album','Albums'),item('playlist','PLone','Matching playlist','Playlists')];
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',headless:true});
 try {
  for(const width of [320,390,768]) {
   const page=await browser.newPage({viewport:{width,height:844},isMobile:true,hasTouch:true});
   const calls=[],errors=[];let failArtist=true;
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('http://portal.test/**',async route=>{
    const glowFixture=require('./soft-glow-fixture.cjs')(route);if(glowFixture)return glowFixture;
    const request=route.request();assert.equal(request.method(),'GET');const url=new URL(request.url());
    if(url.pathname==='/api/library')return route.fulfill({json:[]});
    if(url.pathname.endsWith('/status'))return route.fulfill({json:{status:'stopped',title:'',artist:'',position:0,duration:0,repeat:'one'}});
    if(url.pathname==='/api/stream/browse'){
     const view=url.searchParams.get('view'),cursor=url.searchParams.get('cursor');calls.push({view,cursor});
     let items=[],next_cursor=null;
     if(view==='recommended'){
      items=cursor?[item('track',songs[0].id,'Song 0','Recommended new songs'),...songs.slice(1).map(t=>({...t,section:'Recommended new songs'}))]:songs;
      next_cursor=cursor?null:'private-client-cursor';
     }else if(view==='search')items=search;
     else if(view==='artist'){
      if(failArtist){failArtist=false;return route.fulfill({status:502,json:{error:'Temporary failure'}});}
      items=[item('track','00000000001','Top song','Top songs'),item('album','MPREalbum','Artist album','Albums'),item('artist','UCrelated','Related artist','Similar artists')];
     }else if(view==='album'||view==='playlist')items=[item('track','00000000001','Album song')];
     else assert.fail(`Unexpected view: ${view}`);
     return route.fulfill({json:{account:'Example',items,next_cursor}});
    }
    const file=url.pathname==='/'?'index.html':url.pathname.slice(1);assert(['index.html','app.js','style.css'].includes(file));
    return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
   });
   const idle=()=>page.waitForFunction(()=>!document.querySelector('#stream-refresh').disabled);
   await page.goto('http://portal.test/');await page.locator('#stream').click();await idle();
   assert.equal(await page.locator('#stream-page h1').count(),0);
   assert.equal(await page.locator('#stream-account').count(),0);
   assert(!/Logged in as|Example/.test(await page.locator('#stream-page').innerText()));
   assert.deepEqual(await page.locator('[data-view]').allTextContents(),['Recommended','Liked','Playlists','Search']);
   assert.equal(await page.locator('#stream-list .row').count(),30);
   assert.equal(await page.locator('#stream-more').textContent(),'Load more');
   assert.equal(calls.length,1);
   await page.locator('#stream-more').scrollIntoViewIfNeeded();
   await page.waitForFunction(()=>document.querySelectorAll('#stream-list .row').length===60);await idle();
   assert.equal(await page.locator('#stream-list [data-track="00000000000"]').count(),2);
   assert.deepEqual(await page.locator('#stream-list h3').allTextContents(),['Listen again','Recommended new songs']);
   await page.locator('[data-view="search"]').click();assert.equal(calls.length,2);
   assert(await page.locator('#stream-heading-row').isHidden());assert(await page.locator('#stream-message').isHidden());
   const toolbar=await page.evaluate(()=>{
    const form=document.querySelector('#stream-search-form'), tabs=document.querySelector('.stream-tabs');
    const f=form.getBoundingClientRect(),t=tabs.getBoundingClientRect();
    return {width:f.width,tabWidth:t.width,height:f.height,tabHeight:t.height,
     font:getComputedStyle(form.querySelector('input')).fontSize,tabFont:getComputedStyle(tabs.querySelector('button')).fontSize,
     submit:document.querySelector('#stream-submit')!==null,icons:form.querySelectorAll('svg').length};
   });
   assert.equal(toolbar.width,toolbar.tabWidth);assert.equal(toolbar.height,toolbar.tabHeight);
   assert.equal(toolbar.font,'16px');assert.equal(toolbar.tabFont,'11px');assert.equal(toolbar.submit,false);assert.equal(toolbar.icons,1);
   assert(await page.locator('#stream-refresh').isHidden());
   assert(await page.locator('#stream-count').isHidden());
   await page.locator('#stream-search').press('Enter');assert.equal(calls.length,2);
   await page.locator('#stream-search').fill('example');await page.waitForTimeout(150);assert.equal(calls.length,2);await page.locator('#stream-search').press('Enter');await idle();
   assert.equal(await page.locator('#stream-list .rowtitle').textContent(),'Matching song');
   for(const kind of ['artist','album','playlist','track']){
    await page.locator(`[data-kind="${kind}"]`).click();assert.equal(await page.locator('#stream-list .row').count(),1);
   }
   assert.equal(calls.length,3); // Switching categories never requests again.
   await page.locator('#stream-search').press('Enter');await idle();assert.equal(calls.length,4);assert.equal(calls.at(-1).view,'search');
   await page.locator('#stream-search').press('Enter');await idle();assert.equal(calls.length,5);assert.equal(calls.at(-1).view,'search');
   const pills=await page.locator('[data-kind]').evaluateAll(rows=>rows.map(e=>({top:e.getBoundingClientRect().top,width:e.clientWidth,scroll:e.scrollWidth})));
   assert(pills.every(p=>p.top===pills[0].top && p.scroll<=p.width));
   await page.locator('[data-kind="artist"]').click();await page.locator('#stream-list .row').click();await idle();
   assert.equal(await page.locator('#stream-message').textContent(),'Temporary failure');assert(await page.locator('#stream-back').isHidden());
   await page.locator('#stream-list .row').click();await idle();
   assert.deepEqual(await page.locator('#stream-list h3').allTextContents(),['Top songs','Albums','Similar artists']);
   assert(await page.locator('#stream-categories').isHidden());assert(await page.locator('#stream-search-form').isHidden());
   await page.locator('#stream-list .row').nth(1).click();await idle();
   assert.equal(calls.at(-1).view,'album');await page.locator('#stream-refresh').click();await idle();assert.equal(calls.at(-1).view,'album');
   const beforeBack=calls.length;
   await page.locator('#stream-back').click();assert.equal(await page.locator('#stream-list .row').count(),3);
   await page.locator('#stream-back').click();assert.equal(await page.locator('#stream-list .rowtitle').textContent(),'Matching artist');
   assert.equal(await page.locator('#stream-search').inputValue(),'example');assert(await page.locator('#stream-back').isHidden());assert.equal(calls.length,beforeBack);
   for(const kind of ['album','playlist']){
    await page.locator(`[data-kind="${kind}"]`).click();await page.locator('#stream-list .row').click();await idle();assert.equal(calls.at(-1).view,kind);await page.locator('#stream-back').click();
    assert.equal(await page.locator('[data-kind].selected').getAttribute('data-kind'),kind);
   }
   await page.screenshot({path:`/tmp/portal-search-${width}.png`});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.deepEqual(errors,[]);
   console.log(`PASS ${width}px: real-shelf pagination, four result types, failure/retry, nested navigation and cached Back`);await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
