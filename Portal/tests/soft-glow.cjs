// Static decoration must not sample audio, animate, change layout or clip capsule sides.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
// Compare real rendered pixels, not just the presence of a CSS shadow rule.
async function assertTextHalo(page, selector, truncated) {
 const element=page.locator(selector).first(),r=await element.boundingBox();
 if(truncated)assert(await element.evaluate(e=>e.scrollWidth>e.clientWidth),selector+': fixture must exercise ellipsis');
 const clip={x:Math.floor(r.x)-6,y:Math.floor(r.y)-6,width:Math.ceil(r.width)+12,height:Math.ceil(r.height)+12};
 const glowing=await page.screenshot({clip,captureBeyondViewport:false});
 await element.evaluate(e=>{e.style.filter='none';e.style.textShadow='none';});
 const plain=await page.screenshot({clip,captureBeyondViewport:false});
 await element.evaluate(e=>{e.style.removeProperty('filter');e.style.removeProperty('text-shadow');});
 const pixels=await page.evaluate(async({glowing,plain,r,clip})=>{
  const data=await Promise.all([glowing,plain].map(async base64=>{
   const image=new Image();image.src='data:image/png;base64,'+base64;await image.decode();
   const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
   const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);
   return {width:canvas.width,rgba:ctx.getImageData(0,0,canvas.width,canvas.height).data};
  }));
  const scale=data[0].width/clip.width,counts={left:0,right:0,top:0,bottom:0},strength={near:0,far:0},edge={left:0,right:0,top:0,bottom:0};
  for(let i=0;i<data[0].rgba.length;i+=4){
   const delta=Math.max(...[0,1,2].map(k=>Math.abs(data[0].rgba[i+k]-data[1].rgba[i+k])));
   const x=clip.x+((i/4)%data[0].width+.5)/scale;
   const y=clip.y+(Math.floor(i/4/data[0].width)+.5)/scale;
   if(x>=r.x&&x<r.x+r.width){
    if(y>=r.y&&y<r.y+.5)edge.top=Math.max(edge.top,delta);
    if(y>=r.y+r.height-.5&&y<r.y+r.height)edge.bottom=Math.max(edge.bottom,delta);
    if(delta>=1&&y<r.y)counts.top++;
    if(delta>=1&&y>=r.y+r.height)counts.bottom++;
   }
   if(y<r.y||y>=r.y+r.height)continue;
   const distance=x<r.x?r.x-x:x>=r.x+r.width?x-r.x-r.width:0;
   if(x>=r.x&&x<r.x+.5)edge.left=Math.max(edge.left,delta);
   if(x>=r.x+r.width-.5&&x<r.x+r.width)edge.right=Math.max(edge.right,delta);
   if(distance<=0)continue;
   if(delta>=1)counts[x<r.x?'left':'right']++;
   if(distance<2)strength.near=Math.max(strength.near,delta);
   if(distance>=5)strength.far=Math.max(strength.far,delta);
  }
  return {counts,strength,edge};
 },{glowing:glowing.toString('base64'),plain:plain.toString('base64'),r,clip});
 for(const side of ['left','right','top','bottom'])assert(pixels.counts[side]>0||pixels.edge[side]<=2,selector+': no bright halo may terminate at the '+side+' text edge '+JSON.stringify(pixels));
 assert(pixels.counts.left+pixels.counts.right>0,selector+': halo must escape the text box');
 assert(pixels.strength.near>pixels.strength.far&&pixels.strength.far<=2,selector+': halo must fade naturally before adjacent content');
}
async function assertListTypography(page) {
 const labels=await page.locator('.rowtitle,.rowmeta,#artist').evaluateAll(es=>es.map(e=>{
  const s=getComputedStyle(e),artist=e.matches('.rowmeta,#artist');
  return {artist,weight:s.fontWeight,color:s.color,filter:s.filter,shadow:s.textShadow};
 }));
 for(const label of labels){
  assert.equal(label.weight,'400');
  assert.equal(label.color,label.artist?'rgb(170, 166, 157)':'rgb(255, 255, 255)');
  if(label.artist){assert.equal(label.filter,'none');assert.equal(label.shadow,'none');}
 }
 const unchanged=await page.locator('.row.current').evaluateAll(rows=>rows.every(row=>{
  const geometry=()=>[...row.querySelectorAll('.rowtitle,.rowmeta')].map(e=>{
   const r=e.getBoundingClientRect(),s=getComputedStyle(e);
   return [r.x,r.y,r.width,r.height,s.fontSize,s.fontWeight,e.scrollWidth];
  });
  const selected=JSON.stringify(geometry());row.classList.remove('current');
  const plain=JSON.stringify(geometry());row.classList.add('current');return selected===plain;
 }));
 assert(unchanged,'Selection must not resize or reflow list text');
}
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
 try {for(const width of [320,390,768]){for(const size of ['long','short']){
  const page=await browser.newPage({viewport:{width,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true});
  const requests=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
  const track={id:'song',title:size==='long'?'Warm 光 · é · 👩‍🚀 ambient horizon — a long title '.repeat(3):'Warm ambient',artist:size==='long'?'Bright Artist with a very long name and ending':'Artist',album:'Ambient'};
  await page.route('http://portal.test/**',async route=>{
   const url=new URL(route.request().url());requests.push(url.pathname);
   if(url.pathname==='/api/library')return route.fulfill({json:[track,...Array.from({length:40},(_,i)=>({...track,id:'other'+i,title:'Other '+i}))]});
   if(url.pathname.endsWith('/status'))return route.fulfill({json:{...track,track_id:track.id,position:30,duration:180,repeat:'one',status:'playing'}});
   if(url.pathname==='/api/stream/like')return route.fulfill({json:{id:'song',liked:false}});
   if(url.pathname==='/api/stream/browse')return route.fulfill({json:{items:[{...track,kind:'track',subtitle:track.artist}],next_cursor:null}});
   const file=url.pathname==='/'?'index.html':url.pathname.slice(1);
   assert(['index.html','app.js','style.css','soft-glow.css'].includes(file),'Unexpected resource '+file);
   return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
  });
  await page.goto('http://portal.test/');
  await page.locator('#search').fill('ambient');await page.locator('#search').press('Enter');await page.locator('#search').blur();
  for(const selector of ['nav .selected','.row.current .rowtitle','#title']){
   const values=await page.locator(selector).first().evaluate(e=>{const s=getComputedStyle(e);return {weight:s.fontWeight,shadow:s.textShadow,filter:s.filter,animation:s.animationName};});
   assert.equal(values.weight,selector==='.row.current .rowtitle'?'400':'600');assert(values.shadow!=='none'||values.filter!=='none');assert.equal(values.animation,'none');
  }
  assert.equal(await page.locator('.row:not(.current) .rowtitle').first().evaluate(e=>getComputedStyle(e).fontWeight),'400');
  assert.equal(await page.locator('.row:not(.current) .rowtitle').first().evaluate(e=>getComputedStyle(e).textShadow),'none');
  assert.equal(await page.locator('#artist').evaluate(e=>getComputedStyle(e).color),'rgb(170, 166, 157)');
  await assertListTypography(page);
  assert.equal(await page.locator('canvas').count(),0);
  await page.waitForTimeout(250); // Let selection/hover transitions settle.
  const before=await page.screenshot();await page.waitForTimeout(600);
  assert(before.equals(await page.screenshot()),'Static glow pixels must not breathe or move');
  await page.emulateMedia({reducedMotion:'reduce'});
  assert(before.equals(await page.screenshot()),'Reduced motion has identical static appearance');
  // Measure each side independently, avoiding rounded corners and adjacent labels.
  for(const selector of ['.row.current','.source-tabs .selected','#play']){
   const element=page.locator(selector),r=await element.boundingBox();
   const clip={x:Math.floor(r.x)-4,y:Math.floor(r.y)-4,width:Math.ceil(r.width)+8,height:Math.ceil(r.height)+8};
   const glow=await page.screenshot({clip,captureBeyondViewport:false});await element.evaluate(e=>e.style.boxShadow='none');
   const plain=await page.screenshot({clip,captureBeyondViewport:false});await element.evaluate(e=>e.style.removeProperty('box-shadow'));
   const sides=await page.evaluate(async({glow,plain,r,clip})=>{
    const images=await Promise.all([glow,plain].map(async data=>{
     const image=new Image();image.src='data:image/png;base64,'+data;await image.decode();
     const c=document.createElement('canvas');c.width=image.width;c.height=image.height;const ctx=c.getContext('2d');ctx.drawImage(image,0,0);
     return {pixels:ctx.getImageData(0,0,c.width,c.height).data,width:c.width};
    }));
    const sides={left:0,right:0,top:0,bottom:0},scale=images[0].width/clip.width;
    for(let i=0;i<images[0].pixels.length;i+=4){
     if(Math.max(...[0,1,2].map(k=>Math.abs(images[0].pixels[i+k]-images[1].pixels[i+k])))<2)continue;
     const x=clip.x+((i/4)%images[0].width+.5)/scale,y=clip.y+(Math.floor(i/4/images[0].width)+.5)/scale;
     if(y>r.y+r.height*.4&&y<r.y+r.height*.6){if(x<r.x)sides.left++;if(x>=r.x+r.width)sides.right++;}
     if(x>r.x+r.width*.4&&x<r.x+r.width*.6){if(y<r.y)sides.top++;if(y>=r.y+r.height)sides.bottom++;}
    }
    return sides;
   },{glow:glow.toString('base64'),plain:plain.toString('base64'),r,clip});
   assert(Object.values(sides).every(n=>n>0),selector+': glow must spread on all four sides '+JSON.stringify(sides));
  }
  for(const selector of ['.row.current .rowtitle','#title'])await assertTextHalo(page,selector,size==='long');
  await page.waitForTimeout(250);
  fs.writeFileSync('/tmp/portal-static-before.png',before);
  const after=await page.screenshot({path:'/tmp/portal-static-after.png'});
  assert(before.equals(after),'Settled compositing must preserve all footer pixels');
  await page.screenshot({path:'/tmp/portal-soft-glow-'+width+'-'+size+'.png'});
  await page.locator('#stream').click();await page.waitForFunction(()=>document.querySelector('#stream-list .row.current'));
  const active=await page.locator('nav .selected').evaluateAll(es=>es.filter(e=>e.getBoundingClientRect().width).map(e=>({weight:getComputedStyle(e).fontWeight,shadow:getComputedStyle(e).textShadow})));
  assert(active.every(s=>s.weight==='600'&&s.shadow!=='none'));
  await assertListTypography(page);
  for(const selector of ['#stream-list .row.current .rowtitle'])await assertTextHalo(page,selector,size==='long');
  assert(!requests.some(p=>p.includes('music-glow')),'No audio-feature polling or animation assets');
  assert.deepEqual(errors,[]);
  console.log('PASS '+width+'px '+size+': static pixels, bold top tabs, stable regular list text, unlit gray artist, four-sided halo, no audio polling, Local/Stream');
  await page.close();
 }}}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
