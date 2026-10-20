// Static glow must remain identical across playback states and pending controls.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
async function assertGlow(page) {
 const actual=await page.evaluate(()=>{
  const style=s=>getComputedStyle(document.querySelector(s));
  const row=document.querySelector('.row.current .rowtitle');
  return {title:style('#title').filter,row:getComputedStyle(row).filter,
   nav:[...document.querySelectorAll('nav .selected')].map(e=>({shadow:getComputedStyle(e).textShadow,weight:getComputedStyle(e).fontWeight})),
   artist:style('#artist').filter,artistShadow:style('#artist').textShadow,
   rowWeight:getComputedStyle(row).fontWeight,titleWeight:style('#title').fontWeight,
   capsule:style('.row.current').boxShadow};
 });
 assert.notEqual(actual.title,'none');assert.notEqual(actual.row,'none');
 assert(actual.nav.every(n=>n.shadow!=='none'&&n.weight==='600'));
 assert.equal(actual.artist,'none');assert.equal(actual.artistShadow,'none');
 assert.equal(actual.rowWeight,'400');assert.equal(actual.titleWeight,'600');
 assert.notEqual(actual.capsule,'none','Paused song keeps its selected capsule');
 return actual;
}
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
 try {for(const source of ['local','stream']){
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(source=>localStorage.setItem('portal-source',source),source);
  const track={id:'abcdefghijk',track_id:'abcdefghijk',title:'A warm ambient song',artist:'Quiet artist',duration:240,position:30,repeat:'off'};
  let playback='paused',failed=false,commands=0;
  const endpoint=source==='local'?'/api':'/api/stream';
  await page.route('http://portal.test/**',async route=>{
   const url=new URL(route.request().url());
   if(url.pathname==='/api/library')return route.fulfill({json:[track]});
   if(url.pathname.endsWith('/status')){
    if(failed&&url.pathname===endpoint+'/status')return route.fulfill({status:503,json:{error:'Offline'}});
    return route.fulfill({json:{...track,status:url.pathname===endpoint+'/status'?playback:'stopped'}});
   }
   if(url.pathname===endpoint+'/control'){
    assert.deepEqual(route.request().postDataJSON(),{action:'toggle'});commands++;
    await new Promise(resolve=>setTimeout(resolve,300));
    playback=playback==='playing'?'paused':'playing';
    return route.fulfill({json:{...track,status:playback}});
   }
   if(url.pathname==='/api/stream/like')return route.fulfill({json:{id:track.id,liked:false}});
   if(url.pathname==='/api/stream/browse')return route.fulfill({json:{items:[{...track,kind:'track',subtitle:track.artist}],next_cursor:null}});
   const file=url.pathname==='/'?'index.html':url.pathname.slice(1);
   assert(['index.html','app.js','style.css','soft-glow.css'].includes(file));
   return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
  });
  await page.goto('http://portal.test/');await page.waitForFunction(()=>document.querySelector('#title').textContent==='A warm ambient song');
  await page.locator('#search').fill('ambient');await page.locator('#search').press('Enter');
  if(source==='stream'){await page.locator('#stream').click();await page.waitForSelector('#stream-list .row.current');}
  const baseline=await assertGlow(page);
  for(const playing of [true,false,true]){
   await page.locator('#play').click();await page.waitForFunction(()=>document.body.classList.contains('busy'));
   assert.deepEqual(await assertGlow(page),baseline); // Pending requests do not flash the glow.
   await page.waitForFunction(()=>!document.body.classList.contains('busy'));
   assert.equal(await page.locator('#play').getAttribute('aria-label'),playing?'Pause':'Play');
   assert.deepEqual(await assertGlow(page),baseline);
  }
  // External pause/stop/loading updates arrive through the existing status poll.
  for(const status of ['paused','playing','loading','playing','stopped','playing']){
   playback=status;
   await page.waitForFunction(playing=>(document.querySelector('#play').getAttribute('aria-label')==='Pause')===playing,status==='playing');
   assert.deepEqual(await assertGlow(page),baseline);
  }
  failed=true;
  await page.waitForFunction(()=>document.querySelector('#notice').textContent==='Player not connected. Please retry.');
  assert.deepEqual(await assertGlow(page),baseline);
  failed=false;
  await page.waitForResponse(r=>new URL(r.url()).pathname===endpoint+'/status'&&r.status()===200);
  await assertGlow(page);
  await page.reload();await page.waitForResponse(r=>new URL(r.url()).pathname===endpoint+'/status'&&r.status()===200);
  await page.locator('#search').fill('ambient');await page.locator('#search').press('Enter');
  await assertGlow(page);assert.equal(commands,3);assert.deepEqual(errors,[]);
  console.log(`PASS ${source}: unchanged static glow across pending toggle, pause, stop, loading, disconnect, recovery and reload`);
  await page.close();
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
