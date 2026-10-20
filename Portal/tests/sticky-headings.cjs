// Mock-only list headers: real account and playback are never accessed.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.join(__dirname,'../web');
const songs=Array.from({length:100},(_,i)=>({id:String(i).padStart(11,'0'),kind:'track',title:`Song ${i}`,artist:'Artist',album:'Album',subtitle:'Artist'}));
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true});
 try{
  for(const width of [320,390,768]){
   const page=await browser.newPage({viewport:{width,height:844},isMobile:true,hasTouch:true,reducedMotion:"reduce"});const errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('http://portal.test/**',route=>{
    const u=new URL(route.request().url());
    if(u.pathname==='/api/library')return route.fulfill({json:songs});
    if(u.pathname.endsWith('/status'))return route.fulfill({json:{status:'stopped',track_id:null,title:'',artist:'',position:0,duration:0,repeat:'one'}});
    if(u.pathname==='/api/stream/browse'){
     const view=u.searchParams.get('view');
     const items=view==='playlists'?[{kind:'playlist',id:'PLtest',title:'Very long playlist title '.repeat(8),subtitle:''}]:songs;
     return route.fulfill({json:{account:'Example',items,next_cursor:view==='liked'?'next':null}});
    }
    const file=u.pathname==='/'?'index.html':u.pathname.slice(1);assert(['index.html','app.js','style.css'].includes(file));
    return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
   });
   const idle=()=>page.waitForFunction(()=>!document.querySelector('#stream-refresh').disabled);
   async function sticky(selector){
    const before=await page.locator(selector).boundingBox();
    const edge=await page.locator('section:not([hidden]) .list-scroll').boundingBox();
    const clip={x:0,y:0,width,height:Math.floor(edge.y)};
    const topBefore=await page.screenshot({clip});
    await page.evaluate(()=>document.querySelector('section:not([hidden]) .list-scroll').scrollTo(0,1000));
    await page.waitForTimeout(60);
    const after=await page.locator(selector).boundingBox();
    const topAfter=await page.screenshot({clip});
    // Compositing can shift an antialiased edge by one gray level. No visible glow may leak.
    const pixelDiff=await page.evaluate(async encoded=>{
     const pixels=await Promise.all(encoded.map(async data=>{
      const image=new Image();image.src=`data:image/png;base64,${data}`;await image.decode();
      const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
      const context=canvas.getContext('2d');context.drawImage(image,0,0);return context.getImageData(0,0,image.width,image.height).data;
     }));
     let max=0,changed=0;
     for(let i=0;i<pixels[0].length;i+=4){let d=0;for(let c=0;c<3;c++)d=Math.max(d,Math.abs(pixels[0][i+c]-pixels[1][i+c]));max=Math.max(max,d);if(d)changed++;}
     return {max,changed};
    },[topBefore.toString('base64'),topAfter.toString('base64')]);
    assert(pixelDiff.max<=1&&pixelDiff.changed<=4,`Top region changed while scrolling ${selector}: ${JSON.stringify(pixelDiff)}`);
    assert.equal(after.y,before.y);assert.equal(await page.evaluate(()=>scrollY),0);
    const tabs=await page.locator('.stream-tabs').boundingBox();
    if(selector==='#stream-toolbar')assert.equal(after.y,tabs.y+tabs.height);
   }
   async function streamHeader(count,search=false){
    assert.equal(await page.locator('#stream-count').textContent(),count);
    assert(await page.locator('#stream-message').isHidden());
    if(!search){
    const g=await page.evaluate(search=>{
     const r=s=>document.querySelector(s).getBoundingClientRect();
     const heading=r(search?'#stream-search-form':'#stream-heading-row'),count=r('#stream-count'),refresh=r('#stream-refresh');
     const title=r(search?'#stream-search':'#stream-heading');
     return {height:heading.height,right:heading.right-refresh.right,ordered:title.right<=count.left&&count.right<=refresh.left,
      center:Math.abs(count.y+count.height/2-refresh.y-refresh.height/2),color:getComputedStyle(document.querySelector('#stream-count')).color,
      localColor:getComputedStyle(document.querySelector('#subtitle')).color,overflow:document.documentElement.scrollWidth>innerWidth};
    },search);
    assert(g.height===(search?32:44));assert(Math.abs(g.right-(search?11:0))<1);assert(g.ordered&&g.center<1&&!g.overflow);assert.equal(g.color,g.localColor);
    }else{
     assert(await page.locator('#stream-count').isHidden());
     assert(await page.locator('#stream-refresh').isHidden());
     assert.equal(await page.locator('#stream-search-form').evaluate(e=>e.children.length),2);
    }
    if(search){
     const matching=await page.evaluate(()=>{
      const input=document.querySelector('#stream-search'),box=input.closest('.search'),tabs=document.querySelector('.stream-tabs');
      return {height:box.getBoundingClientRect().height,tabHeight:tabs.getBoundingClientRect().height,
       font:getComputedStyle(input).fontSize,tabFont:getComputedStyle(tabs.querySelector('button')).fontSize};
     });
     assert.equal(matching.height,matching.tabHeight);assert.equal(matching.font,'16px');assert.equal(matching.tabFont,'11px');
    }
    await sticky('#stream-toolbar');
    if(!search) await plainHeader('#stream-heading-row');
   }
   async function plainHeader(selector){
    const c=await page.locator(selector).evaluate(e=>{
     const s=getComputedStyle(e);
     return {radius:parseFloat(s.borderRadius),border:s.borderTopWidth,background:s.backgroundColor};
    });
    assert.equal(c.radius,0);assert.equal(c.border,'0px');assert.equal(c.background,'rgb(0, 0, 0)');
   }
   async function glowScreenshot(bar,list,name){
    // Put a selected track just beneath the sticky edge; inspect its glow at rounded corners.
    await page.evaluate(({bar,list})=>{
     const bounds=document.querySelector(bar).getBoundingClientRect();
     const row=[...document.querySelectorAll(`${list} .row`)].find(e=>{
      const r=e.getBoundingClientRect();return r.top<=bounds.bottom+36 && r.bottom>bounds.bottom;
     });
     if(row)row.classList.add('current');
    },{bar,list});
    await page.screenshot({path:`/tmp/portal-clipped-${name}-${width}.png`});
   }
   await page.goto('http://portal.test/');await page.waitForFunction(()=>document.querySelector('#subtitle').textContent==='100 tracks');
   await page.locator('#search').fill('Song');await page.locator('#search').press('Enter');assert(await page.locator('.heading').isHidden());
   await page.locator('#search').fill('');await page.locator('#search').press('Enter');await page.locator('#list .row').click();await sticky('.heading');await page.locator('#list .row').click();
   await sticky('.heading');await plainHeader('#local-heading');assert(await page.locator('#back').isVisible());
   await glowScreenshot('#local-heading','#list','local');
   await page.locator('#back').click();assert.equal(await page.locator('#heading').textContent(),'Artist');
   await page.locator('#stream').click();await idle();await streamHeader('100 tracks');
   await page.locator('[data-view=liked]').click();await idle();await streamHeader('100+ tracks');
   await page.locator('#stream-refresh').click();await idle();assert.equal(await page.evaluate(()=>document.querySelector('#stream-scroll').scrollTop),0);
   await page.locator('[data-view=playlists]').click();await idle();assert.equal(await page.locator('#stream-count').textContent(),'1 playlist');
   await page.locator('#stream-list .row').click();await idle();await streamHeader('100 tracks');
   assert(await page.locator('#stream-heading').evaluate(e=>e.scrollWidth>e.clientWidth));
   await glowScreenshot('#stream-heading-row','#stream-list','stream');
   await page.screenshot({path:`/tmp/portal-heading-${width}.png`});
   await page.locator('#stream-back').click();assert.equal(await page.locator('#stream-count').textContent(),'1 playlist');
   await page.locator('[data-view=search]').click();await page.locator('#stream-search').fill('song');await page.locator('#stream-search').press('Enter');await idle();
   await streamHeader('100 tracks',true);await page.screenshot({path:`/tmp/portal-search-count-${width}.png`});
   assert.deepEqual(errors,[]);await page.close();
   console.log(`PASS ${width}px: Local/Stream sticky headers, right-aligned counts before Refresh, long titles, pagination, nested Back and compact Search`);
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
