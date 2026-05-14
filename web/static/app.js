'use strict';

// ── constants ─────────────────────────────────────────────────────────────────
const COMMON_FIELDS = [
  'Description', 'ExecStart', 'ExecReload', 'ExecStop',
  'WorkingDirectory', 'User', 'Group', 'Environment', 'Restart', 'WantedBy',
];
const COMMON_SET = new Set(COMMON_FIELDS);

const FIELD_SECTION = {
  Description: 'Unit',
  ExecStart: 'Service', ExecReload: 'Service', ExecStop: 'Service',
  WorkingDirectory: 'Service', User: 'Service', Group: 'Service',
  Environment: 'Service', Restart: 'Service',
  WantedBy: 'Install',
};

const SUFFIX_SECTION = {
  '.service': 'Service', '.socket': 'Socket', '.timer': 'Timer',
  '.mount': 'Mount', '.automount': 'Automount', '.swap': 'Swap',
  '.path': 'Path', '.slice': 'Slice', '.scope': 'Scope',
};

const ALL_SECTIONS = ['Unit','Service','Socket','Mount','Automount','Swap','Path','Timer','Slice','Install'];

const TYPE_PRIORITY = {
  service:0, socket:1, timer:2, target:3, mount:4,
  automount:5, swap:6, slice:7, path:8, scope:9, device:10,
};
const TYPE_LABELS = {
  service:'Services', socket:'Sockets', timer:'Timers',
  target:'Targets', mount:'Mounts', automount:'Automounts',
  swap:'Swap units', slice:'Slices', path:'Path units',
  scope:'Scopes', device:'Devices',
};

const UNIT_DEP_KEYS = new Set([
  'Requires','Wants','After','Before','Requisite','BindsTo','PartOf','Upholds',
  'Conflicts','OnFailure','OnSuccess','RequiredBy','UpheldBy',
]);

// ── state ─────────────────────────────────────────────────────────────────────
let _services    = [];
let _selected    = null;
let _tab         = 'info';
let _favOnly     = false;
let _classFilter = 'all';
let _dirty       = false;

// ── suggestions cache ─────────────────────────────────────────────────────────
const _sg = {
  directives: [], section_directives: {}, values: {}, section_values: {}, env_keys: [],
  users: [], groups: [], targets: [], units: [], commands: [],
  _dlists: {},
};

function _dl(id, items) {
  if (_sg._dlists[id]) return _sg._dlists[id];
  const dl = document.createElement('datalist');
  dl.id = id;
  items.forEach(v => { const o = document.createElement('option'); o.value = v; dl.appendChild(o); });
  document.body.appendChild(dl);
  _sg._dlists[id] = dl;
  return dl;
}

function _attach(input, listId) {
  if (_sg._dlists[listId]) input.setAttribute('list', listId);
  else setTimeout(() => { if (_sg._dlists[listId]) input.setAttribute('list', listId); }, 1200);
  input.setAttribute('autocomplete', 'off');
}

// ── API ───────────────────────────────────────────────────────────────────────
const enc = n => encodeURIComponent(n);

function _handle401(r) {
  if (r.status === 401) { location.reload(); throw new Error('Session expired'); }
}

async function GET(path) {
  const r = await fetch(path);
  _handle401(r);
  if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || r.statusText); }
  return r.json();
}

async function POST(path, body) {
  const opts = { method: 'POST' };
  if (body !== undefined) { opts.headers = { 'Content-Type': 'application/json' }; opts.body = JSON.stringify(body); }
  const r = await fetch(path, opts);
  if (path !== '/api/login') _handle401(r);
  if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || r.statusText); }
  return r.json();
}

async function DEL(path) {
  const r = await fetch(path, { method: 'DELETE' });
  _handle401(r);
  if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(d.detail || r.statusText); }
  return r.json();
}

// ── status bar (mirrors GTK status_label) ─────────────────────────────────────
let _statusTimer = null;
function statusMsg(msg, cls = '') {
  const el = document.getElementById('status-bar');
  if (!el) return;
  el.textContent = msg;
  el.className = cls;
  clearTimeout(_statusTimer);
  if (msg) _statusTimer = setTimeout(() => { el.textContent = ''; el.className = ''; }, 6000);
}

// ── auth ──────────────────────────────────────────────────────────────────────
async function submitLogin() {
  const user = document.getElementById('login-user').value.trim();
  const pass = document.getElementById('login-pass').value;
  const err  = document.getElementById('login-error');
  const btn  = document.getElementById('login-btn');
  err.textContent = ''; btn.disabled = true;
  try {
    await POST('/api/login', { username: user, password: pass });
    document.getElementById('login-screen').hidden = true;
    await _bootApp();
  } catch (e) {
    err.textContent = e.message || 'Invalid credentials';
  } finally { btn.disabled = false; }
}

document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !document.getElementById('login-screen').hidden) submitLogin();
});

async function doLogout() {
  await POST('/api/logout').catch(() => {});
  location.reload();
}

// ── boot ──────────────────────────────────────────────────────────────────────
addEventListener('DOMContentLoaded', async () => {
  const status = await GET('/api/auth-status').catch(() => ({ authenticated: true, enabled: false }));
  if (!status.authenticated) {
    document.getElementById('login-screen').hidden = false;
    document.getElementById('login-user').focus();
    return;
  }
  // hide sign-out button if auth is disabled (desktop mode)
  if (!status.enabled) {
    document.querySelector('button[onclick="doLogout()"]')?.remove();
  }
  await _bootApp();
});

async function _bootApp() {
  _restoreFilterState();

  GET('/api/suggestions/static').then(s => {
    Object.assign(_sg, s);
    _dl('sg-directives', _sg.directives);
    Object.entries(_sg.values).forEach(([k, vs]) => _dl(`sg-val-${k}`, vs));
    _dl('sg-env-keys', _sg.env_keys);
  }).catch(() => {});

  GET('/api/suggestions/dynamic').then(d => {
    Object.assign(_sg, d);
    _dl('sg-users',    _sg.users);
    _dl('sg-groups',   _sg.groups);
    _dl('sg-targets',  _sg.targets);
    _dl('sg-units',    _sg.units);
    _dl('sg-commands', _sg.commands);
    _dl('sg-disks',    _sg.disks);
  }).catch(() => {});

  try {
    _services = await GET('/api/services');
    renderList();
    if (_services.length) selectService(_services[0]);
  } catch (e) {
    document.getElementById('empty-state').textContent = 'Error: ' + e.message;
  }
}

// ── unit helpers ──────────────────────────────────────────────────────────────
function _unitSuffix(name) { const m = name.match(/\.([^.]+)$/); return m ? m[1] : ''; }
function _unitSortKey(svc) {
  return [svc.favorite ? 0 : 1, TYPE_PRIORITY[_unitSuffix(svc.name)] ?? 99, svc.name.toLowerCase()];
}
function _cmpKeys(a, b) {
  for (let i = 0; i < a.length; i++) { if (a[i] < b[i]) return -1; if (a[i] > b[i]) return 1; }
  return 0;
}
function _sectionName(svc) {
  if (svc.favorite) return 'Pinned';
  return TYPE_LABELS[_unitSuffix(svc.name)] || 'Other';
}
function _isVendorUnit(svc) {
  const p = svc.path || '';
  return p.startsWith('/usr/lib/systemd/system/') || p.startsWith('/lib/systemd/system/');
}
function _canSaveUnit(svc) {
  const p = svc.path || '';
  return p.startsWith('/etc/systemd/system/') || ['custom','app'].includes(svc.service_class);
}
function _canDelete(svc) {
  const p = svc.path || '';
  return p.startsWith('/etc/systemd/system/') || ['custom','app'].includes(svc.service_class);
}
function _saveEndpoint(svc) {
  if (_isVendorUnit(svc)) return 'save-vendor-unit';
  if (_canSaveUnit(svc))  return 'save-unit';
  return 'save';
}
function _saveLabel(svc) {
  if (_isVendorUnit(svc)) return 'Save vendor unit';
  if (_canSaveUnit(svc))  return 'Save unit';
  return 'Save override';
}

