'use strict';
const $ = id => document.getElementById(id);
const state = { tracks: [], localQuery: '', artist: null, album: null, current: null, busy: false, seeking: false, scroll: new Map(), tab: 'local', source: localStorage.getItem('portal-source') === 'stream' ? 'stream' : 'local', streamView: 'recommended', streamPage: null, streamRequest: {view:'recommended'}, streamBusy: false, streamLoaded: false, streamMoreBusy: false, streamMoreFailed: false, streamGeneration: 0, streamSearchKind: 'track', streamHistory: [], rating: null, likeWriting: false, likedRevision: 0, likedDirty: false };
const scroller = () => $(`${state.tab}-scroll`);
const time = seconds => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
const key = () => JSON.stringify([state.artist, state.album, state.localQuery]);

function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }

async function api(path, body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  try {
    const response = await fetch(path, { method: body ? 'POST' : 'GET', cache: 'no-store', signal: controller.signal,
      headers: body ? { 'Content-Type': 'application/json', 'X-Portal-Request': '1' } : {}, body: body ? JSON.stringify(body) : undefined });
    const result = await response.json();
    if (!response.ok) {
      const error = new Error(result.error || `Request failed (${response.status})`);
      error.status = response.status; throw error;
    }
    return result;
  } finally { clearTimeout(timeout); }
}

function row(title, subtitle, onClick, trackId) {
  const button = document.createElement('button'); button.className = 'row';
  const text = document.createElement('span'); text.className = 'rowtext';
  const name = document.createElement('span'); name.className = 'rowtitle'; name.textContent = title;
  text.append(name);
  if (subtitle) {
    const meta = document.createElement('span'); meta.className = 'rowmeta'; meta.textContent = subtitle;
    text.append(meta);
  }
  button.title = [title, subtitle].filter(Boolean).join(' · ');
  button.append(text); button.addEventListener('click', onClick);
  if (trackId) { button.dataset.track = trackId; button.classList.toggle('current', trackId === state.current); }
  return button;
}

function navigate(artist, album) {
  state.scroll.set(key(), scroller().scrollTop);
  state.artist = artist; state.album = album; state.localQuery = ''; $('search').value = '';
  render(); scroller().scrollTo(0, state.scroll.get(key()) || 0);
}

function render() {
  const query = state.localQuery.toLocaleLowerCase();
  const scope = state.tracks.filter(t => (!state.artist || t.artist === state.artist) && (!state.album || t.album === state.album));
  $('heading').textContent = state.album || state.artist || 'Local music';
  $('back').hidden = !state.artist;
  $('local-heading').hidden = !state.artist;
  $('local-search').hidden = Boolean(state.artist);
  $('subtitle').textContent = `${scope.length} ${scope.length === 1 ? 'track' : 'tracks'}`;
  const fragment = document.createDocumentFragment();
  if (query || state.album) {
    for (const track of scope.filter(t => `${t.artist} ${t.album} ${t.title}`.toLocaleLowerCase().includes(query))) {
      fragment.append(row(track.title, track.artist, () => control({ action: 'play', id: track.id }, 'local'), track.id));
    }
  } else {
    const groups = new Map();
    for (const track of scope) {
      const group = state.artist ? track.album : track.artist;
      groups.set(group, (groups.get(group) || 0) + 1);
    }
    for (const [name, count] of [...groups].sort(([a], [b]) => a.localeCompare(b))) {
      const group = row(name, `${count} ${count === 1 ? 'track' : 'tracks'}`,  () => state.artist ? navigate(state.artist, name) : navigate(name, null));
      group.classList.add('group-row'); fragment.append(group);
    }
  }
  $('empty').hidden = fragment.childElementCount > 0; $('list').replaceChildren(fragment);
}

function paintSeek() {
  const seek = $('seek');
  const duration = Number(seek.max);
  const progress = duration > 0 ? Math.min(100, Math.max(0, Number(seek.value) / duration * 100)) : 0;
  seek.style.setProperty('--progress', `${progress}%`);
}

