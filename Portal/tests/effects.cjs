// Isolated HTTP fixtures: never change the user's playback or account.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
 try {for(const width of [320,390,768]) for(const source of ['local','stream']) {
  const page=await browser.newPage({viewport:{width,height:844},isMobile:true,hasTouch:true});
  await page.addInitScript(source=>localStorage.setItem('portal-source',source),source);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let effects={fade:false,forced:false,a:null,b:null},preference=false,position=60,fail=false;
  const id=source==='stream'?'abcdefghijk':'Artist/Album/Test.wav';
  await page.route('http://portal.test/**',async route=>{
    const glowFixture=require('./soft-glow-fixture.cjs')(route);if(glowFixture)return glowFixture;
   const url=new URL(route.request().url());
   if(url.pathname==='/api/library')return route.fulfill({json:[]});
   if(url.pathname==='/api/stream/like')return route.fulfill({json:{id,liked:false}});
   if(url.pathname.endsWith('/status'))return route.fulfill({json:{status:'paused',track_id:id,title:'Quiet passage',artist:'Artist',position,duration:180,repeat:'one',shuffle:false,effects}});
   if(url.pathname==='/api/effects') {
    assert.equal(route.request().headers()['x-portal-request'],'1');
    const body=route.request().postDataJSON();assert.equal(body.source,source);assert.equal(body.track_id,id);
    if(fail)return route.fulfill({status:409,json:{error:'Track changed. Retry.'}});
    if(body.action==='fade') {preference=!preference;effects={...effects,fade:preference};}
    else if(effects.b!=null) effects={fade:preference,forced:false,a:null,b:null};
    else if(effects.a==null) effects={...effects,a:position};
    else effects={...effects,b:position,fade:true,forced:true};
    return route.fulfill({json:effects});
   }
   const file=url.pathname==='/'?'index.html':url.pathname.slice(1);
   assert(['index.html','app.js','style.css'].includes(file));
   return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
  });
  await page.goto('http://portal.test/');await page.waitForFunction(()=>!document.querySelector('#ab').disabled);
  const click=async selector=>{await page.locator(selector).click();await page.waitForFunction(()=>!document.body.classList.contains('busy'));};
  for(const original of [false,true]) {
   if(original)await click('#fade');
   assert.equal(await page.locator('#fade').getAttribute('aria-pressed'),String(original));
   position=60;await click('#ab');assert.equal(await page.locator('#ab-mode').textContent(),'B');
   assert(await page.locator('#marker-a').isVisible());assert(!(await page.locator('#marker-b').isVisible()));
   position=30;await click('#ab');assert.equal(await page.locator('#ab-mode').textContent(),'AB');
   assert.equal(await page.locator('#fade').getAttribute('aria-pressed'),'true');assert(await page.locator('#fade').isDisabled());
   const layout=await page.evaluate(()=>{
    const rect=s=>document.querySelector(s).getBoundingClientRect();const center=s=>{const r=rect(s);return r.x+r.width/2;};
    return {icons:[...document.querySelectorAll('.transport svg')].map(e=>[e.getBoundingClientRect().width,e.getBoundingClientRect().height]),
     a:center('#marker-a'),b:center('#marker-b'),fade:center('#fade'),ab:center('#ab'),play:center('#play'),
     height:rect('footer').height,overflow:document.documentElement.scrollWidth>innerWidth,
     colors:['#fade','#ab','#marker-a','#marker-b'].map(s=>getComputedStyle(document.querySelector(s)).color)};
   });
   assert.equal(layout.icons.length,9);assert(layout.icons.every(([w,h])=>w===21&&h===21));assert.equal(layout.height,143);assert(!layout.overflow);
   const order=await page.locator('.transport button').evaluateAll(buttons=>buttons.map(b=>({id:b.id||b.dataset.action,x:b.getBoundingClientRect().x,y:b.getBoundingClientRect().y+b.getBoundingClientRect().height/2})));
   assert.deepEqual(order.map(b=>b.id),['ab','fade','previous','backward','play','forward','next','shuffle','repeat']);
   assert(order.every((b,i)=>!i||b.x>order[i-1].x));assert(order.every(b=>Math.abs(b.y-order[0].y)<1));
   assert(layout.a>layout.b);assert(Math.abs(layout.play-width/2)<1);assert(layout.ab<layout.fade && layout.fade<layout.play);
   assert(layout.colors.every(c=>c==='rgb(255, 255, 255)'));
   await page.reload();await page.waitForFunction(()=>document.querySelector('#ab-mode').textContent==='AB');
   await page.screenshot({path:`/tmp/portal-effects-${source}-${width}.png`});
   await click('#ab');assert.equal(await page.locator('#ab-mode').textContent(),'A');
   assert.equal(await page.locator('#fade').getAttribute('aria-pressed'),String(original));
   assert(!(await page.locator('#marker-a').isVisible()));assert(!(await page.locator('#marker-b').isVisible()));
  }
  fail=true;await click('#ab');assert.equal(await page.locator('#ab-mode').textContent(),'A');assert.equal(await page.locator('#notice').textContent(),'Track changed. Retry.');
  assert.deepEqual(errors,[]);await page.close();console.log(`PASS ${source} ${width}px: A/B/AB, reversed markers, forced fade/restoration, reload, errors, 9 equal icons, unchanged compact height`);
 }} finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