// ── list ──────────────────────────────────────────────────────────────────────
function renderList() {
  const ul = document.getElementById('svc-list');
  ul.innerHTML = '';
  const sorted = [..._services].sort((a, b) => _cmpKeys(_unitSortKey(a), _unitSortKey(b)));
  let prevSection = null;
  sorted.forEach(svc => {
    const section = _sectionName(svc);
    if (section !== prevSection) {
      const hdr = document.createElement('li');
      hdr.className = 'list-section-header';
      hdr.textContent = section.toUpperCase();
      ul.appendChild(hdr);
      prevSection = section;
    }
    const li = document.createElement('li');
    li.dataset.name   = svc.name;
    li.dataset.search = [
      svc.name, svc.description, svc.path||'', svc.target||'',
      svc.service_class, svc.status, svc.load_state||'',
      svc.enabled ? 'enabled' : 'disabled',
      (svc.tags||[]).join(' '), (svc.deps||[]).map(d=>d.name).join(' '),
    ].join(' ').toLowerCase();
    li.dataset.fav   = svc.favorite ? '1' : '';
    li.dataset.class = (svc.service_class||'').toLowerCase();
    li.innerHTML = `
      <span class="svc-dot ${svc.status}"></span>
      <div class="svc-info">
        <div class="svc-name">${esc(svc.name)}</div>
        <div class="svc-class">${esc(svc.service_class)}</div>
      </div>
      <button class="star-btn ${svc.favorite?'on':''}"
              title="${svc.favorite?'Remove from favorites':'Add to favorites'}"
              onclick="toggleFav(event,'${escAttr(svc.name)}')">${svc.favorite?'★':'☆'}</button>`;
    li.addEventListener('click', e => { if (!e.target.classList.contains('star-btn')) selectService(svc); });
    ul.appendChild(li);
  });
  filterList();
}

function filterList() {
  const q = document.getElementById('search').value.toLowerCase();
  let shown = 0, lastHdr = null, hdrVisible = false;
  document.querySelectorAll('#svc-list li').forEach(li => {
    if (li.classList.contains('list-section-header')) {
      if (lastHdr) lastHdr.hidden = !hdrVisible;
      lastHdr = li; hdrVisible = false; return;
    }
    const ok = (_classFilter === 'all' || li.dataset.class === _classFilter)
      && (!q || li.dataset.search.includes(q))
      && (!_favOnly || li.dataset.fav === '1');
    li.hidden = !ok;
    if (ok) { shown++; hdrVisible = true; }
  });
  if (lastHdr) lastHdr.hidden = !hdrVisible;
  document.getElementById('svc-count').textContent = `${shown} / ${_services.length}`;
}

function setClassFilter(btn) {
  _classFilter = btn.dataset.class;
  localStorage.setItem('sysd_classFilter', _classFilter);
  document.querySelectorAll('#class-filter .chip').forEach(c => c.classList.toggle('active', c === btn));
  filterList();
}

function _restoreFilterState() {
  _favOnly     = !!localStorage.getItem('sysd_favOnly');
  _classFilter = localStorage.getItem('sysd_classFilter') || 'all';
  _applyFavBtn();
  const chip = document.querySelector(`#class-filter .chip[data-class="${_classFilter}"]`);
  if (chip) {
    document.querySelectorAll('#class-filter .chip').forEach(c => c.classList.toggle('active', c === chip));
  }
}

function toggleFavFilter() {
  _favOnly = !_favOnly;
  localStorage.setItem('sysd_favOnly', _favOnly ? '1' : '');
  _applyFavBtn();
  filterList();
}

function _applyFavBtn() {
  const btn = document.getElementById('fav-toggle');
  if (!btn) return;
  btn.textContent = (_favOnly ? '★' : '☆') + ' Favorites';
  btn.classList.toggle('on', _favOnly);
}

async function toggleFav(e, name) {
  e.stopPropagation();
  try {
    const res = await POST(`/api/services/${enc(name)}/favorite`);
    const idx = _services.findIndex(s => s.name === name);
    if (idx >= 0) _services[idx].favorite = res.favorite;
    renderList();
    document.querySelectorAll('#svc-list li').forEach(li => li.classList.toggle('sel', li.dataset.name === name));
  } catch (err) { console.error(err); }
}

// ── detail ────────────────────────────────────────────────────────────────────
async function selectService(svc) {
  _selected = svc;
  document.querySelectorAll('#svc-list li').forEach(li => li.classList.toggle('sel', li.dataset.name === svc.name));
  document.getElementById('empty-state').hidden = true;
  document.getElementById('create-content').hidden = true;
  document.getElementById('detail-content').hidden = false;
  document.getElementById('d-name').textContent = svc.name;
  document.getElementById('d-desc').textContent = svc.description;
  const badge = document.getElementById('d-status');
  badge.textContent = svc.status; badge.className = 'badge ' + svc.status;
  renderActions(svc);
  renderMeta(svc);
  if (_tab === 'journal') await loadJournal();
  if (_tab === 'editor')  await loadEditor();
}

function renderMeta(svc) {
  const rows = [
    ['Load state', svc.load_state], ['Enabled', svc.enabled ? 'yes' : 'no'],
    ['PID', svc.pid], ['Uptime', svc.uptime], ['Since', svc.since],
    ['Memory', svc.memory], ['CPU', svc.cpu], ['Restarts', svc.restarts],
    ['Target', svc.target], ['Path', svc.path || '—'],
    ['Class', svc.service_class], ['Tags', (svc.tags||[]).join(', ') || '—'],
  ];
  document.getElementById('d-meta').innerHTML =
    rows.map(([k,v]) => `<tr><td>${k}</td><td>${esc(String(v??''))}</td></tr>`).join('');
  const deps = svc.deps || [];
  document.getElementById('d-deps').innerHTML = deps.length
    ? '<h4>Dependencies</h4>' + deps.map(d =>
        `<div class="dep-row"><span class="dep-badge ${d.state==='warn'?'warn':''}">${esc(d.state)}</span><span>${esc(d.name)}</span></div>`).join('')
    : '';
}

// mirrors GTK _actions_for
function renderActions(svc) {
  const acts = [];
  if (svc.status === 'active') {
    acts.push({ label:'Stop',    act:'stop',    cls:'btn danger' });
    acts.push({ label:'Restart', act:'restart', cls:'btn primary' });
  } else if (svc.status === 'failed') {
    acts.push({ label:'Restart', act:'restart', cls:'btn primary' });
    acts.push({ label:'Start',   act:'start',   cls:'btn primary' });
  } else {
    acts.push({ label:'Start', act:'start', cls:'btn primary' });
  }
  acts.push(svc.enabled ? { label:'Disable', act:'disable', cls:'btn' } : { label:'Enable', act:'enable', cls:'btn' });
  acts.push(svc.favorite ? { label:'Unpin', act:'unfavorite', cls:'btn' } : { label:'Pin', act:'favorite', cls:'btn' });
  if (svc.path) {
    acts.push({ label:'Backup',         act:'backup',  cls:'btn' });
    acts.push({ label:'Restore backup', act:'restore', cls:'btn danger' });
  }
  acts.push(svc.enabled
    ? { label:'Mask',   act:'mask',   cls:'btn danger' }
    : { label:'Unmask', act:'unmask', cls:'btn' });
  if (_canDelete(svc)) acts.push({ label:'Delete', act:'delete', cls:'btn danger' });

  document.getElementById('d-actions').innerHTML =
    acts.map(({label, act, cls}) => `<button class="${cls}" onclick="doAction('${act}',this)">${label}</button>`).join('');
}

