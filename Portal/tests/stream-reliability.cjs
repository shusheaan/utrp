// Restart/eviction regression: mocks only, no account or real playback changes.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
const items=start=>Array.from({length:100},(_,i)=>({kind:'track',id:String(start+i).padStart(11,'0'),title:`Song ${start+i}`,subtitle:'Artist',section:''}));
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
 try{
  for(const width of [320,390,768])for(const view of ['liked','recommended']){
   const page=await browser.newPage({viewport:{width,height:844},isMobile:true,hasTouch:true});
   const errors=[],reads=[],plays=[];let restarted=false,failNetwork=false;
   let status={status:'paused',track_id:'00000000000',title:'Song 0',artist:'Artist',position:10,duration:180,repeat:'one',shuffle:false};
   page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(()=>localStorage.setItem('portal-source','stream'));
   await page.route('http://portal.test/**',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.pathname==='/api/library')return route.fulfill({json:[]});
    if(url.pathname.endsWith('/status'))return route.fulfill({json:status});
    if(url.pathname==='/api/stream/like')return route.fulfill({json:{id:url.searchParams.get('id'),liked:false}});
    if(url.pathname==='/api/stream/control'){
     const body=req.postDataJSON();plays.push(body);
     const selected=body.metadata[body.index];assert.equal(selected.id,body.ids[body.index]);
     status={...status,title:selected.title,artist:selected.artist,track_id:selected.id};
     return route.fulfill({json:status});
    }
    if(url.pathname==='/api/stream/browse'){
     const requested=url.searchParams.get('view');
     if(view==='liked'&&requested==='recommended')return route.fulfill({json:{items:[],next_cursor:null}});
     assert.equal(requested,view);
     const cursor=url.searchParams.get('cursor')||'';reads.push(cursor);
     if(failNetwork)return route.fulfill({status:502,json:{error:'Temporary network failure'}});
     if(cursor.startsWith('old:')&&restarted)return route.fulfill({status:409,json:{error:'Expired cursor'}});
     const offset=Number(cursor.split(':')[1]||0);
     return route.fulfill({json:{items:items(offset),next_cursor:offset<200?`${restarted?'new':'old'}:${offset+100}`:null}});
    }
    const file=url.pathname==='/'?'index.html':url.pathname.slice(1);
    assert(['index.html','app.js','style.css'].includes(file));
    return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
   });
   const count=n=>page.waitForFunction(n=>document.querySelectorAll('#stream-list .row').length===n,n);
   await page.goto('http://portal.test/');await page.locator('#stream').click();
   if(view==='liked'){
    await page.waitForFunction(()=>!document.querySelector('#stream-refresh').disabled);
    await page.locator('[data-view=liked]').click();
   }
   await count(100);await page.waitForTimeout(120);assert.deepEqual(reads,['']);
   await page.evaluate(()=>window.firstRow=document.querySelector('#stream-list .row'));
   restarted=true;
   // Previously loaded rows remain playable; no browse refresh or POST retry.
   await page.locator('#stream-list .row').nth(1).click();
   await page.waitForFunction(()=>!document.body.classList.contains('busy'));
   assert.equal(plays.length,1);assert.equal(plays[0].metadata[plays[0].index].artist,'Artist');assert.deepEqual(reads,['']);
   // Expired continuation transparently replays the prefix, appends only new rows.
   await page.evaluate(()=>document.querySelector('#stream-scroll').scrollTo(0,1e6));
   const scroll=await page.locator('#stream-scroll').evaluate(e=>e.scrollTop);
   await count(200);
   assert.deepEqual(reads,['','old:100','','new:100']);
   assert(await page.evaluate(()=>window.firstRow===document.querySelector('#stream-list .row')));
   assert(Math.abs(await page.locator('#stream-scroll').evaluate(e=>e.scrollTop)-scroll)<2);
   assert.equal(await page.locator('#stream-message').textContent(),'');
   // Actual network failures are not hidden or retried forever. Existing rows stay.
   failNetwork=true;await page.locator('#stream-more').scrollIntoViewIfNeeded();
   await page.waitForFunction(()=>document.querySelector('#stream-more').textContent==='Retry loading more');
   const failedReads=reads.length;await page.waitForTimeout(400);assert.equal(reads.length,failedReads);
   assert.equal(await page.locator('#stream-list .row').count(),200);
   failNetwork=false;await page.locator('#stream-more').click();await count(300);
   assert(await page.locator('#stream-more').isHidden());
   assert.equal(await page.locator('#stream-list .row').evaluateAll(rows=>new Set(rows.map(r=>r.dataset.track)).size),300);
   // Partial same-song polls retain artist; a different song must not inherit it.
   status={...status,artist:''};
   await page.evaluate(s=>update(s),status);assert.equal(await page.locator('#artist').textContent(),'Artist');
   const right=await page.locator('#like').evaluate(e=>e.getBoundingClientRect().right);
   status={...status,track_id:'99999999999',title:'Next song',artist:''};
   await page.evaluate(s=>update(s),status);assert(await page.locator('#artist').isHidden());
   const missingRight=await page.locator('#like').evaluate(e=>e.getBoundingClientRect().right);
   assert(Math.abs(right-missingRight)<1,'Heart must stay right-aligned without artist');
   await page.screenshot({path:`/tmp/portal-reliability-${view}-${width}.png`});
   assert.deepEqual(errors,[]);await page.close();
   console.log(`PASS ${view} ${width}px: cached rows play, 409 auto-recovery, stable DOM/scroll, bounded network retry, metadata and heart alignment`);
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