function update(status) {
  // Partial loading responses must not erase labels for the same song/source.
  const previous = state.displayStatus;
  if (status.track_id && previous?.source === state.source && previous.track_id === status.track_id) {
    status = {...status, title:status.title || previous.title, artist:status.artist || previous.artist};
  }
  state.displayStatus = {...status, source:state.source};
  syncLike(status);
  state.current = status.track_id;
  $('title').textContent = status.title || 'Choose a track';
  $('artist').textContent = status.artist || '';
  $('artist').hidden = !status.artist;
  $('title').title = status.title || '';
  $('artist').title = status.artist || '';
  $('play-icon').toggleAttribute('hidden', status.status === 'playing');
  $('pause-icon').toggleAttribute('hidden', status.status !== 'playing');
  $('play').setAttribute('aria-label', status.status === 'playing' ? 'Pause' : 'Play');
  $('play').title = $('play').getAttribute('aria-label');
  const repeatLabel = { one: 'Repeat one', all: 'Repeat all', off: 'Repeat off' }[status.repeat];
  $('repeat-mode').textContent = { one: '1', all: 'A', off: 'off' }[status.repeat];
  $('repeat').setAttribute('aria-label', repeatLabel);
  $('repeat').title = repeatLabel;
  const shuffleLabel = status.shuffle ? 'On' : 'Off';
  $('shuffle').setAttribute('aria-pressed', String(Boolean(status.shuffle)));
  $('shuffle').setAttribute('aria-label', `Shuffle ${shuffleLabel.toLowerCase()}`);
  $('shuffle').title = `Shuffle ${shuffleLabel.toLowerCase()}`;
  if (!state.seeking) { $('seek').max = status.duration; $('seek').value = status.position; $('position').textContent = time(status.position); paintSeek(); }
  $('seek').disabled = !status.duration; $('duration').textContent = time(status.duration);
  document.querySelectorAll('[data-track]').forEach(element => element.classList.toggle('current', element.dataset.track === state.current));
  paintEffects(status.effects || {});
  if (status.error) notice(status.error);
}

function paintEffects(effects) {
  const available = Boolean(state.current && Number($('seek').max) > 0);
  const forced = Boolean(effects.forced);
  $('fade').disabled = !available || forced;
  $('fade').setAttribute('aria-pressed', String(Boolean(effects.fade)));
  $('fade').title = forced ? 'Fade on (required for AB)' : effects.fade ? 'Fade on' : 'Fade off';
  $('fade').setAttribute('aria-label', $('fade').title);
  const mode = effects.b != null ? 'AB' : effects.a != null ? 'B' : 'A';
  $('ab-mode').textContent = mode;
  $('ab').disabled = !available;
  $('ab').title = mode === 'AB' ? 'Clear AB loop' : `Set ${mode}`;
  $('ab').setAttribute('aria-label', $('ab').title);
  for (const point of ['a', 'b']) {
    const marker = $(`marker-${point}`), value = effects[point], duration = Number($('seek').max);
    marker.hidden = value == null || !available;
    if (!marker.hidden) {
      const fraction = Math.min(1, Math.max(0, value / duration));
      // Match the native range thumb's centre, including its 7px end inset.
      marker.style.left = `calc(${fraction * 100}% + ${7 - fraction * 14}px)`;
      marker.title = `${point.toUpperCase()} ${time(Math.floor(value))}`;
    }
  }
  if (effects.error) notice(effects.error);
}
async function effect(action) {
  if (state.busy || !state.current) return;
  state.busy = true; document.body.classList.add('busy');
  try {
    const effects = await api('/api/effects', {source:state.source, action, track_id:state.current});
    notice(''); paintEffects(effects);
  } catch (error) { notice(error.name === 'AbortError' ? 'Effects request timed out. Check playback before retrying.' : error.message); }
  finally { state.busy = false; document.body.classList.remove('busy'); }
}
$('fade').addEventListener('click', () => effect('fade'));
$('ab').addEventListener('click', () => effect('ab'));

