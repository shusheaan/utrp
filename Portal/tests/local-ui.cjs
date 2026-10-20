// Isolated Local navigation/layout checks; never starts real playback.
const {chromium}=require('playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
const artist='Artist Needle with a very long artist name for testing narrow screens';
const album='Album Needle with a very long album name for testing narrow screens';
const tracks=[{id:'one',title:'Song Needle',artist,album},{id:'two',title:'Second',artist,album:'Other album'},{id:'three',title:'Third',artist:'Other artist',album:'Another'}];
async function header(page,title,count) {
 assert.equal(await page.locator('#heading').textContent(),title);
 assert.equal(await page.locator('#subtitle').textContent(),`${count} ${count === 1 ? 'track' : 'tracks'}`);
 if(title==='Local music'){
  assert(await page.locator('#local-heading').isHidden());
  assert(await page.locator('#local-search').isVisible());
  const top=await page.evaluate(()=>({search:document.querySelector('#local-search').getBoundingClientRect().top,main:document.querySelector('main').getBoundingClientRect().top,padding:parseFloat(getComputedStyle(document.querySelector('main')).paddingTop)}));
  assert(Math.abs(top.search-top.main-top.padding)<1);return;
 }
 assert(await page.locator('#local-heading').isVisible());
 const d=await page.evaluate(()=>{
  const r=s=>document.querySelector(s).getBoundingClientRect();
  return {height:r('.heading').height,right:r('.heading').right-r('#subtitle').right,
   overlap:r('#heading').right>r('#subtitle').left,center:Math.abs((r('#heading').top+r('#heading').bottom)/2-(r('#subtitle').top+r('#subtitle').bottom)/2),
   weight:getComputedStyle(document.querySelector('#heading')).fontWeight,font:getComputedStyle(document.querySelector('#heading')).fontSize,overflow:document.documentElement.scrollWidth>innerWidth};
 });
 assert(d.height===44 && Math.abs(d.right)<1 && !d.overlap && d.center<1 && !d.overflow);
 assert.equal(d.font,'13px');assert(Number(d.weight)>=600);
}
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',headless:true});
 try {
  for(const width of [320,390,768]) {
   const page=await browser.newPage({viewport:{width,height:844},isMobile:true,hasTouch:true});const errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('http://portal.test/**',route=>{
    const url=new URL(route.request().url());assert.equal(route.request().method(),'GET');
    if(url.pathname==='/api/library')return route.fulfill({json:tracks});
    if(url.pathname==='/api/stream/browse')return route.fulfill({json:{items:[],next_cursor:null}});
    if(url.pathname.endsWith('/status'))return route.fulfill({json:{status:'stopped',title:'',artist:'',track_id:null,position:0,duration:0,repeat:'one'}});
    const file=url.pathname==='/'?'index.html':url.pathname.slice(1);assert(['index.html','app.js','style.css'].includes(file));
    return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
   });
   await page.goto('http://portal.test/');await page.waitForFunction(()=>document.querySelector('#subtitle').textContent==='3 tracks');
   await header(page,'Local music',3);assert(await page.locator('#local-search').isVisible());
   const pill=async(selector,text)=>page.locator(selector).evaluate((e,text)=>{
    const r=e.getBoundingClientRect(),s=getComputedStyle(e),t=getComputedStyle(document.querySelector(text));
    return {x:r.x,y:r.y,width:r.width,height:r.height,radius:s.borderRadius,border:s.borderColor,font:t.fontSize,family:t.fontFamily,weight:t.fontWeight};
   },text);
   const searchPill=await pill('#local-search','#search');
   assert.equal(searchPill.font,'16px');
   const viewport=await page.locator('meta[name=viewport]').getAttribute('content');
   assert(!/user-scalable\s*=\s*(no|0)|maximum-scale|minimum-scale/i.test(viewport),'Do not restrict user zoom');
   await page.locator('#search').focus();assert.deepEqual(await pill('#local-search','#search'),searchPill);
   await page.locator('#stream').click();
   assert.deepEqual(await pill('.stream-tabs','.stream-tabs button'),{...searchPill,font:'11px'});
   await page.locator('[data-view=search]').click();
   const streamSearchPill=await pill('#stream-search-form','#stream-search');
   assert.deepEqual({...streamSearchPill,y:searchPill.y},searchPill);
   assert.equal(await page.locator('#local-search span, #stream-submit').count(),0);
   for(const selector of ['#search','#stream-search'])assert.equal(await page.locator(selector).getAttribute('placeholder'),' ');
   assert.equal(await page.locator('#stream-search-form').evaluate(e=>e.children.length),2);
   assert(await page.locator('#stream-refresh').isHidden());
   const hints=[];
   for(const [source,form,input] of [['stream','#stream-search-form','#stream-search'],['local','#local-search','#search']]){
    await page.locator(`#${source}`).click();await page.locator(input).blur();
    const hint=page.locator(`${form} .search-hint`);assert(await hint.isVisible());
    const geometry=await hint.evaluate(e=>{const r=e.getBoundingClientRect(),p=e.parentElement.getBoundingClientRect(),s=getComputedStyle(e);return {w:r.width,h:r.height,x:r.x-p.x,center:r.y+r.height/2-p.y-p.height/2,color:s.color,markup:e.innerHTML};});
    assert.equal(geometry.w,14);assert.equal(geometry.h,14);assert(Math.abs(geometry.center)<.1);hints.push(geometry);
    // Tapping the icon's area focuses the underlying input, not a new submit button.
    const rect=await hint.boundingBox();await page.mouse.click(rect.x+7,rect.y+7);
    assert(await page.locator(input).evaluate(e=>e===document.activeElement));assert(await hint.isHidden());
    await page.locator(input).fill('sample');await page.locator(input).blur();assert(await hint.isHidden());
    await page.locator(input).fill('');await page.locator(input).blur();assert(await hint.isVisible());
   }
   assert.deepEqual(hints[0],hints[1]);
   await page.locator('#stream').click();

   await page.screenshot({path:`/tmp/portal-matched-stream-${width}.png`});
   await page.locator('#local').click();assert.deepEqual(await pill('#local-search','#search'),searchPill);
   await page.screenshot({path:`/tmp/portal-matched-local-${width}.png`});
   for(const [query,count] of [['Song Needle',1],['Album Needle',1],['Artist Needle',2]]) {
    const before=await page.locator('#list').innerText();await page.locator('#search').fill(query);assert.equal(await page.locator('#list').innerText(),before);await page.locator('#search').press('Enter');assert.equal(await page.locator('#list .row').count(),count);
   }
   await page.locator('#search').fill('');await page.locator('#search').press('Enter');
   await page.locator('#list .row').filter({hasText:artist}).click();
   await header(page,artist,2);assert(await page.locator('#local-search').isHidden());
   assert(await page.locator('#list .group-row .rowtitle').first().evaluate(e=>Number(getComputedStyle(e).fontWeight)>=600));
   await page.locator('#list .row').filter({hasText:album}).click();
   await header(page,album,1);assert(await page.locator('#local-search').isHidden());
   assert.equal(await page.locator('#list .row').count(),1);
   assert(await page.locator('#play').evaluate(e=>{
    const r=e.getBoundingClientRect();return r.width===36 && r.height===36 && getComputedStyle(e).borderRadius==='50%';
   }));
   await page.screenshot({path:`/tmp/portal-local-album-${width}.png`});
   await page.locator('#back').click();await header(page,artist,2);assert(await page.locator('#local-search').isHidden());
   await page.locator('#back').click();await header(page,'Local music',3);assert(await page.locator('#local-search').isVisible());
   assert.equal(await page.locator('#search').inputValue(),'');assert(await page.locator('#back').isHidden());
   await page.screenshot({path:`/tmp/portal-local-overview-${width}.png`});assert.deepEqual(errors,[]);
   console.log(`PASS ${width}px: compact header, three-level navigation, global search, circular player`);await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