async function doAction(act, btn) {
  const prev = btn.textContent;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  try {
    if (act === 'delete') {
      btn.textContent = prev; btn.disabled = false;
      if (!confirm(`Delete ${_selected.name} from /etc/systemd/system?`)) return;
      btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
      await DEL(`/api/services/${enc(_selected.name)}`);
      statusMsg(`Deleted ${_selected.name}`, 'ok');
      _services = _services.filter(s => s.name !== _selected.name);
      _selected = null; renderList();
      document.getElementById('detail-content').hidden = true;
      document.getElementById('empty-state').hidden = false;
      return;
    }
    if (act === 'favorite' || act === 'unfavorite') {
      const res = await POST(`/api/services/${enc(_selected.name)}/favorite`);
      const idx = _services.findIndex(s => s.name === _selected.name);
      if (idx >= 0) _services[idx].favorite = res.favorite;
      const fresh = await GET(`/api/services/${enc(_selected.name)}`);
      const idx2 = _services.findIndex(s => s.name === fresh.name);
      if (idx2 >= 0) { fresh.favorite = res.favorite; _services[idx2] = fresh; }
      renderList(); await selectService(fresh);
      statusMsg(`${_selected.name}: ${res.favorite ? 'pinned' : 'unpinned'}`);
      return;
    }
    if (act === 'backup') {
      const res = await POST(`/api/services/${enc(_selected.name)}/backup`);
      statusMsg(`Backup created: ${res.backup}`, 'ok');
      btn.textContent = prev; btn.disabled = false; return;
    }
    if (act === 'restore') {
      btn.textContent = prev; btn.disabled = false;
      if (!confirm(`Restore backup over:\n${_selected.path}`)) return;
      btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
      const res = await POST(`/api/services/${enc(_selected.name)}/restore-backup`);
      statusMsg(`Restored backup: ${res.backup}`, 'ok');
    } else {
      await POST(`/api/services/${enc(_selected.name)}/${act}`);
      statusMsg(`${_selected.name}: ${act}`);
    }
    const fresh = await GET(`/api/services/${enc(_selected.name)}`);
    const idx = _services.findIndex(s => s.name === fresh.name);
    if (idx >= 0) { fresh.favorite = _services[idx].favorite; _services[idx] = fresh; }
    renderList(); await selectService(fresh);
  } catch (err) {
    statusMsg(err.message, 'err');
    btn.textContent = prev; btn.disabled = false;
  }
}

async function daemonReload(btn) {
  const prev = btn.textContent;
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
  statusMsg('Requesting daemon-reload…');
  try {
    await POST('/api/daemon-reload');
    _services = await GET('/api/services');
    renderList();
    if (_selected) {
      const fresh = _services.find(s => s.name === _selected.name);
      if (fresh) await selectService(fresh);
    }
    statusMsg('daemon-reload completed', 'ok');
  } catch (err) { statusMsg(err.message, 'err'); }
  finally { btn.textContent = prev; btn.disabled = false; }
}

// ── tabs ──────────────────────────────────────────────────────────────────────
async function switchTab(btn) {
  _tab = btn.dataset.tab;
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b === btn));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + _tab));
  if (_tab === 'journal') await loadJournal();
  if (_tab === 'editor')  await loadEditor();
}

// ── journal ───────────────────────────────────────────────────────────────────
async function loadJournal() {
  const ul = document.getElementById('d-journal');
  ul.innerHTML = '<li style="color:var(--muted)"><span class="spinner"></span></li>';
  try {
    const entries = await GET(`/api/services/${enc(_selected.name)}/journal`);
    ul.innerHTML = entries.length
      ? entries.map(e => `<li><span class="jtime">${esc(e.time)}</span><span>${esc(e.message)}</span></li>`).join('')
      : '<li style="color:var(--muted)">No journal entries</li>';
  } catch (e) { ul.innerHTML = `<li style="color:var(--failed)">${esc(e.message)}</li>`; }
}

// ── editor ────────────────────────────────────────────────────────────────────
async function loadEditor() {
  const container = document.getElementById('d-editor');
  container.innerHTML = '<span class="spinner"></span>';
  markClean(); _updateSaveBtn(); _updateFooterBtns();

  const reqEl = document.getElementById('d-required-by');
  reqEl.hidden = true; reqEl.textContent = '';
  try {
    const rb = await GET(`/api/services/${enc(_selected.name)}/required-by`);
    if (rb.units && rb.units.length) {
      reqEl.textContent = `⚠ Required by: ${rb.units.join(', ')} — changes here may affect those units.`;
      reqEl.hidden = false;
    }
  } catch (_) {}

  try {
    const [props, sections] = await Promise.all([
      GET(`/api/services/${enc(_selected.name)}/properties`),
      GET(`/api/services/${enc(_selected.name)}/sections`),
    ]);
    container.innerHTML = '';
    container.appendChild(buildEditorForm(_selected.name, props, sections));
    _connectDirtyTracking();
    markClean();
  } catch (e) {
    container.innerHTML = `<span style="color:var(--failed)">${esc(e.message)}</span>`;
  }
}

async function reloadFromDisk() {
  if (_dirty && !confirm('Discard unsaved changes and reload from disk?')) return;
  statusMsg('Reloading from disk…');
  await loadEditor();
  statusMsg(`Reloaded ${_selected?.name} from disk`, 'ok');
}

function _updateSaveBtn() {
  const btn = document.getElementById('save-btn');
  if (!btn || !_selected) return;
  btn.textContent = _saveLabel(_selected);
  btn.title = _isVendorUnit(_selected)
    ? 'Modifies vendor unit file directly. A backup will be created first.'
    : '';
}

function _updateFooterBtns() {
  const hasPath = !!(_selected?.path);
  ['backup-btn','restore-btn','reload-btn'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = !hasPath;
  });
}

function _connectDirtyTracking() {
  document.querySelectorAll('#d-editor .field-input, #d-editor .key-input, #d-editor .env-key, #d-editor .env-val, #d-editor .path-entry-input').forEach(el => {
    el.addEventListener('input', markDirty);
  });
}

function markDirty() {
  _dirty = true;
  const el = document.getElementById('editor-state');
  el.textContent = '● Modified'; el.className = 'dirty';
}

function markClean() {
  _dirty = false;
  const el = document.getElementById('editor-state');
  el.textContent = '● Saved'; el.className = 'clean';
}

// Exec-type keys that get command suggestions (mirrors GTK _apply_value_completion)
const EXEC_KEYS = new Set([
  'ExecStart','ExecReload','ExecStop','ExecStartPre','ExecStartPost',
  'ExecStopPre','ExecStopPost','ExecCondition',
]);

// Path-type keys that get path validation (mirrors GTK _set_path_completion list)
const PATH_KEYS = new Set([
  'WorkingDirectory','RootDirectory','RootImage','EnvironmentFile',
  'SourcePath','RequiresMountsFor','WantsMountsFor',
  'AssertPathExists','AssertPathIsDirectory','AssertPathIsSymbolicLink',
  'AssertFileIsExecutable','ConditionPathExists','ConditionPathIsDirectory',
  'ConditionPathIsSymbolicLink','ConditionFileIsExecutable',
  'ConditionPathExistsGlob','ConditionPathIsMountPoint',
  'ConditionPathIsReadWrite','ConditionDirectoryNotEmpty','ConditionFileNotEmpty',
  'Where','PathExists','PathExistsGlob','PathChanged','PathModified','DirectoryNotEmpty',
]);