// Each track owns its async result: late responses never repaint a newer track.
function paintLike(rating) {
  const button = $('like');
  button.hidden = !rating;
  if (!rating) return;
  button.disabled = rating.pending || state.likeWriting;
  if (rating.value === null) button.removeAttribute('aria-pressed');
  else button.setAttribute('aria-pressed', String(rating.value));
  button.title = rating.value === null ? 'Reload rating' : rating.value ? 'Unlike' : 'Like';
  button.setAttribute('aria-label', button.title);
  button.setAttribute('aria-busy', String(rating.pending));
}
function syncLike(status) {
  const id = state.source === 'stream' && /^[\w-]{11}$/.test(status.track_id || '') ? status.track_id : null;
  if (state.rating?.id !== id) state.rating = id ? {id, value:null, pending:false, checked:0} : null;
  const rating = state.rating;
  paintLike(rating);
  if (rating && !rating.pending && !state.likeWriting && Date.now() - rating.checked > 30000) readLike(rating);
}
function validateRating(result, id) {
  if (result.id !== id || typeof result.liked !== 'boolean') throw new Error('Could not confirm the track rating.');
  return result.liked;
}
async function readLike(rating) {
  rating.pending = true; paintLike(rating);
  try {
    const result = await api(`/api/stream/like?${new URLSearchParams({id:rating.id})}`);
    rating.value = validateRating(result, rating.id);
  } catch (error) {
    rating.value = null;
    if (state.rating === rating) notice(error.name === 'AbortError' ? 'Rating request timed out. Tap the heart to retry.' : error.message);
  } finally {
    rating.pending = false; rating.checked = Date.now();
    if (state.rating === rating) paintLike(rating);
  }
}
function invalidateLiked() {
  state.likedRevision += 1;
  state.likedDirty = true;
  if (isLikedRequest(state.streamRequest)) state.streamGeneration += 1;
}
$('like').addEventListener('click', async () => {
  const rating = state.rating;
  if (!rating || rating.pending || state.likeWriting) return;
  if (rating.value === null) { readLike(rating); return; }
  state.likeWriting = true; rating.pending = true; paintLike(rating);
  try {
    const result = await api('/api/stream/like', {id:rating.id, liked:!rating.value});
    rating.value = validateRating(result, rating.id);
    notice('');
  } catch (error) {
    // A timeout may have applied upstream. Do not claim either state without a read.
    rating.value = null;
    notice(error.name === 'AbortError' ? 'Rating request timed out. Tap the heart to reload its state.' : error.message);
  } finally {
    state.likeWriting = false; rating.pending = false; rating.checked = Date.now();
    invalidateLiked(); paintLike(state.rating); updateMore();
  }
});

function endpoint(source) { return source === 'stream' ? '/api/stream' : '/api'; }
function setSource(source) { state.source = source; localStorage.setItem('portal-source', source); }

async function control(command, source = state.source) {
  if (state.busy) return;
  state.busy = true; document.body.classList.add('busy');
  try {
    const status = await api(`${endpoint(source)}/control`, command);
    setSource(source); notice(''); update(status);
  } catch (error) { notice(error.name === 'AbortError' ? 'Request timed out. Check playback before retrying.' : error.message); }
  finally { state.busy = false; document.body.classList.remove('busy'); }
}

async function poll() {
  if (!document.hidden && !state.busy) {
    const source = state.source;
    const results = await Promise.allSettled(['local','stream'].map(s => api(`${endpoint(s)}/status`)));
    if (!state.busy && state.source === source) {
      const playing = results.findIndex(r => r.status === 'fulfilled' && ['playing','loading'].includes(r.value.status));
      if (playing >= 0) setSource(['local','stream'][playing]);
      const result = results[state.source === 'stream' ? 1 : 0];
      if (result.status === 'fulfilled') update(result.value);
      else { notice('Player not connected. Please retry.'); }
    }
  }
  setTimeout(poll, 2000);
}

