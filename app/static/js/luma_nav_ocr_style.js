(function normalizeToOcrNav() {
  if (window.__lumaOcrNavApplied) return;
  window.__lumaOcrNavApplied = true;

  var style = document.createElement('style');
  style.textContent = [
    '.topbar{position:sticky;top:0;z-index:60;height:60px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;gap:18px;background:rgba(5,8,21,.96);border-bottom:1px solid rgba(255,255,255,.09);backdrop-filter:blur(16px)}',
    '.topbar a{color:inherit;text-decoration:none}',
    '.topbar .logo{display:flex;align-items:center;gap:10px;min-width:150px}',
    '.topbar .logo img{height:32px;object-fit:contain}',
    '.topbar .logo-name{font-family:"DM Serif Display",serif;color:#f5c86b;font-size:1.1rem;line-height:1}',
    '.topbar .logo-sub{font-size:.58rem;color:#94a3bd;letter-spacing:.08em;font-style:italic}',
    '.topbar .nav{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;justify-content:center;flex:1;min-width:0}',
    '.topbar .nav::-webkit-scrollbar{display:none}',
    '.topbar .npill{padding:6px 9px;border-radius:18px;font-size:.7rem;color:#94a3bd;white-space:nowrap;transition:.18s}',
    '.topbar .npill:hover{background:rgba(255,255,255,.04);color:#eef3ff}',
    '.topbar .npill.active{background:rgba(245,200,107,.14);color:#f5c86b}',
    '.topbar .nav-user{display:flex;align-items:center;gap:8px;font-size:.72rem;color:#94a3bd;min-width:130px;justify-content:flex-end}',
    '.topbar .nav-user-name{max-width:96px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#eef3ff}',
    '.topbar .nav-login-btn,.topbar .nav-logout{border:1px solid rgba(245,200,107,.3);background:rgba(245,200,107,.1);color:#f5c86b;padding:6px 13px;border-radius:18px;font-size:.74rem;white-space:nowrap}',
    '.topbar .nav-logout{border-color:rgba(255,141,141,.25);background:rgba(255,141,141,.08);color:#ff8d8d;border-radius:8px}',
    '@media(max-width:900px){.topbar{padding:0 16px}.topbar .nav{display:none}.topbar .nav-user{min-width:auto}}'
  ].join('\n');
  document.head.appendChild(style);

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, function(char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
    });
  }

  function readUser() {
    try {
      return JSON.parse(localStorage.getItem('luma_user') || '{}');
    } catch (error) {
      return {};
    }
  }

  function navItem(href, label, matcher) {
    var path = location.pathname;
    var active = matcher ? matcher(path) : path === href;
    return '<a href="' + href + '" class="npill' + (active ? ' active' : '') + '">' + label + '</a>';
  }

  function logout() {
    localStorage.removeItem('luma_token');
    localStorage.removeItem('luma_user');
    location.href = '/auth/login';
  }

  window.lumaNavLogout = logout;

  var token = localStorage.getItem('luma_token');
  var user = readUser();
  var label = user.display_name || user.nickname || user.name || user.email || '로그인 사용자';
  var authHtml = token
    ? '<span class="nav-user-name">' + escapeHtml(user.emoji || '✨') + ' ' + escapeHtml(label) + '</span><button type="button" class="nav-logout" onclick="lumaNavLogout()">로그아웃</button>'
    : '<a href="/auth/login" class="nav-login-btn">로그인</a>';

  var header = document.querySelector('header.topbar') || document.querySelector('.topbar') || document.querySelector('header');
  if (!header) {
    header = document.createElement('header');
    document.body.insertBefore(header, document.body.firstChild);
  }

  header.className = 'topbar';
  header.innerHTML = [
    '<a href="/" class="logo">',
      '<img src="/asset/images/Luma_logo_1.png" alt="LUMA">',
      '<div><div class="logo-name">LUMA</div><div class="logo-sub">문장이 빛이 되는 독서 지도</div></div>',
    '</a>',
    '<nav class="nav">',
      navItem('/', '별자리 지도'),
      navItem('/heart', '마음 행성계', function(path) { return path.indexOf('/heart') === 0; }),
      navItem('/lounge', '탐사 성운', function(path) { return path.indexOf('/lounge') === 0 || path.indexOf('/discover') === 0; }),
      navItem('/community/', '은하 공동체', function(path) { return path.indexOf('/community') === 0; }),
      navItem('/live', '궤도 정거장', function(path) { return path.indexOf('/live') === 0; }),
      navItem('/socrates', '지성의 위성', function(path) { return path.indexOf('/socrates') === 0; }),
      navItem('/social', '생각 피드', function(path) { return path.indexOf('/social') === 0; }),
      navItem('/deepdive', '심층 관측소', function(path) { return path.indexOf('/deepdive') === 0; }),
      navItem('/ocr', '광학 스캐너', function(path) { return path.indexOf('/ocr') === 0; }),
      navItem('/profile', '나의 조종석', function(path) { return path.indexOf('/profile') === 0; }),
    '</nav>',
    '<div class="nav-user" id="nav-user">' + authHtml + '</div>'
  ].join('');

  function removeDuplicateNavs() {
    var navWords = ['별자리 지도', '마음 행성계', '탐사 성운', '은하 공동체', '궤도 정거장', '지성의 위성', '생각 피드', '심층 관측소', '광학 스캐너', '나의 조종석'];
    Array.prototype.slice.call(document.querySelectorAll(
      'header, .topbar, .navbar, .nav-bar, .top-nav, .site-nav, .site-header, .app-header, .page-header, .global-header, [class*="navbar"], [class*="topbar"], [class*="header"], [class*="nav"]'
    )).forEach(function(node) {
      if (!node || node === header || header.contains(node) || node.contains(header)) return;
      if (node.tagName === 'BODY' || node.tagName === 'HTML') return;
      var rect = node.getBoundingClientRect();
      var text = (node.textContent || '').replace(/\s+/g, ' ');
      var hitCount = navWords.filter(function(word) { return text.indexOf(word) >= 0; }).length;
      var hasLumaNav =
        node.querySelector('.npill, .nav, .logo, .nav-user') ||
        text.indexOf('LUMA') >= 0 ||
        hitCount >= 2;
      if (hasLumaNav && rect.top < 180 && rect.height < 140) node.remove();
    });

    Array.prototype.slice.call(document.body.children).forEach(function(node) {
      if (!node || node === header || header.contains(node) || node.contains(header)) return;
      var rect = node.getBoundingClientRect();
      var text = (node.textContent || '').replace(/\s+/g, ' ');
      var hitCount = navWords.filter(function(word) { return text.indexOf(word) >= 0; }).length;
      var looksLikeDuplicateNav = rect.top < 180 && rect.height < 160 && (text.indexOf('LUMA') >= 0 || hitCount >= 2);
      if (looksLikeDuplicateNav) node.remove();
    });
  }

  removeDuplicateNavs();
  requestAnimationFrame(removeDuplicateNavs);
  setTimeout(removeDuplicateNavs, 300);
  window.addEventListener('load', removeDuplicateNavs, { once: true });
})();