// Subset of PATH_KEYS that should open a directory picker
const DIR_KEYS = new Set([
  'WorkingDirectory','RootDirectory','RequiresMountsFor','WantsMountsFor',
  'Where','ConditionPathIsDirectory','AssertPathIsDirectory',
  'ConditionDirectoryNotEmpty','DirectoryNotEmpty',
]);

// ── suggestions wiring ────────────────────────────────────────────────────────
function _attachSuggestions(input, key, section) {
  if (!key) return;
  if (UNIT_DEP_KEYS.has(key))   { _attach(input, 'sg-units');   return; }
  if (key === 'WantedBy')        { _attach(input, 'sg-targets'); return; }
  if (key === 'User')            { _attach(input, 'sg-users');   return; }
  if (key === 'Group')           { _attach(input, 'sg-groups');  return; }
  if (EXEC_KEYS.has(key))        { _attach(input, 'sg-commands'); return; }
  if (key === 'What')            { _attach(input, 'sg-disks');   return; }
  if (PATH_KEYS.has(key))        { _attachPathSuggestions(input); return; }
  if (section && _sg.section_values[section]?.[key]) {
    const id = `sg-secval-${section}-${key}`;
    if (!_sg._dlists[id]) _dl(id, _sg.section_values[section][key]);
    _attach(input, id); return;
  }
  if (_sg.values[key]) { _attach(input, `sg-val-${key}`); return; }
}

function _attachPathSuggestions(input) {
  const dlId = 'sg-paths-live';
  if (!_sg._dlists[dlId]) _dl(dlId, []);
  input.setAttribute('list', dlId);
  input.setAttribute('autocomplete', 'off');
  let _t = null;
  input.addEventListener('input', () => {
    clearTimeout(_t);
    _t = setTimeout(async () => {
      try {
        const items = await GET(`/api/suggestions/paths?prefix=${encodeURIComponent(input.value)}`);
        const dl = _sg._dlists[dlId];
        dl.innerHTML = '';
        items.forEach(v => { const o = document.createElement('option'); o.value = v; dl.appendChild(o); });
      } catch (_) {}
    }, 200);
  });
}

// Section-filtered directive key suggestions
function _attachKeySuggestions(input, section) {
  if (section && _sg.section_directives[section]?.length) {
    const id = `sg-keys-${section}`;
    if (!_sg._dlists[id]) _dl(id, _sg.section_directives[section]);
    _attach(input, id);
    return;
  }
  _attach(input, 'sg-directives');
}

// ── validation helpers ────────────────────────────────────────────────────────
// Mirrors GTK _on_unit_value_changed
function _validateUnitRef(input, hintEl) {
  const text = input.value.trim();
  if (!text || !_sg.units.length) { _clearHint(input, hintEl); return; }
  const missing = text.split(/\s+/).filter(t => t && !_sg.units.includes(t));
  if (missing.length) {
    _setHint(input, hintEl, `Unit not found: ${missing.join(', ')}`, 'err');
  } else { _clearHint(input, hintEl); }
}

// Validates directive key: unknown = error, wrong section = warning
function _validateDirectiveKey(input, hintEl, section) {
  const name = input.value.trim();
  if (!name || !_sg.directives.length) { _clearHint(input, hintEl); return; }
  const knownSections = Object.entries(_sg.section_directives)
    .filter(([, dirs]) => dirs.includes(name))
    .map(([sec]) => sec);
  if (!knownSections.length) {
    _setHint(input, hintEl, `Unknown directive: ${name}`, 'err');
  } else if (section && !knownSections.includes(section)) {
    _setHint(input, hintEl, `Belongs to [${knownSections.join('/')}], not [${section}]`, 'warn');
  } else {
    _clearHint(input, hintEl);
  }
}

function _setHint(input, hintEl, msg, cls) {
  input.classList.add('err'); // uses .field-input.err CSS
  if (hintEl) { hintEl.textContent = msg; hintEl.className = `field-hint ${cls}`; hintEl.hidden = false; }
}
function _clearHint(input, hintEl) {
  input.classList.remove('err');
  if (hintEl) { hintEl.textContent = ''; hintEl.hidden = true; }
}

// Path keys: check existence via API (mirrors GTK _single_path_row refresh_check)
let _pathDebounceMap = new WeakMap();
function _validatePathInput(input, hintEl) {
  const val = input.value.trim();
  if (!val) { _clearHint(input, hintEl); return; }
  clearTimeout(_pathDebounceMap.get(input));
  _pathDebounceMap.set(input, setTimeout(async () => {
    try {
      const r = await GET(`/api/check-path?path=${encodeURIComponent(val)}`);
      if (!r.exists) {
        _setHint(input, hintEl, r.message, 'err');
      } else if (r.is_dir) {
        _setHint(input, hintEl, r.message, 'ok');
        input.classList.remove('err');
      } else {
        _setHint(input, hintEl, r.message, 'ok');
        input.classList.remove('err');
      }
    } catch (_) {}
  }, 500));
}

// ExecStart: check via API
let _execDebounce = null;
function _validateExecStart(input, hintEl) {
  clearTimeout(_execDebounce);
  const val = input.value.trim();
  if (!val) { _setHint(input, hintEl, 'ExecStart is required', 'err'); return; }
  _execDebounce = setTimeout(async () => {
    try {
      const r = await GET(`/api/check-exec?cmd=${encodeURIComponent(val)}`);
      if (!r.ok) _setHint(input, hintEl, r.message, 'err');
      else _clearHint(input, hintEl);
    } catch (_) {}
  }, 500);
}

// ── editor form ───────────────────────────────────────────────────────────────
function buildEditorForm(unitName, props, fileSections) {
  const suffix  = Object.keys(SUFFIX_SECTION).find(s => unitName.endsWith(s)) || '.service';
  const typeSec = SUFFIX_SECTION[suffix] || 'Service';

  const ORDER = ['Unit', typeSec, 'Install', 'Extra'].filter((s,i,a) => a.indexOf(s) === i);
  const rows  = Object.fromEntries(ORDER.map(s => [s, []]));

  COMMON_FIELDS.forEach(key => {
    const sec = FIELD_SECTION[key] || 'Service';
    if (rows[sec] !== undefined)
      rows[sec].push({ key, value: props[key] || '', isCommon: true });
  });

  Object.entries(fileSections).forEach(([sec, pairs]) => {
    const target = rows[sec] !== undefined ? sec : 'Extra';
    pairs.filter(p => !COMMON_SET.has(p.key))
         .forEach(p => rows[target].push({ key: p.key, value: p.value, isCommon: false }));
  });

  const wrap = document.createElement('div');
  ORDER.forEach(sec => {
    const block = makeSection(`[${sec}]`);
    rows[sec].forEach(({ key, value, isCommon }) => {
      if (key === 'Environment')  block.body.appendChild(makeEnvEditorRow(value));
      else if (key === 'ExecStart') block.body.appendChild(makeExecStartRow(key, value, sec));
      else if (isCommon)          block.body.appendChild(makeFieldRow(key, value, sec, true));
      else                        block.body.appendChild(makeExtraRow(sec, key, value));
    });
    _appendAddDirectiveBtn(block.body, sec);
    wrap.appendChild(block.el);
  });

  // ── "+ Add section" button (mirrors GTK _on_add_section) ──────────────────
  const existingSections = new Set(ORDER);
  const addSecBtn = document.createElement('button');
  addSecBtn.className = 'add-row-btn';
  addSecBtn.style.cssText = 'margin: 8px 0; display: block;';
  addSecBtn.textContent = '+ Add section';
  addSecBtn.title = 'Add a standard systemd section to this unit';
  addSecBtn.onclick = () => _showAddSectionPicker(addSecBtn, wrap, existingSections);
  wrap.appendChild(addSecBtn);

  return wrap;
}