const isLikedRequest = request => request.view === 'liked' || (request.view === 'playlist' && ['LM','VLLM'].includes(request.id));
const isPagedPlaylist = request => ['liked','playlist'].includes(request.view);
function streamTracks() { return (state.streamPage?.items || []).filter(item => item.kind === 'track'); }
function playStream(id) {
  const tracks = streamTracks();
  const selected = tracks.findIndex(t => t.id === id);
  // Bound the queue around the selection, not by silently omitting the selected song.
  const start = Math.max(0, selected - 100);
  if (selected < 0) return;
  const queue = tracks.slice(start, start + 500);
  const metadata = queue.map(t => ({id:t.id, title:t.title.slice(0, 200), artist:(t.subtitle || '').slice(0, 200), album:''}));
  control({action:'play', ids:queue.map(t=>t.id), metadata, index:selected - start}, 'stream');
}
function streamSnapshot() {
  return {page:state.streamPage, request:state.streamRequest, title:$('stream-heading').textContent,
    scroll:scroller().scrollTop, searchKind:state.streamSearchKind};
}
function syncStream() {
  const searching = state.streamRequest.view === 'search';
  $('stream-search-form').hidden = !searching;
  $('stream-heading-row').hidden = searching;
  $('stream-count').hidden = searching || !state.streamPage;
  if (!state.streamPage) $('stream-count').textContent = '';
  $('stream-categories').hidden = !searching || !state.streamPage;
  $('stream-back').hidden = !state.streamHistory.length;
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('selected',b.dataset.view===state.streamView));
  document.querySelectorAll('[data-kind]').forEach(b=>{
    const selected = b.dataset.kind === state.streamSearchKind;
    b.classList.toggle('selected', selected); b.setAttribute('aria-pressed', String(selected));
  });
}
function renderStream(page, append = false) {
  syncStream();
  const searching = state.streamRequest.view === 'search';
  const visible = items => searching ? items.filter(i=>i.kind===state.streamSearchKind) : items;
  const fragment = document.createDocumentFragment(); let section = '';
  for (const item of visible(page.items)) {
    if (!searching && item.section && item.section !== section) {
      section = item.section; const heading = document.createElement('h3'); heading.textContent = section; fragment.append(heading);
    }
    fragment.append(row(item.title, item.subtitle,
      () => item.kind === 'track' ? playStream(item.id) : loadStream({view:item.kind,id:item.id},item.title,true),
      item.kind === 'track' ? item.id : null));
  }
  if (append) $('stream-list').append(fragment); else $('stream-list').replaceChildren(fragment);
  const items = visible(state.streamPage.items);
  const total = items.length;
  const kinds = new Set(items.map(item => item.kind));
  const kind = searching ? state.streamSearchKind : kinds.size === 1 ? items[0].kind
    : ['liked','album'].includes(state.streamRequest.view) ? 'track' : 'item';
  const noun = ['track','artist','album','playlist'].includes(kind) ? kind : 'item';
  const partial = Boolean(state.streamPage.next_cursor);
  $('stream-count').textContent = `${total}${partial ? '+' : ''} ${noun}${total === 1 && !partial ? '' : 's'}`;
  $('stream-count').title = partial ? 'Loaded so far; more available' : 'Loaded items';
  $('stream-message').textContent = total ? '' : 'No items returned for this view.';
  updateMore();
}
async function loadStream(request, title, push = false, reset = false) {
  if (state.streamBusy || state.streamMoreBusy) return;
  const previous = streamSnapshot();
  const likedRevision = state.likedRevision;
  let retryLiked = false;
  state.streamBusy = true;
  state.streamGeneration += 1; state.streamMoreFailed = false; updateMore();
  $('stream-message').textContent = 'Loading…';
  try {
    const page = await api(`/api/stream/browse?${new URLSearchParams(request)}`);
    if (isLikedRequest(request) && likedRevision !== state.likedRevision) { retryLiked = true; return; }
    if (isLikedRequest(request)) state.likedDirty = false;
    if (reset) state.streamHistory = [];
    if (push && previous.page) state.streamHistory.push(previous);
    if (['recommended','liked','playlists','search'].includes(request.view)) state.streamView = request.view;
    state.streamPage = page; state.streamRequest = request; state.streamLoaded = true;
    $('stream-heading').textContent = title || request.view[0].toUpperCase() + request.view.slice(1);
    renderStream(page);
    scroller().scrollTo(0, 0);
  } catch (error) { $('stream-message').textContent = error.name === 'AbortError' ? 'Request timed out. Please retry.' : error.message; }
  finally {
    state.streamBusy = false;
    if (retryLiked) loadStream(request, title, push, reset);
    else updateMore();
  }
}
function updateMore() {
  if (state.likedDirty && !state.likeWriting && !state.streamBusy && !state.streamMoreBusy && state.tab === 'stream' && isLikedRequest(state.streamRequest)) {
    state.likedDirty = false;
    loadStream(state.streamRequest, $('stream-heading').textContent);
    return;
  }
  document.querySelectorAll('[data-view], [data-kind], #stream-refresh, #stream-search-form button, #stream-back').forEach(b=>b.disabled=state.streamBusy || state.streamMoreBusy);
  const button = $('stream-more');
  button.hidden = state.streamBusy || !state.streamPage?.next_cursor;
  button.disabled = state.streamMoreBusy;
  button.textContent = state.streamMoreBusy ? 'Loading…' : state.streamMoreFailed ? 'Retry loading more' : isPagedPlaylist(state.streamRequest) ? 'Load 100 more' : 'Load more';
}
const streamItemKey = item => JSON.stringify([item.kind, item.id, item.section || '']);
async function continuationPage(cursor, generation) {
  const request = {...state.streamRequest};
  const fetchPage = cursor => api(`/api/stream/browse?${new URLSearchParams({...request, ...(cursor ? {cursor} : {})})}`);
  try { return await fetchPage(cursor); }
  catch (error) { if (error.status !== 409) throw error; }
  // Rebuild only enough of the continuation chain to reach new rows. Keep the
  // displayed snapshot and its DOM/scroll position; never replay a control POST.
  const known = new Set(state.streamPage.items.map(streamItemKey));
  const visited = new Set();
  let next = '', page;
  for (let attempt = 0; attempt < 101; attempt++) {
    if (generation !== state.streamGeneration) return null;
    page = await fetchPage(next);
    if (!page.next_cursor || page.items.some(item => !known.has(streamItemKey(item)))) return page;
    if (visited.has(page.next_cursor)) throw new Error('Pagination did not advance. Retry loading more.');
    visited.add(page.next_cursor); next = page.next_cursor;
  }
  throw new Error('Pagination recovery limit reached. Retry loading more.');
}
async function loadMore() {
  const cursor = state.streamPage?.next_cursor;
  if (state.tab !== 'stream' || !cursor || state.streamBusy || state.streamMoreBusy) return;
  const generation = state.streamGeneration;
  state.streamMoreBusy = true; state.streamMoreFailed = false; updateMore();
  try {
    const page = await continuationPage(cursor, generation);
    if (!page || generation !== state.streamGeneration) return;
    const itemKey = isPagedPlaylist(state.streamRequest) ? item => item.id : streamItemKey;
    const ids = new Set(state.streamPage.items.map(itemKey));
    const items = page.items.filter(item => {
      const key = itemKey(item); if (ids.has(key)) return false; ids.add(key); return true;
    });
    $('stream-message').textContent = '';
    state.streamPage = {...page, items:[...state.streamPage.items, ...items]};
    renderStream({...page, items}, true);
  } catch (error) {
    if (generation === state.streamGeneration) {
      state.streamMoreFailed = true;
      $('stream-message').textContent = error.name === 'AbortError' ? 'Request timed out. Retry loading more.' : error.message;
    }
  } finally { state.streamMoreBusy = false; updateMore(); }
}
$('stream-more').addEventListener('click', loadMore);
// Observe the bottom sentinel, not every scroll event. No automatic retry loop.
new IntersectionObserver(entries => {
  if (entries.some(entry => entry.isIntersecting) && !state.streamMoreFailed) loadMore();
}, {root:$('stream-scroll'), rootMargin:'0px', threshold:0.1}).observe($('stream-more'));
function chooseView(view) {
  if (state.streamBusy || state.streamMoreBusy) return;
  if (view === 'search') {
    state.streamView = view; state.streamRequest = {view}; state.streamHistory = [];
    state.streamGeneration += 1; state.streamPage = null; state.streamMoreFailed = false;
    syncStream(); updateMore(); $('stream-list').replaceChildren();
    $('stream-heading').textContent = 'Search'; $('stream-message').textContent = '';
    return;
  }
  loadStream({view}, undefined, false, true);
}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>chooseView(b.dataset.view)));
document.querySelectorAll('[data-kind]').forEach(b=>b.addEventListener('click',()=>{
  if (state.streamBusy || state.streamMoreBusy || !state.streamPage) return;
  state.streamSearchKind = b.dataset.kind; renderStream(state.streamPage);
}));
$('stream-search-form').addEventListener('submit',e=>{
  e.preventDefault(); const query=$('stream-search').value.trim();
  if(query) loadStream({view:'search',query}, undefined, false, true);
});
$('stream-refresh').addEventListener('click',()=>loadStream(state.streamRequest,$('stream-heading').textContent));
$('stream-back').addEventListener('click',()=>{
  if (state.streamBusy || state.streamMoreBusy) return;
  const previous = state.streamHistory.pop(); if (!previous) return;
  if (isPagedPlaylist(previous.request)) { loadStream(previous.request, previous.title); return; }
  state.streamGeneration += 1; state.streamMoreFailed = false;
  state.streamPage = previous.page; state.streamRequest = previous.request; state.streamSearchKind = previous.searchKind;
  $('stream-heading').textContent = previous.title;
  renderStream(state.streamPage); scroller().scrollTo(0, previous.scroll);
});

