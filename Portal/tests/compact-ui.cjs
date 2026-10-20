const {chromium}=require('playwright');
const fs=require('fs');const assert=require('node:assert/strict');
const root=require('node:path').join(__dirname,'../web');
const longTitle='A very long song title that should stay on one line even on the smallest phone screen and remain truncated on a wide tablet screen too';
const artist='An artist with an exceptionally long name';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',headless:true});
 for(const width of [320,390,768]) {
  const page=await browser.newPage({viewport:{width,height:844},isMobile:true,hasTouch:true});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const commands=[];let current={status:'playing',title:longTitle,artist,album:'Album should not appear',track_id:'track0',position:30,duration:240,repeat:'one'};
  const tracks=Array.from({length:40},(_,i)=>({id:'track'+i,title:longTitle+' '+i,artist,album:'Album'}));
  await page.route('http://portal.test/**',async route=>{
   const path=new URL(route.request().url()).pathname;
   if(path==='/api/library')return route.fulfill({json:tracks});
   if(path==='/api/status')return route.fulfill({json:current});
   if(path==='/api/stream/status')return route.fulfill({json:{...current,status:'stopped'}});
   if(path==='/api/control'){
    const command=route.request().postDataJSON();commands.push(command);
    if(command.action==='repeat')current.repeat={one:'all',all:'off',off:'one'}[current.repeat];
    if(command.action==='toggle')current.status=current.status==='playing'?'paused':'playing';
    return route.fulfill({json:current});
   }
   if(path==='/api/stream/browse')return route.fulfill({json:{account:'Test account',items:tracks.map(t=>({id:t.id,kind:'track',title:t.title,subtitle:t.artist,section:''}))}});
   const file=path==='/'?'index.html':path.slice(1);
   assert(['index.html','app.js','style.css'].includes(file));
   return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(root+'/'+file)});
  });
  await page.goto('http://portal.test/');await page.waitForFunction(()=>document.querySelector('#title').textContent.startsWith('A very long'));
  await page.locator('#search').fill('long');await page.locator('#search').press('Enter');
  const dimensions=await page.evaluate(()=>{
   const rect=s=>document.querySelector(s).getBoundingClientRect();
   return {header:rect('header').height,footer:rect('footer').height,row:rect('.row').height,overflow:document.documentElement.scrollWidth>innerWidth,artist:rect('#artist').width,now:rect('.now').width,meta:rect('.rowmeta').width,rowtext:rect('.rowtext').width,playCenter:rect('#play').x+rect('#play').width/2, viewport:innerWidth,titleTruncated:document.querySelector('#title').scrollWidth>rect('#title').width,rowTruncated:document.querySelector('.rowtitle').scrollWidth>rect('.rowtitle').width};
  });
  assert.equal(dimensions.footer,125);assert(dimensions.header===52);assert(dimensions.row<=36);assert(!dimensions.overflow);
  assert(dimensions.artist<=dimensions.now/4+1);assert(dimensions.meta<=dimensions.rowtext/4+1);
  assert(Math.abs(dimensions.playCenter-width/2)<1);assert(dimensions.titleTruncated && dimensions.rowTruncated);
  assert.equal(await page.locator('.art,.badge,.source,.brand,#connection,.chevron').count(),0);
  const aligned=await page.evaluate(()=>{
   const rect=s=>document.querySelector(s).getBoundingClientRect();
   const style=s=>getComputedStyle(document.querySelector(s));
   return {title:rect('#title').width,now:rect('.now').width,rowTitle:rect('.rowtitle').width,rowText:rect('.rowtext').width,
    artistRight:rect('.now').right-rect('#artist').right,metaRight:rect('.rowtext').right-rect('.rowmeta').right,
    titleGap:rect('#artist').left-rect('#title').right,rowGap:rect('.rowmeta').left-rect('.rowtitle').right,
    titleColor:style('#title').color,rowColor:style('.rowtitle').color,artistWeight:style('.rowmeta').fontWeight,
    rowRadius:parseFloat(style('.row').borderRadius),searchRadius:parseFloat(style('.search').borderRadius),
    backBorder:style('#back').borderWidth,backBackground:style('#back').backgroundColor,
    streamBackBorder:style('#stream-back').borderWidth,streamBackBackground:style('#stream-back').backgroundColor};
  });
  assert(aligned.title<=aligned.now*.75+1);assert(aligned.rowTitle<=aligned.rowText*.75+1);
  assert(Math.abs(aligned.artistRight)<1 && Math.abs(aligned.metaRight)<1);
  assert(aligned.titleGap>=11 && aligned.rowGap>=11);
  assert.equal(aligned.titleColor,'rgb(255, 255, 255)');assert.equal(aligned.rowColor,'rgb(255, 255, 255)');
  assert(Number(aligned.artistWeight)>=600);assert(aligned.rowRadius>=18 && aligned.searchRadius>=18);
  assert.equal(aligned.backBorder,'0px');assert.equal(aligned.streamBackBorder,'0px');
  assert.equal(aligned.backBackground,'rgba(0, 0, 0, 0)');assert.equal(aligned.streamBackBackground,'rgba(0, 0, 0, 0)');
  assert.equal(await page.locator('.separator,#title-dot').count(),0);
  // A short name must still sit flush right, rather than follow the title.
  assert(await page.locator('.rowmeta').first().evaluate(e=>{
    const original=e.textContent;e.textContent='A';
    const aligned=Math.abs(e.getBoundingClientRect().right-e.parentElement.getBoundingClientRect().right)<1;
    e.textContent=original;return aligned;
  }));
  for(const [label,action] of [['Previous track','previous'],['Back five seconds','backward'],['Forward five seconds','forward'],['Next track','next']]){
   await page.getByRole('button',{name:label,exact:true}).click();await page.waitForFunction(()=>!document.body.classList.contains('busy'));assert.equal(commands.at(-1).action,action);
  }
  for(const [label,icon,nextLabel] of [['Repeat one','A','Repeat all'],['Repeat all','off','Repeat off'],['Repeat off','1','Repeat one']]){
   await page.getByRole('button',{name:label,exact:true}).click();await page.waitForFunction(()=>!document.body.classList.contains('busy'));
   assert.equal(await page.locator('#repeat-mode').textContent(),icon);assert.equal(await page.locator('#repeat').getAttribute('aria-label'),nextLabel);
  }
  await page.getByRole('button',{name:'Pause',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#play').getAttribute('aria-label')==='Play');
  await page.locator('#stream').click();await page.waitForFunction(()=>document.querySelectorAll('#stream-list .row').length===40);
  assert.equal(await page.locator('#stream-list .row').first().locator('svg,img').count(),0);
  assert.equal(await page.locator('.stream-tabs .selected').getAttribute('data-view'),'recommended');
  assert.equal(await page.locator('#stream-heading').textContent(),'Recommended');
  const tabs=await page.locator('.stream-tabs button').evaluateAll(buttons=>buttons.map(b=>({label:b.textContent,top:b.getBoundingClientRect().top,bottom:b.getBoundingClientRect().bottom,width:b.clientWidth,scroll:b.scrollWidth})));
  assert.deepEqual(tabs.map(t=>t.label),['Recommended','Liked','Playlists','Search']);
  assert(tabs.every(t=>Math.abs(t.top-tabs[0].top)<1 && Math.abs(t.bottom-tabs[0].bottom)<1 && t.scroll<=t.width));
  const theme=await page.evaluate(()=>({backgrounds:['html','body','header','footer','.source-tabs','.stream-tabs','.search'].map(s=>getComputedStyle(document.querySelector(s)).backgroundColor),gap:getComputedStyle(document.querySelector('.stream-tabs')).gap,theme:document.querySelector('meta[name="theme-color"]').content}));
  assert(theme.backgrounds.every(c=>c==='rgb(0, 0, 0)'));assert.equal(theme.gap,'3px');assert.equal(theme.theme,'#000000');
  const capsules=await page.evaluate(()=>['.source-tabs','.stream-tabs'].map(selector=>{
   const nav=document.querySelector(selector),css=getComputedStyle(nav),r=nav.getBoundingClientRect();
   return {border:css.border,padding:css.padding,radius:css.borderRadius,gap:css.gap,height:r.height,
    children:[...nav.children].map(b=>{const c=getComputedStyle(b),box=b.getBoundingClientRect();return {border:c.borderWidth,radius:c.borderRadius,height:box.height,inside:box.left>=r.left&&box.right<=r.right};})};
  }));
  for(const key of ['border','padding','radius','gap','height'])assert.equal(capsules[0][key],capsules[1][key]);
  assert.equal(capsules[1].children.length,4);
  assert(capsules[1].children.every(b=>b.border==='0px'&&b.radius==='999px'&&b.height===26&&b.inside));
  await page.screenshot({path:`/tmp/portal-compact-${width}.png`});
  await page.locator('#stream-list .row').last().scrollIntoViewIfNeeded();
  assert(await page.locator('#stream-list .row').last().evaluate(e=>e.getBoundingClientRect().bottom<=document.querySelector('footer').getBoundingClientRect().top+1));
  assert.deepEqual(errors,[]);console.log(JSON.stringify({width,...dimensions,controls:'passed',errors}));await page.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