function _appendAddDirectiveBtn(body, sec) {
  const addBtn = document.createElement('button');
  addBtn.className = 'add-row-btn';
  addBtn.textContent = '+ Add directive';
  addBtn.onclick = () => {
    const row = makeExtraRow(sec, '', '');
    body.insertBefore(row, addBtn);
    row.querySelector('.key-input')?.focus();
    markDirty();
  };
  body.appendChild(addBtn);
}

// mirrors GTK _on_add_section
function _showAddSectionPicker(anchor, wrap, existingSections) {
  const available = ALL_SECTIONS.filter(s => !existingSections.has(s));
  if (!available.length) { statusMsg('All standard sections already present'); return; }

  // Simple inline dropdown (no Popover API required)
  const existing = document.getElementById('_add-sec-menu');
  if (existing) existing.remove();

  const menu = document.createElement('div');
  menu.id = '_add-sec-menu';
  menu.className = 'add-sec-menu';
  available.forEach(sec => {
    const item = document.createElement('button');
    item.textContent = `[${sec}]`;
    item.onclick = () => {
      menu.remove();
      existingSections.add(sec);
      const block = makeSection(`[${sec}]`);
      _appendAddDirectiveBtn(block.body, sec);
      // insert before the "+ Add section" button
      wrap.insertBefore(block.el, anchor);
      block.el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      statusMsg(`[${sec}] section added`);
      markDirty();
    };
    menu.appendChild(item);
  });
  document.body.appendChild(menu);
  const rect = anchor.getBoundingClientRect();
  menu.style.top  = (rect.bottom + scrollY) + 'px';
  menu.style.left = rect.left + 'px';
  setTimeout(() => document.addEventListener('click', () => menu.remove(), { once: true }), 0);
}

function makeSection(title) {
  const el = document.createElement('div');
  el.className = 'section-block';
  const header = document.createElement('div');
  header.className = 'section-title';
  header.innerHTML = `<span class="fold-arrow">▼</span>${esc(title)}`;
  const body = document.createElement('div');
  body.className = 'section-body';
  header.addEventListener('click', () => {
    const c = body.classList.toggle('collapsed');
    header.classList.toggle('collapsed', c);
  });
  el.appendChild(header); el.appendChild(body);
  return { el, body };
}

// Common field row — label is cyan (mirrors GTK .common-label)
function makeFieldRow(key, value, section, isCommon) {
  const row = document.createElement('div');
  row.className = 'field-row';

  const lbl = document.createElement('span');
  lbl.className = isCommon ? 'field-label common' : 'field-label';
  lbl.textContent = key;

  const wrap = document.createElement('div');
  wrap.style.flex = '1'; wrap.style.display = 'flex'; wrap.style.flexDirection = 'column'; wrap.style.gap = '2px';

  const input = document.createElement('input');
  input.className = 'field-input prop-input';
  input.dataset.key = key; input.value = value;
  _attachSuggestions(input, key, section || FIELD_SECTION[key] || '');

  const hint = document.createElement('div');
  hint.className = 'field-hint'; hint.hidden = true;

  // input row: input + optional browse button side-by-side
  const inputRow = document.createElement('div');
  inputRow.style.cssText = 'display:flex;gap:4px;align-items:center';
  inputRow.appendChild(input);

  if (UNIT_DEP_KEYS.has(key)) {
    input.addEventListener('input', () => { _validateUnitRef(input, hint); markDirty(); });
    _validateUnitRef(input, hint);
  } else if (PATH_KEYS.has(key)) {
    inputRow.appendChild(_makeBrowseBtn(input, { directory: DIR_KEYS.has(key) }));
    input.addEventListener('input', () => { _validatePathInput(input, hint); markDirty(); });
    if (value) _validatePathInput(input, hint);
  } else if (EXEC_KEYS.has(key)) {
    inputRow.appendChild(_makeBrowseBtn(input, { replaceFirstToken: true }));
    input.addEventListener('input', markDirty);
  } else {
    input.addEventListener('input', markDirty);
  }

  wrap.appendChild(inputRow); wrap.appendChild(hint);
  row.appendChild(lbl); row.appendChild(wrap);
  return row;
}

// ExecStart row with real validation via API
function makeExecStartRow(key, value, section) {
  const row = document.createElement('div');
  row.className = 'field-row';
  row.style.alignItems = 'flex-start';

  const lbl = document.createElement('span');
  lbl.className = 'field-label common';
  lbl.textContent = key;
  lbl.style.paddingTop = '7px';

  const wrap = document.createElement('div');
  wrap.style.flex = '1'; wrap.style.display = 'flex'; wrap.style.flexDirection = 'column'; wrap.style.gap = '4px';

  const inputRow = document.createElement('div');
  inputRow.style.cssText = 'display:flex;gap:4px;align-items:center';

  const input = document.createElement('input');
  input.className = 'field-input prop-input';
  input.dataset.key = key; input.value = value;
  _attach(input, 'sg-commands');
  inputRow.appendChild(input);
  inputRow.appendChild(_makeBrowseBtn(input, { replaceFirstToken: true }));

  const hint = document.createElement('div');
  hint.className = 'field-hint'; hint.hidden = true;

  input.addEventListener('input', () => { _validateExecStart(input, hint); markDirty(); });
  if (value) _validateExecStart(input, hint);

  wrap.appendChild(inputRow); wrap.appendChild(hint);
  row.appendChild(lbl); row.appendChild(wrap);
  return row;
}

// Extra (non-common) directive row with key+value+remove+validation
function makeExtraRow(section, key, value) {
  const row = document.createElement('div');
  row.className = 'field-row extra-row';
  row.dataset.section = section;
  row.style.alignItems = 'flex-start';

  const keyWrap = document.createElement('div');
  keyWrap.style.cssText = 'display:flex;flex-direction:column;gap:2px;width:160px;flex-shrink:0';
  const keyIn = document.createElement('input');
  keyIn.className = 'key-input extra-key';
  keyIn.placeholder = 'Directive'; keyIn.value = key;
  _attachKeySuggestions(keyIn, section);
  const keyHint = document.createElement('div');
  keyHint.className = 'field-hint'; keyHint.hidden = true;
  keyWrap.appendChild(keyIn); keyWrap.appendChild(keyHint);

  const valWrap = document.createElement('div');
  valWrap.style.cssText = 'display:flex;flex-direction:column;gap:2px;flex:1';
  const valInRow = document.createElement('div');
  valInRow.style.cssText = 'display:flex;gap:4px;align-items:center';
  const valIn = document.createElement('input');
  valIn.className = 'field-input extra-val';
  valIn.placeholder = 'Value'; valIn.value = value;
  if (key) _attachSuggestions(valIn, key, section);
  valInRow.appendChild(valIn);
  if (EXEC_KEYS.has(key)) valInRow.appendChild(_makeBrowseBtn(valIn, { replaceFirstToken: true }));
  else if (PATH_KEYS.has(key)) valInRow.appendChild(_makeBrowseBtn(valIn, { directory: DIR_KEYS.has(key) }));
  const valHint = document.createElement('div');
  valHint.className = 'field-hint'; valHint.hidden = true;
  valWrap.appendChild(valInRow); valWrap.appendChild(valHint);

  const rmBtn = document.createElement('button');
  rmBtn.className = 'remove-row';
  rmBtn.textContent = '×';
  rmBtn.style.marginTop = '4px';
  rmBtn.onclick = () => { row.remove(); markDirty(); };

  keyIn.addEventListener('input', () => {
    const k = keyIn.value.trim();
    _validateDirectiveKey(keyIn, keyHint, section);
    _attachSuggestions(valIn, k, section);
    if (UNIT_DEP_KEYS.has(k)) {
      valIn.addEventListener('input', () => _validateUnitRef(valIn, valHint));
      _validateUnitRef(valIn, valHint);
    } else if (PATH_KEYS.has(k)) {
      valIn.addEventListener('input', () => { _validatePathInput(valIn, valHint); markDirty(); });
    }
    markDirty();
  });
  valIn.addEventListener('input', markDirty);

  if (key) { _validateDirectiveKey(keyIn, keyHint, section); }
  if (UNIT_DEP_KEYS.has(key) && value) _validateUnitRef(valIn, valHint);
  if (PATH_KEYS.has(key) && value) _validatePathInput(valIn, valHint);

  row.appendChild(keyWrap); row.appendChild(valWrap); row.appendChild(rmBtn);
  return row;
}

