// Geometry and mobile screenshots for both states; mocked controls only.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',headless:true});
 try {
  for(const [width,dpr] of [[320,2],[390,3],[768,2]]) {
   const page=await browser.newPage({viewport:{width,height:844},deviceScaleFactor:dpr,isMobile:true,hasTouch:true});
   let playing=true;const errors=[],commands=[];page.on('pageerror',e=>errors.push(e.message));
   const status=()=>({status:playing?'playing':'paused',title:'A centered player',artist:'Artist',position:30,duration:240,repeat:'one'});
   await page.route('http://portal.test/**',async route=>{
    const glowFixture=require('./soft-glow-fixture.cjs')(route);if(glowFixture)return glowFixture;
    const url=new URL(route.request().url());
    if(url.pathname==='/api/library')return route.fulfill({json:[]});
    if(url.pathname==='/api/status')return route.fulfill({json:status()});
    if(url.pathname==='/api/stream/status')return route.fulfill({json:{...status(),status:'stopped'}});
    if(url.pathname==='/api/control'){
     const command=route.request().postDataJSON();assert.deepEqual(command,{action:'toggle'});commands.push(command);playing=!playing;
     await new Promise(resolve=>setTimeout(resolve,300));
     return route.fulfill({json:status()});
    }
    const file=url.pathname==='/'?'index.html':url.pathname.slice(1);assert(['index.html','app.js','style.css'].includes(file));
    return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
   });
   await page.goto('http://portal.test/');await page.waitForFunction(()=>document.querySelector('#play').getAttribute('aria-label')==='Pause');
   await page.evaluate(()=>{window.originalPlaySvg=document.querySelector('#play svg');});
   for(const label of ['Pause','Play','Pause']) {
    await page.waitForFunction(label=>document.querySelector('#play').getAttribute('aria-label')===label,label);
    const geometry=await page.locator('#play').evaluate((button,label)=>{
     const circle=button.getBoundingClientRect(),svg=button.querySelector('svg'),box=svg.getBoundingClientRect();
     const visible=svg.querySelector(label==='Pause'?'#pause-icon':'#play-icon');
     const other=svg.querySelector(label==='Pause'?'#play-icon':'#pause-icon');
     // Pause uses the symmetric bounding-box center; Play uses its filled-area centroid.
     const b=visible.getBBox();
     const x=label==='Pause'?b.x+b.width/2:(9+18+9)/3;
     const y=label==='Pause'?b.y+b.height/2:(5+12+19)/3;
     const center=new DOMPoint(x,y).matrixTransform(visible.getScreenCTM());
     return {width:circle.width,height:circle.height,radius:getComputedStyle(button).borderRadius,
      svgDx:box.x+box.width/2-circle.x-circle.width/2,svgDy:box.y+box.height/2-circle.y-circle.height/2,
      inkDx:center.x-circle.x-circle.width/2,inkDy:center.y-circle.y-circle.height/2,
      hidden:getComputedStyle(other).display,visible:getComputedStyle(visible).display,
      stable:svg===window.originalPlaySvg,text:button.textContent.trim()};
    },label);
    assert.equal(geometry.width,36);assert.equal(geometry.height,36);assert.equal(geometry.radius,'50%');
    for(const key of ['svgDx','svgDy','inkDx','inkDy'])assert(Math.abs(geometry[key])<0.01,`${label}: ${key}=${geometry[key]}`);
    assert.equal(geometry.hidden,'none');assert.notEqual(geometry.visible,'none');assert(geometry.stable);assert.equal(geometry.text,'');
    await page.screenshot({path:`/tmp/portal-icon-${width}-${label.toLowerCase()}.png`});
    await page.locator('#play').screenshot({path:`/tmp/portal-button-${width}-${label.toLowerCase()}.png`});
    if(commands.length<2){
     await page.locator('#play').click();await page.waitForFunction(()=>document.body.classList.contains('busy'));
     await page.waitForTimeout(150);
     assert.equal(await page.locator('#play').evaluate(e=>getComputedStyle(e).opacity),'1','Pending toggle must not flash/dim the play button');
     await page.waitForFunction(()=>!document.body.classList.contains('busy'));
    }
   }
   assert.equal(commands.length,2);assert.deepEqual(errors,[]);
   console.log(`PASS ${width}px @${dpr}x: 36px circle, centered SVG/ink, both states, stable DOM and controls`);await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
