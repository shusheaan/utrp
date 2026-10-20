// Isolated UI regression test: no real cookies, services, or playback.
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.join(__dirname, '../web');
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium', headless:true});
  try {
   for (const playlistId of [null,'LM','VLLM','PLtest']) {
    const page = await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    const requests = [], views = [], errors = [], commands = [];
    let failNext = true;
    page.on('pageerror', error => errors.push(error.message));
    const status = {status:'stopped',title:'',artist:'',track_id:null,position:0,duration:0,repeat:'one'};
    const items = start => Array.from({length:Math.min(100,250-start)}, (_,i) => ({kind:'track',id:String(start+i).padStart(11,'0'),title:`Song ${start+i}`,subtitle:'Artist',section:''}));
    await page.route('http://portal.test/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/api/library') return route.fulfill({json:[]});
      if (url.pathname.endsWith('/status')) return route.fulfill({json:status});
      if (url.pathname === '/api/stream/control') {
        commands.push(route.request().postDataJSON()); return route.fulfill({json:status});
      }
      if (url.pathname === '/api/stream/browse') {
        const view = url.searchParams.get('view'); views.push(view);
        if (view === 'recommended') return route.fulfill({json:{account:'Test',items:items(0).slice(0,5),next_cursor:null}});
        if(view==='playlists')return route.fulfill({json:{items:[{kind:'playlist',id:playlistId,title:'Test playlist',subtitle:''}],next_cursor:null}});
        assert.equal(view, playlistId ? 'playlist' : 'liked');
        if(playlistId)assert.equal(url.searchParams.get('id'),playlistId);
        const start = Number(url.searchParams.get('cursor') || 0);
        requests.push(start);
        await wait(150);
        if (start === 200 && failNext) {
          failNext = false;
          return route.fulfill({status:502,json:{error:'Temporary failure. Retry loading more.'}});
        }
        return route.fulfill({json:{account:'Test',items:items(start),next_cursor:start+100<250 ? String(start+100) : null}});
      }
      const file = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
      assert(['index.html','app.js','style.css'].includes(file));
      return route.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
    });
    await page.goto('http://portal.test/');
    await page.locator('#stream').click();
    await page.waitForFunction(() => document.querySelectorAll('#stream-list .row').length === 5);
    assert.deepEqual(views,['recommended']); assert.deepEqual(requests,[]);
    assert.equal(await page.locator('.stream-tabs .selected').getAttribute('data-view'),'recommended');
    assert(await page.locator('#stream-more').isHidden());
    if(playlistId){
      await page.locator('[data-view="playlists"]').click();
      await page.locator('#stream-list .row').filter({hasText:'Test playlist'}).click();
    }else await page.locator('[data-view="liked"]').click();
    const count = count => page.waitForFunction(n => document.querySelectorAll('#stream-list .row').length === n, count);
    await count(100); await wait(350); assert.deepEqual(requests,[0]);
    await page.evaluate(() => { window.firstRow = document.querySelector('#stream-list .row'); });
    await page.locator('#stream-more').scrollIntoViewIfNeeded();
    const scrollBefore = await page.evaluate(() => document.querySelector('#stream-scroll').scrollTop);
    // Repeated bottom events while in flight must not duplicate the fetch.
    await page.evaluate(() => { dispatchEvent(new Event('scroll')); dispatchEvent(new Event('scroll')); });
    await count(200); await wait(350); assert.deepEqual(requests,[0,100]);
    assert(await page.evaluate(() => window.firstRow === document.querySelector('#stream-list .row')));
    assert(Math.abs(await page.evaluate(() => document.querySelector('#stream-scroll').scrollTop) - scrollBefore) < 2);
    await page.locator('#stream-list .row').nth(101).click();
    await page.waitForFunction(() => !document.body.classList.contains('busy'));
    assert.equal(commands[0].action,'play');
    assert.equal(commands[0].ids[commands[0].index],String(101).padStart(11,'0'));
    await page.locator('#stream-more').scrollIntoViewIfNeeded();
    await page.waitForFunction(() => document.querySelector('#stream-more').textContent === 'Retry loading more');
    await wait(600); assert.deepEqual(requests,[0,100,200]);
    assert.equal(await page.locator('#stream-list .row').count(),200);
    await page.locator('#stream-more').click(); await count(250);
    assert(await page.locator('#stream-more').isHidden());
    await page.evaluate(() => document.querySelector('#stream-scroll').scrollTo(0,100000));
    await wait(350); assert.deepEqual(requests,[0,100,200,200]);
    assert.equal(await page.locator('#stream-list .row').evaluateAll(rows=>new Set(rows.map(r=>r.dataset.track)).size),250);
    await page.locator('#stream-refresh').click(); await count(100); await wait(350);
    assert.deepEqual(requests,[0,100,200,200,0]);
    assert.equal(await page.evaluate(() => document.querySelector('#stream-scroll').scrollTop),0);
    await page.locator('[data-view="search"]').click();
    assert(await page.locator('#stream-more').isHidden());
    await wait(350); assert.deepEqual(requests,[0,100,200,200,0]);
    assert.deepEqual(errors,[]);
    await page.close();
    console.log(`${playlistId || 'Liked tab'}: PASS 100 → 200 → retry → 250, no eager fetching/duplicates, stable DOM/scroll, loaded-track playback, exhaustion, refresh and Search`);
   }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