// ── Environment editor ────────────────────────────────────────────────────────
function _parseEnvText(raw) {
  const result = [];
  for (const line of (raw||'').split('\n')) {
    const chunk = line.trim();
    if (!chunk) continue;
    const eq = chunk.indexOf('=');
    if (eq === -1) { result.push({ key: chunk, value: '' }); continue; }
    let val = chunk.slice(eq + 1);
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'")))
      val = val.slice(1, -1);
    result.push({ key: chunk.slice(0, eq), value: val });
  }
  return result;
}

// GTK: _build_environment_editor — ▼Variables with Add variable + PATH block support
function makeEnvEditorRow(rawValue) {
  const wrapper = document.createElement('div');
  wrapper.className = 'field-row env-editor-wrapper';

  const lbl = document.createElement('span');
  lbl.className = 'field-label common env-field-label';
  lbl.textContent = 'Environment';
  wrapper.appendChild(lbl);

  const right = document.createElement('div');
  right.style.flex = '1';
  wrapper.appendChild(right);

  // hidden prop-input (collected by doSave)
  const hidden = document.createElement('input');
  hidden.type = 'hidden'; hidden.className = 'prop-input'; hidden.dataset.key = 'Environment';
  right.appendChild(hidden);

  // ▼ Variables section
  const varSection = _makeFoldable('Variables', () => [_makeAddVarBtn(), _makeAddPathBtn()]);
  right.appendChild(varSection.el);
  const varBody = varSection.body;

  let pathBlock = null;

  function syncHidden() {
    const lines = [];
    varBody.querySelectorAll('.env-kv-row').forEach(row => {
      const k = row.querySelector('.env-key')?.value.trim();
      const v = row.querySelector('.env-val')?.value ?? '';
      if (k) lines.push(k + '=' + v);
    });
    if (pathBlock) {
      const parts = [];
      pathBlock.querySelectorAll('.path-entry-input').forEach(inp => {
        const v = inp.value.trim(); if (v) parts.push(v);
      });
      if (parts.length) lines.push('PATH=' + parts.join(':'));
    }
    hidden.value = lines.join('\n');
  }

  function addEnvRow(key, value) {
    // If key is PATH, convert to PATH block (mirrors GTK _on_environment_key_changed)
    if (key === 'PATH') { addPathBlock(value); return; }
    const row = _makeEnvKvRow(key, value, syncHidden, () => { row.remove(); syncHidden(); markDirty(); });
    // Wire: if user types "PATH" in key field → convert
    row.querySelector('.env-key').addEventListener('change', e => {
      if (e.target.value.trim() === 'PATH') {
        const val = row.querySelector('.env-val')?.value || '';
        row.remove(); addPathBlock(val); syncHidden(); markDirty();
      }
    });
    varBody.appendChild(row); syncHidden();
  }

  function addPathBlock(rawPath) {
    if (pathBlock) return;
    pathBlock = _makePathBlock(rawPath, syncHidden, () => {
      pathBlock.remove(); pathBlock = null; syncHidden(); markDirty();
    });
    varBody.appendChild(pathBlock); syncHidden();
  }

  function _makeAddVarBtn() {
    const btn = document.createElement('button');
    btn.className = 'env-action-btn'; btn.textContent = 'Add variable';
    btn.onclick = () => { addEnvRow('', ''); markDirty(); };
    return btn;
  }
  function _makeAddPathBtn() {
    const btn = document.createElement('button');
    btn.className = 'env-action-btn'; btn.textContent = 'Add PATH variable';
    btn.title = 'Add PATH with one directory per row';
    btn.onclick = () => { addPathBlock(''); markDirty(); };
    return btn;
  }

  _parseEnvText(rawValue).forEach(({ key, value }) => addEnvRow(key, value));
  syncHidden();
  return wrapper;
}

// ── foldable sub-section ──────────────────────────────────────────────────────
function _makeFoldable(title, makeActions) {
  const el = document.createElement('div');
  el.className = 'env-fold-block';
  const hdr = document.createElement('div');
  hdr.className = 'env-fold-header';
  const arrow = document.createElement('span');
  arrow.className = 'fold-arrow'; arrow.textContent = '▼';
  const titleSpan = document.createElement('span');
  titleSpan.className = 'env-fold-title'; titleSpan.textContent = title;
  const spacer = document.createElement('span'); spacer.style.flex = '1';
  hdr.appendChild(arrow); hdr.appendChild(titleSpan); hdr.appendChild(spacer);
  (makeActions ? makeActions() : []).forEach(a => hdr.appendChild(a));
  const body = document.createElement('div');
  body.className = 'env-fold-body';
  hdr.addEventListener('click', e => {
    if (e.target.tagName === 'BUTTON') return;
    const c = body.classList.toggle('collapsed');
    arrow.style.transform = c ? 'rotate(-90deg)' : '';
  });
  el.appendChild(hdr); el.appendChild(body);
  return { el, body };
}

// ── env KEY=VALUE row ──────────────────────────────────────────────────────────
function _looksLikePath(v) {
  return v.startsWith('/') || v.startsWith('~/') || v.startsWith('./') || v.startsWith('../');
}

function _envKeyIsDir(k) {
  const u = k.toUpperCase();
  if (/FILE|EXEC|BIN|CMD|COMMAND/.test(u)) return false;
  return true; // most env var paths are directories
}