document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => control({ action: button.dataset.action })));
$('back').addEventListener('click', () => navigate(state.album ? state.artist : null, null));
$('local-search').addEventListener('submit', e => {
  e.preventDefault(); state.localQuery = $('search').value.trim(); render(); $('local-scroll').scrollTo(0, 0);
});
$('seek').addEventListener('input', () => { state.seeking = true; $('position').textContent = time(Number($('seek').value)); paintSeek(); });
$('seek').addEventListener('change', async () => { await control({ action: 'seek', seconds: Number($('seek').value) }); state.seeking = false; });
for (const tab of ['local', 'stream']) $(tab).addEventListener('click', () => {
  state.tab = tab;
  for (const name of ['local', 'stream']) { $(name).classList.toggle('selected', name === tab); $(name).setAttribute('aria-pressed', String(name === tab)); $(`${name}-page`).hidden = name !== tab; }
  updateMore();
  if (tab === 'stream' && !state.streamLoaded) loadStream({view:state.streamView});
});

async function start() {
  try { state.tracks = await api('/api/library'); render(); }
  catch (error) { notice(error.message); $('subtitle').textContent = 'Library unavailable. Refresh to retry.'; }
  poll();
}
new ResizeObserver(([entry]) => {
  document.documentElement.style.setProperty('--player-height', `${entry.target.getBoundingClientRect().height}px`);
}).observe(document.querySelector('footer'));
new ResizeObserver(([entry]) => {
  document.documentElement.style.setProperty('--header-height', `${entry.target.getBoundingClientRect().height}px`);
}).observe(document.querySelector('header'));
start();
