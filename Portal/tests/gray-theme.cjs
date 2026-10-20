// Mocked playback: selected surfaces share a color and seeking stays functional.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',headless:true});
 try {
  for(const width of [320,390,768]) {
   const page=await browser.newPage({viewport:{width,height:844},deviceScaleFactor:3,isMobile:true,hasTouch:true,reducedMotion:'reduce'});
   const errors=[],commands=[];page.on('pageerror',e=>errors.push(e.message));
   const track={id:'abcdefghijk',title:'Selected song',artist:'Artist',album:'Album'};
   let current={status:'playing',track_id:track.id,title:track.title,artist:track.artist,position:120,duration:240,repeat:'one'};
   await page.route('http://portal.test/**',async route=>{
    const glowFixture=require('./soft-glow-fixture.cjs')(route);if(glowFixture)return glowFixture;
    const url=new URL(route.request().url());
    if(url.pathname==='/api/library')return route.fulfill({json:[track]});
    if(url.pathname==='/api/status')return route.fulfill({json:current});
    if(url.pathname==='/api/stream/status')return route.fulfill({json:{...current,status:'stopped'}});
    if(url.pathname==='/api/control'){
     const command=route.request().postDataJSON();commands.push(command);assert.equal(command.action,'seek');current={...current,position:command.seconds};return route.fulfill({json:current});
    }
    if(url.pathname==='/api/stream/browse')return route.fulfill({json:{account:'Example',items:[{...track,kind:'track',subtitle:'Artist',section:''}],next_cursor:null}});
    const file=url.pathname==='/'?'index.html':url.pathname.slice(1);assert(['index.html','app.js','style.css'].includes(file));
    return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
   });
   await page.goto('http://portal.test/');await page.waitForFunction(()=>document.querySelector('#seek').value==='120');
   await page.locator('#search').fill('Selected');await page.locator('#search').press('Enter');
   // Seamless black surfaces: no separators, while sticky/fixed clipping stays intact.
   const surfaces=await page.evaluate(()=>['header','main','footer'].map(selector=>{
    const s=getComputedStyle(document.querySelector(selector));
    return {borderTop:s.borderTopWidth,borderBottom:s.borderBottomWidth,shadow:s.boxShadow,background:s.backgroundColor,position:s.position};
   }));
   for(const surface of surfaces){assert.equal(surface.borderTop,'0px');assert.equal(surface.borderBottom,'0px');assert.equal(surface.shadow,'none');}
   assert.equal(surfaces[0].background,'rgb(0, 0, 0)');assert.equal(surfaces[2].background,'rgb(0, 0, 0)');
   assert.equal(surfaces[0].position,'sticky');assert.equal(surfaces[2].position,'fixed');
   const colors=await page.evaluate(()=>['.source-tabs .selected','.row.current','#play'].map(s=>getComputedStyle(document.querySelector(s)).backgroundColor));
   assert.deepEqual(colors,Array(3).fill('rgb(65, 65, 65)'));
   const spacing=await page.evaluate(()=>{
    const footer=document.querySelector('footer'), now=document.querySelector('.now');
    return {top:parseFloat(getComputedStyle(document.querySelector('header')).paddingTop),bottom:parseFloat(getComputedStyle(footer).paddingBottom),gap:now.getBoundingClientRect().top-footer.getBoundingClientRect().top,
     height:footer.getBoundingClientRect().height,mainPadding:parseFloat(getComputedStyle(document.querySelector('main')).paddingBottom),
     progress:getComputedStyle(document.documentElement).getPropertyValue('--progress-color').trim()};
   });
   assert.equal(spacing.top,14);assert.equal(spacing.bottom,11);assert.equal(spacing.gap,32);assert.equal(spacing.height,143);assert.equal(spacing.mainPadding,spacing.height);assert.equal(spacing.progress,'#fff');
   const clipping=await page.evaluate(()=>({gap:parseFloat(getComputedStyle(document.querySelector('.list')).gap),
    clip:getComputedStyle(document.querySelector('.row')).clipPath,overflow:getComputedStyle(document.querySelector('#local-scroll')).overflowY}));
   assert.equal(clipping.gap,4);assert.equal(clipping.clip,'none');assert.equal(clipping.overflow,'auto');
   const glyphs=await page.locator('nav .selected,.row.current .rowtitle,#title').evaluateAll(es=>es.map(e=>{const s=getComputedStyle(e);return s.textShadow!=='none'||s.filter!=='none';}));
   assert(glyphs.every(Boolean),'Selected text and now-playing labels have static soft glow');
   const glows=await page.evaluate(()=>['.source-tabs .selected','.row.current','#play'].map(s=>getComputedStyle(document.querySelector(s)).boxShadow));
   assert(glows.every(s=>s===glows[0] && s!=='none'));assert.equal(glows[0],'rgba(180, 180, 180, 0.28) 0px 0px 2px 0px');
   assert.equal(await page.locator('#stream').evaluate(e=>getComputedStyle(e).boxShadow),'none');
   const rules=await page.evaluate(()=>Array.from(document.styleSheets).flatMap(s=>Array.from(s.cssRules)).filter(r=>r.selectorText?.startsWith('#seek::')).map(r=>({selector:r.selectorText,width:r.style.width,height:r.style.height,radius:r.style.borderRadius,background:r.style.background})));
   for(const suffix of ['-webkit-slider-thumb']){
    const rule=rules.find(r=>r.selector===`#seek::${suffix}`);assert(rule);
    assert.equal(rule.width,'var(--seek-thumb-size)');assert.equal(rule.height,'var(--seek-thumb-size)');assert.equal(rule.radius,'50%');assert.equal(rule.background,'var(--progress-color)');
   }
   assert.equal(await page.locator('#seek').evaluate(e=>getComputedStyle(e).getPropertyValue('--seek-thumb-size').trim()),'14px');
   assert.equal(await page.locator('#seek').evaluate(e=>getComputedStyle(e).getPropertyValue('--seek-track-size').trim()),'4px');
   assert(rules.find(r=>r.selector==='#seek::-webkit-slider-runnable-track').background.includes('var(--progress-color)'));
   assert.equal(await page.locator('#seek').evaluate(e=>e.style.getPropertyValue('--progress')),'50%');
   // Compare rendered pixels with/without the row glow: visible beyond the capsule,
   // with enough gutter for a natural fade instead of a hard clip.
   await page.locator('#search').blur();
   const bounds=await page.locator('.row.current').boundingBox();
   const clip={x:0,y:Math.floor(bounds.y)-4,width,height:Math.ceil(bounds.height)+8};
   const glowing=await page.screenshot({clip});
   await page.locator('.row.current').evaluate(e=>e.style.boxShadow='none');
   const plain=await page.screenshot({clip});
   await page.locator('.row.current').evaluate(e=>e.style.removeProperty('box-shadow'));
   const pixels=await page.evaluate(async({images,bounds,clip})=>{
    const data=await Promise.all(images.map(async encoded=>{
     const img=new Image();img.src=`data:image/png;base64,${encoded}`;await img.decode();
     const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=img.height;
     const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);
     return {bytes:ctx.getImageData(0,0,img.width,img.height).data,width:img.width};
    }));
    const scale=pixelsWidth=>pixelsWidth/clip.width;let visible=0,spill=0;
    for(let i=0;i<data[0].bytes.length;i+=4){
     const difference=Math.max(...[0,1,2].map(c=>Math.abs(data[0].bytes[i+c]-data[1].bytes[i+c])));
     if(difference<2)continue;
     const y=clip.y+(Math.floor(i/4/data[0].width)+.5)/scale(data[0].width);
     if(y<bounds.y||y>=bounds.y+bounds.height)visible++;
     if(y<bounds.y-4||y>=bounds.y+bounds.height+4)spill++;
    }
    return {visible,spill};
   },{images:[glowing.toString('base64'),plain.toString('base64')],bounds,clip});
   assert(pixels.visible>0,'Glow must be visible outside the selected capsule');
   assert.equal(pixels.spill,0,'Small glow must fade inside the reserved gutter');
   await page.screenshot({path:`/tmp/portal-gray-${width}.png`});
   await page.locator('#seek').screenshot({path:`/tmp/portal-gray-seek-${width}.png`});
   // Drag preview updates fill immediately, without a playback command until change.
   await page.locator('#seek').evaluate(e=>{e.value='180';e.dispatchEvent(new Event('input',{bubbles:true}));});
   assert.equal(await page.locator('#seek').evaluate(e=>e.style.getPropertyValue('--progress')),'75%');assert.equal(commands.length,0);
   await page.locator('#seek').evaluate(e=>e.dispatchEvent(new Event('change',{bubbles:true})));
   await page.waitForFunction(()=>!document.body.classList.contains('busy'));assert.deepEqual(commands,[{action:'seek',seconds:180}]);
   // Keyboard access and native change semantics remain intact.
   await page.locator('#seek').focus();await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>!document.body.classList.contains('busy'));
   assert.equal(commands.at(-1).seconds,181);
   for(const [seconds,percent] of [[0,'0%'],[240,'100%']]) {
    await page.locator('#seek').evaluate((e,value)=>{e.value=String(value);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));},seconds);
    await page.waitForFunction(()=>!document.body.classList.contains('busy'));
    assert.equal(await page.locator('#seek').evaluate(e=>e.style.getPropertyValue('--progress')),percent);
    assert.equal(commands.at(-1).seconds,seconds);
   }
   await page.locator('#stream').click();await page.waitForFunction(()=>document.querySelector('#stream-list .row.current'));
   assert.equal(await page.locator('#stream-list .row.current').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(65, 65, 65)');
   assert.equal(await page.locator('.stream-tabs .selected').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(65, 65, 65)');
   assert.equal(await page.locator('#stream').evaluate(e=>getComputedStyle(e).boxShadow),glows[0]);
   assert.equal(await page.locator('#local').evaluate(e=>getComputedStyle(e).boxShadow),'none');
   assert.equal(await page.locator('.stream-tabs .selected').evaluate(e=>getComputedStyle(e).boxShadow),glows[0]);
   assert.equal(await page.locator('#stream-list .row.current').evaluate(e=>getComputedStyle(e).boxShadow),glows[0]);
   assert.deepEqual(errors,[]);console.log(`PASS ${width}px: subtle shared gray glow, 32px player inset, white round thumb/progress, seek and keyboard`);await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