function _makeEnvKvRow(key, value, syncHidden, removeCallback) {
  const row = document.createElement('div');
  row.className = 'env-kv-row';
  row.style.alignItems = 'flex-start';

  const keyIn = document.createElement('input');
  keyIn.className = 'key-input env-key'; keyIn.placeholder = 'VARIABLE'; keyIn.value = key;
  keyIn.style.marginTop = '4px';
  _attach(keyIn, 'sg-env-keys');

  const eq = document.createElement('span');
  eq.className = 'env-eq'; eq.textContent = '='; eq.style.marginTop = '7px';

  const valWrap = document.createElement('div');
  valWrap.style.cssText = 'flex:1;display:flex;flex-direction:column;gap:2px';

  const valRow = document.createElement('div');
  valRow.style.cssText = 'display:flex;gap:4px;align-items:center';

  const valIn = document.createElement('input');
  valIn.className = 'field-input env-val'; valIn.placeholder = 'value'; valIn.value = value;

  const browseBtn = document.createElement('button');
  browseBtn.type = 'button'; browseBtn.className = 'browse-btn'; browseBtn.textContent = '…';
  browseBtn.title = 'Browse…'; browseBtn.hidden = true;

  const hint = document.createElement('div');
  hint.className = 'field-hint'; hint.hidden = true;

  valRow.appendChild(valIn); valRow.appendChild(browseBtn);
  valWrap.appendChild(valRow); valWrap.appendChild(hint);

  const rmBtn = document.createElement('button');
  rmBtn.className = 'env-action-btn env-remove-btn'; rmBtn.textContent = 'Remove variable';
  rmBtn.style.marginTop = '2px';
  if (removeCallback) rmBtn.onclick = removeCallback;

  let _pathTimer = null;
  function _checkValAsPath() {
    syncHidden(); markDirty();
    const v = valIn.value.trim();
    if (!_looksLikePath(v)) {
      browseBtn.hidden = true;
      _clearHint(valIn, hint);
      return;
    }
    const isDir = _envKeyIsDir(keyIn.value.trim());
    browseBtn.hidden = false;
    browseBtn.onclick = () => _pickFile(valIn, { directory: isDir });
    clearTimeout(_pathTimer);
    _pathTimer = setTimeout(async () => {
      try {
        const r = await GET(`/api/check-path?path=${encodeURIComponent(v)}`);
        if (!r.exists) _setHint(valIn, hint, r.message, 'err');
        else { _setHint(valIn, hint, r.message, 'ok'); valIn.classList.remove('err'); }
      } catch (_) {}
    }, 400);
  }

  keyIn.addEventListener('input', () => { syncHidden(); markDirty(); });
  valIn.addEventListener('input', _checkValAsPath);
  if (value) _checkValAsPath();

  row.appendChild(keyIn); row.appendChild(eq); row.appendChild(valWrap); row.appendChild(rmBtn);
  return row;
}

// ── PATH block ────────────────────────────────────────────────────────────────
function _makePathBlock(rawPath, syncHidden, removeBlock) {
  const ps = _makeFoldable('PATH', () => {
    const addBtn = document.createElement('button');
    addBtn.className = 'env-action-btn'; addBtn.textContent = 'Add entry';
    addBtn.onclick = () => { _appendPathEntry(''); markDirty(); };
    const rmBtn = document.createElement('button');
    rmBtn.className = 'env-action-btn env-remove-btn'; rmBtn.textContent = 'Remove variable';
    rmBtn.onclick = removeBlock;
    return [addBtn, rmBtn];
  });
  ps.el.className += ' env-path-block';
  const parts = rawPath.split(':').map(p => p.trim()).filter(Boolean);
  function _appendPathEntry(val) {
    const entryEl = _makePathEntry(val, syncHidden, () => { entryEl.remove(); syncHidden(); markDirty(); });
    ps.body.appendChild(entryEl); syncHidden();
  }
  (parts.length ? parts : ['']).forEach(p => _appendPathEntry(p));
  return ps.el;
}

function _makePathEntry(value, syncHidden, removeCallback) {
  const wrap = document.createElement('div'); wrap.className = 'env-path-entry';
  const row  = document.createElement('div'); row.className  = 'env-path-row';
  const inp  = document.createElement('input');
  inp.className = 'field-input path-entry-input'; inp.placeholder = '/path/to/directory'; inp.value = value;
  const browseBtn = _makeBrowseBtn(inp, { directory: true });
  const rmBtn = document.createElement('button');
  rmBtn.className = 'env-action-btn env-remove-btn'; rmBtn.textContent = 'Remove entry';
  rmBtn.onclick = removeCallback;
  row.appendChild(inp); row.appendChild(browseBtn); row.appendChild(rmBtn); wrap.appendChild(row);
  const hint = document.createElement('div'); hint.className = 'path-hint'; wrap.appendChild(hint);
  let _pathEntryTimer = null;
  function checkPath() {
    const v = inp.value.trim();
    syncHidden(); markDirty();
    if (!v) { hint.textContent = ''; hint.className = 'path-hint'; inp.classList.remove('err'); return; }
    if (!v.startsWith('/') && !v.startsWith('~') && !v.startsWith('.')) {
      hint.textContent = '⚠ Not an absolute path';
      hint.className = 'path-hint path-hint-warn';
      inp.classList.add('err'); return;
    }
    clearTimeout(_pathEntryTimer);
    _pathEntryTimer = setTimeout(async () => {
      try {
        const r = await GET(`/api/check-path?path=${encodeURIComponent(v)}`);
        if (!r.exists) {
          hint.textContent = r.message; hint.className = 'path-hint path-hint-err'; inp.classList.add('err');
        } else if (r.is_dir) {
          hint.textContent = r.message; hint.className = 'path-hint path-hint-ok'; inp.classList.remove('err');
        } else {
          hint.textContent = r.message; hint.className = 'path-hint path-hint-ok'; inp.classList.remove('err');
        }
      } catch (_) {}
    }, 400);
  }
  inp.addEventListener('input', checkPath); checkPath();
  return wrap;
}

// ── save ──────────────────────────────────────────────────────────────────────
async function doSave() {
  if (!_selected) return;

  // mirrors GTK _on_save_unit_clicked: warn on ExecStart issue before saving
  const execInput = document.querySelector('#d-editor .prop-input[data-key="ExecStart"]');
  if (execInput) {
    const hint = execInput.parentElement?.querySelector('.field-hint');
    const hintMsg = hint && !hint.hidden ? hint.textContent : '';
    if (hintMsg && !confirm(`${hintMsg}\n\nContinue saving anyway?`)) {
      statusMsg('Save cancelled');
      return;
    }
  }

  if (_isVendorUnit(_selected)) {
    if (!confirm(`Modify vendor unit file directly:\n${_selected.path}\n\nA backup will be created first. Continue?`)) return;
  }
  const fields = {};
  document.querySelectorAll('#d-editor .prop-input').forEach(el => { fields[el.dataset.key] = el.value; });
  const extra = [];
  document.querySelectorAll('#d-editor .extra-row').forEach(row => {
    const key = row.querySelector('.extra-key')?.value.trim();
    const val = row.querySelector('.extra-val')?.value.trim() ?? '';
    if (key) extra.push([key, val]);
  });
  const status = document.getElementById('save-status');
  status.textContent = ''; status.className = '';
  try {
    await POST(`/api/services/${enc(_selected.name)}/${_saveEndpoint(_selected)}`, { fields, extra });
    status.textContent = '✓ Saved'; status.className = 'ok';
    statusMsg(`Saved ${_selected.name}`, 'ok');
    markClean();
  } catch (e) {
    status.textContent = '✗ ' + e.message; status.className = 'err';
    statusMsg(e.message, 'err');
  }
  setTimeout(() => { status.textContent = ''; status.className = ''; }, 4000);
}

// ── backup / restore (editor footer) ─────────────────────────────────────────
async function doBackup() {
  const btn = document.getElementById('backup-btn');
  btn.disabled = true;
  try {
    const res = await POST(`/api/services/${enc(_selected.name)}/backup`);
    statusMsg(`Backup created: ${res.backup}`, 'ok');
    document.getElementById('save-status').textContent = `✓ ${res.backup}`;
    document.getElementById('save-status').className = 'ok';
  } catch (e) {
    statusMsg(e.message, 'err');
  } finally { btn.disabled = false; }
  setTimeout(() => { document.getElementById('save-status').textContent = ''; document.getElementById('save-status').className = ''; }, 6000);
}

async function doRestore() {
  if (!confirm(`Restore backup over:\n${_selected.path}`)) return;
  const btn = document.getElementById('restore-btn'); btn.disabled = true;
  try {
    await POST(`/api/services/${enc(_selected.name)}/restore-backup`);
    statusMsg('Restored backup', 'ok');
    await loadEditor();
  } catch (e) {
    statusMsg(e.message, 'err'); btn.disabled = false;
  }
}

