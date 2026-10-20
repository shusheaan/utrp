// Isolated APIs: no real playback or account access.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',headless:true});
 try {
  for(const width of [320,390,768]) for(const source of ['local','stream']) {
   const page=await browser.newPage({viewport:{width,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true,reducedMotion:'reduce'});
   const errors=[],commands=[];page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(value=>localStorage.setItem('portal-source',value),source);
   let current={status:'paused',track_id:null,title:'Test song',artist:'Artist',position:20,duration:240,repeat:'one',shuffle:false};
   let fail=false;
   await page.route('http://portal.test/**',async route=>{
    const glowFixture=require('./soft-glow-fixture.cjs')(route);if(glowFixture)return glowFixture;
    const url=new URL(route.request().url());
    if(url.pathname==='/api/library')return route.fulfill({json:[]});
    if(url.pathname.endsWith('/status'))return route.fulfill({json:current});
    if(url.pathname.endsWith('/control')) {
     assert.equal(url.pathname,source==='local'?'/api/control':'/api/stream/control');
     const command=route.request().postDataJSON();assert.deepEqual(command,{action:'shuffle'});commands.push(command);
     if(fail)return route.fulfill({status:502,json:{error:'Player unavailable'}});
     current={...current,shuffle:!current.shuffle};return route.fulfill({json:current});
    }
    const file=url.pathname==='/'?'index.html':url.pathname.slice(1);
    assert(['index.html','app.js','style.css'].includes(file));
    return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
   });
   await page.goto('http://portal.test/');await page.waitForFunction(()=>document.querySelector('#title').textContent==='Test song');
   const shape=await page.evaluate(()=>{
    const rect=s=>document.querySelector(s).getBoundingClientRect();
    const center=s=>{const r=rect(s);return {x:r.x+r.width/2,y:r.y+r.height/2};};
    return {ab:center('#ab'),fade:center('#fade'),shuffle:center('#shuffle svg'),repeat:center('#repeat svg'),play:center('#play'),
     sizes:['#shuffle svg','#repeat svg','[data-action=next] svg','[data-action=previous] svg','[data-action=forward] svg','[data-action=backward] svg','#play svg'].map(s=>({width:rect(s).width,height:rect(s).height})),
     colors:['#shuffle','#repeat'].map(s=>getComputedStyle(document.querySelector(s)).color),
     footer:rect('footer').height,overflow:document.documentElement.scrollWidth>innerWidth};
   });
   assert.deepEqual(shape.colors,['rgb(128, 128, 128)','rgb(255, 255, 255)']);
   assert(shape.sizes.every(s=>s.width===21 && s.height===21));
   assert(shape.play.x<shape.shuffle.x && shape.shuffle.x<shape.repeat.x);
   assert(Math.abs(shape.play.x-shape.fade.x-(shape.shuffle.x-shape.play.x))<.1);
   assert(Math.abs(shape.play.x-shape.ab.x-(shape.repeat.x-shape.play.x))<.1);
   assert(Math.abs(shape.repeat.y-shape.shuffle.y)<.1);assert.equal(shape.footer,143);assert(!shape.overflow);
   assert.equal(await page.locator('#shuffle').getAttribute('aria-pressed'),'false');
   assert.equal((await page.locator('#shuffle').textContent()).trim(),'');
   for(const label of ['On','Off']){
    await page.locator('#shuffle').click();await page.waitForFunction(()=>!document.body.classList.contains('busy'));
    assert.equal(await page.locator('#shuffle').evaluate(e=>getComputedStyle(e).color),label==='On'?'rgb(255, 255, 255)':'rgb(128, 128, 128)');
    assert.equal(await page.locator('#shuffle').getAttribute('aria-label'),`Shuffle ${label.toLowerCase()}`);
    assert.equal(await page.locator('#shuffle').getAttribute('aria-pressed'),String(label==='On'));
    assert.equal(await page.locator('#repeat-mode').textContent(),'1');
   }
   fail=true;await page.locator('#shuffle').click();await page.waitForFunction(()=>!document.body.classList.contains('busy'));
   assert.equal(await page.locator('#shuffle').getAttribute('aria-pressed'),'false');
   assert.equal((await page.locator('#shuffle').textContent()).trim(),'');assert.equal(await page.locator('#notice').textContent(),'Player unavailable');
   fail=false;await page.locator('#shuffle').click();await page.waitForFunction(()=>!document.body.classList.contains('busy'));
   await page.reload();await page.waitForFunction(()=>document.querySelector('#shuffle').getAttribute('aria-pressed')==='true');
   assert.equal(commands.length,4);assert.deepEqual(errors,[]);
   await page.screenshot({path:`/tmp/portal-shuffle-${source}-${width}.png`});
   console.log(`PASS ${source} ${width}px: uniform 21px icons, white/gray state without text, real endpoint, failed toggle unchanged, reload restores status`);
   await page.close();
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
