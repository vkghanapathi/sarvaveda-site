/* sarvaveda.info/devataa — find, script toggle, plate viewer. No storage beyond a remembered script. */
(function () {
  // Telugu -> Devanagari, codepoint for codepoint; the Telugu text stays the source.
  // Short e/o (Telugu ఎ ఒ ె ొ) are the Sanskrit e/o, so they go to ए ओ े ो.
  var FIX = {0x0C0E: 0x090F, 0x0C12: 0x0913, 0x0C46: 0x0947, 0x0C4A: 0x094B};
  function toDeva(s) {
    var out = '';
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if (FIX[c]) out += String.fromCharCode(FIX[c]);
      else if (c >= 0x0C00 && c <= 0x0C7F) out += String.fromCharCode(c - 0x0300);
      else out += s[i];
    }
    return out;
  }
  function setScript(sc) {
    document.querySelectorAll('.sl').forEach(function (el) {
      if (!el.dataset.te) el.dataset.te = el.innerHTML;
      el.innerHTML = sc === 'dn' ? toDeva(el.dataset.te) : el.dataset.te;
      el.classList.toggle('dn', sc === 'dn');
      el.classList.toggle('te', sc !== 'dn');
    });
    document.querySelectorAll('.script button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.script === sc));
    });
    try { localStorage.setItem('devataa-script', sc); } catch (e) {}
  }
  document.querySelectorAll('.script button').forEach(function (b) {
    b.addEventListener('click', function () { setScript(b.dataset.script); });
  });
  try { if (localStorage.getItem('devataa-script') === 'dn') setScript('dn'); } catch (e) {}

  // plate viewer
  var dlg = document.getElementById('plate');
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a.plate');
    if (!a || !dlg || !dlg.showModal) return;
    ev.preventDefault();
    dlg.querySelector('img').src = a.href;
    dlg.querySelector('img').alt = (a.querySelector('img') || {}).alt || '';
    dlg.showModal();
  });
  if (dlg) dlg.addEventListener('click', function (ev) { if (ev.target === dlg) dlg.close(); });

  // find
  var box = document.getElementById('find'), found = document.getElementById('found');
  var all = document.getElementById('all-results');
  if (!box) return;
  var norm = function (s) { return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); };
  if (!all) {   // a group page: filter the cards in place
    var cards = Array.prototype.slice.call(document.querySelectorAll('article.dv'));
    box.addEventListener('input', function () {
      var q = norm(box.value.trim()), n = 0;
      cards.forEach(function (c) {
        var hit = !q || norm(c.dataset.q).indexOf(q) >= 0;
        c.hidden = !hit; if (hit) n++;
      });
      document.querySelectorAll('section').forEach(function (s) {
        s.hidden = q && !s.querySelector('article.dv:not([hidden])');
      });
      found.hidden = !q;
      found.textContent = n ? n + ' of ' + cards.length + ' forms match.' : 'No form on this page matches "' + box.value + '".';
    });
    return;
  }
  // the index: search the whole registry
  var reg = null;
  box.addEventListener('focus', function load() {
    box.removeEventListener('focus', load);
    fetch('/devataa/data/devataa.json').then(function (r) { return r.json(); }).then(function (j) {
      reg = j; box.dispatchEvent(new Event('input'));
    }).catch(function () {
      found.hidden = false; found.textContent = 'The registry could not be loaded; open a group above instead.';
    });
  });
  box.addEventListener('input', function () {
    var q = norm(box.value.trim());
    all.innerHTML = '';
    if (!q) { found.hidden = true; return; }
    found.hidden = false;
    if (!reg) { found.textContent = 'Loading the registry…'; return; }
    var gname = {}; reg.groups.forEach(function (g) { gname[g.id] = g.iast; });
    var hits = reg.entries.filter(function (e) {
      return e.kind !== 'text' && norm([e.name_te, e.name_iast, e.name_en].join(' ')).indexOf(q) >= 0;
    });
    found.textContent = hits.length ? hits.length + ' forms match.' : 'No form matches "' + box.value + '".';
    hits.slice(0, 60).forEach(function (e) {
      var a = document.createElement('a');
      a.href = '/devataa/' + e.group + '.html#' + e.id;
      var im = e.images[0];
      a.innerHTML = (im ? '<img loading="lazy" alt="" src="/devataa/' + im.thumb + '">' : '') +
        '<span><span class="te"></span><br><span class="g"></span></span>';
      a.querySelector('.te').textContent = e.name_te || e.name_en || '';
      a.querySelector('.g').textContent = gname[e.group] + (e.num != null ? ' · ' + e.num : '') +
        (e.name_iast ? ' · ' + e.name_iast : '') + (e.shloka_te ? '' : ' · diagram only');
      all.appendChild(a);
    });
  });
})();