// ── create panel ──────────────────────────────────────────────────────────────
function openCreateModal() {
  _selected = null;
  _createLastSuffix = null;
  document.getElementById('create-name').value = '';
  document.getElementById('create-type').value = '.service';
  document.getElementById('create-type').disabled = false;
  document.getElementById('create-name-preview').textContent = '';
  document.getElementById('create-status').textContent = '';
  document.getElementById('create-status').className = '';
  document.getElementById('create-form-sections').innerHTML = '';
  document.getElementById('empty-state').hidden = true;
  document.getElementById('detail-content').hidden = true;
  document.getElementById('create-content').hidden = false;
  document.getElementById('create-name').focus();
}

function closeCreatePanel() {
  document.getElementById('create-content').hidden = true;
  if (_selected) {
    document.getElementById('detail-content').hidden = false;
  } else {
    document.getElementById('empty-state').hidden = false;
  }
}

let _createLastSuffix = null;

function _createFullName() {
  const base   = document.getElementById('create-name').value.trim();
  const suffix = document.getElementById('create-type').value;
  return base ? base + suffix : '';
}

function _updateCreatePreview() {
  const full = _createFullName();
  document.getElementById('create-name-preview').textContent = full || '';
}

function _buildCreateForm() {
  const suffix     = document.getElementById('create-type').value;
  _createLastSuffix = suffix;
  const fakeName   = _createFullName() || ('new' + suffix);
  const emptyProps = Object.fromEntries(COMMON_FIELDS.map(k => [k, '']));
  const container  = document.getElementById('create-form-sections');
  container.innerHTML = '';
  container.appendChild(buildEditorForm(fakeName, emptyProps, {}));
  document.getElementById('create-type').disabled = true;
}

function onCreateNameChange() {
  _updateCreatePreview();
  const container = document.getElementById('create-form-sections');
  if (!container.hasChildNodes()) _buildCreateForm();
}

function onCreateTypeChange() {
  _updateCreatePreview();
  const suffix = document.getElementById('create-type').value;
  if (suffix === _createLastSuffix) return;
  const container = document.getElementById('create-form-sections');
  if (container.hasChildNodes()) _buildCreateForm();
}

async function submitCreate() {
  const name   = _createFullName();
  const status = document.getElementById('create-status');
  status.textContent = ''; status.className = '';

  if (!name) { status.textContent = 'Name is required'; status.className = 'err'; return; }

  const execInput = document.querySelector('#create-form-sections .prop-input[data-key="ExecStart"]');
  const execVal   = execInput?.value.trim() || '';
  if (!execVal) { status.textContent = 'ExecStart is required'; status.className = 'err'; execInput?.focus(); return; }

  const execHint = execInput?.parentElement?.querySelector('.field-hint');
  const execHintMsg = execHint && !execHint.hidden ? execHint.textContent : '';
  if (execHintMsg && !confirm(`${execHintMsg}\n\nContinue creating the service anyway?`)) {
    status.textContent = 'Service creation cancelled'; status.className = '';
    return;
  }

  const fields = {};
  document.querySelectorAll('#create-form-sections .prop-input').forEach(el => {
    if (el.value.trim()) fields[el.dataset.key] = el.value;
  });
  const extra = [];
  document.querySelectorAll('#create-form-sections .extra-row').forEach(row => {
    const k = row.querySelector('.extra-key')?.value.trim();
    const v = row.querySelector('.extra-val')?.value.trim() ?? '';
    if (k) extra.push([k, v]);
  });

  try {
    const res     = await POST('/api/services', { name, fields, extra });
    const created = res.name;

    if ((fields['WantedBy'] || '').trim()) {
      try { await POST(`/api/services/${enc(created)}/enable`); } catch (_) {}
    }
    try { await POST(`/api/services/${enc(created)}/favorite`); } catch (_) {}

    _services = await GET('/api/services');
    renderList();
    statusMsg(`Created ${created}`, 'ok');
    const svc = _services.find(s => s.name === created);
    if (svc) {
      closeCreatePanel();
      await selectService(svc);
      const edTab = document.querySelector('.tab[data-tab="editor"]');
      if (edTab) await switchTab(edTab);
    } else {
      closeCreatePanel();
    }
  } catch (e) { status.textContent = '✗ ' + e.message; status.className = 'err'; }
}

// ── test run ──────────────────────────────────────────────────────────────────
let _testSource = null;

function testRun() {
  if (!_selected) return;

  const execInput = document.querySelector('#d-editor .prop-input[data-key="ExecStart"]');
  const cmd = execInput?.value.trim();
  if (!cmd) { statusMsg('ExecStart is empty — nothing to test', 'err'); return; }

  const term    = document.getElementById('test-terminal');
  const output  = document.getElementById('term-output');
  const stopBtn = document.getElementById('test-stop-btn');

  term.hidden = false;
  output.textContent = '';
  stopBtn.disabled = false;

  if (_testSource) { _testSource.close(); _testSource = null; }

  const url = `/api/services/${enc(_selected.name)}/test-run?cmd=${encodeURIComponent(cmd)}`;
  _testSource = new EventSource(url);

  _testSource.onmessage = e => {
    output.textContent += e.data + '\n';
    output.scrollTop = output.scrollHeight;
  };

  _testSource.onerror = () => {
    _testSource.close(); _testSource = null;
    stopBtn.disabled = true;
  };
}

async function testStop() {
  if (_testSource) { _testSource.close(); _testSource = null; }
  const stopBtn = document.getElementById('test-stop-btn');
  if (stopBtn) stopBtn.disabled = true;
  if (!_selected) return;
  try {
    await POST(`/api/services/${enc(_selected.name)}/test-stop`);
  } catch (e) { statusMsg(e.message, 'err'); }
}

function closeTestTerminal() {
  testStop();
  document.getElementById('test-terminal').hidden = true;
}

// ── add-section dropdown CSS/menu ─────────────────────────────────────────────
const _addSecStyle = document.createElement('style');
_addSecStyle.textContent = `
.add-sec-menu { position:absolute; z-index:200; background:var(--panel2); border:1px solid var(--border); border-radius:8px; box-shadow:0 4px 18px rgba(0,0,0,.5); padding:4px; min-width:160px; }
.add-sec-menu button { display:block; width:100%; text-align:left; padding:7px 14px; background:none; border:none; color:var(--text); font-size:.87em; border-radius:5px; cursor:pointer; font-family:monospace; }
.add-sec-menu button:hover { background:rgba(76,201,240,.12); color:var(--accent); }
`;
document.head.appendChild(_addSecStyle);

// ── file picker ───────────────────────────────────────────────────────────────
// Opens a native file dialog server-side via zenity/kdialog.
async function _pickFile(input, { directory = false, replaceFirstToken = false } = {}) {
  try {
    const r = await GET(`/api/pick-file?directory=${directory}`);
    if (!r.ok) {
      if (r.message !== 'cancelled') statusMsg(r.message || 'File dialog unavailable', 'err');
      return;
    }
    const path = r.path;
    if (replaceFirstToken && input.value.trim()) {
      const first = input.value.trim().split(/\s+/)[0];
      input.value = input.value.replace(first, path);
    } else {
      input.value = path;
    }
    input.dispatchEvent(new Event('input', { bubbles: true }));
  } catch (e) { statusMsg(e.message, 'err'); }
}

function _makeBrowseBtn(input, opts) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'browse-btn';
  btn.textContent = '…';
  btn.title = 'Browse…';
  btn.onclick = () => _pickFile(input, opts);
  return btn;
}


// ── util ──────────────────────────────────────────────────────────────────────
function esc(s)     { return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escAttr(s) { return String(s??'').replace(/&/g,'&amp;').replace(/"/g,'&quot;'); }
