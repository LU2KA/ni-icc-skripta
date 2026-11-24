// Vyskakovací definice: po najetí myší (nebo klepnutí na dotykovém displeji) na pojem nebo odkaz na rámeček
// ukáže jeho definici. Data (window.WOO_POJMY) a odkazy v textu doplňuje tools/link_terms.py po sestavení webu.
(function () {
  var DATA = window.WOO_POJMY;
  if (!DATA) return;
  var me = document.currentScript && document.currentScript.src;
  var ROOT = me ? me.replace(/javascripts\/pojmy\.js(\?.*)?$/, "") : "";
  var touch = window.matchMedia && window.matchMedia("(hover: none)").matches;
  var pop = null, cur = null, showT = 0, hideT = 0, built = {};

  function keyOf(el) {
    if (!el || !el.closest) return null;
    if (pop && pop.contains(el)) return null;
    var t = el.closest("[data-pojem]");
    if (t) return { el: t, key: t.getAttribute("data-pojem") };
    var g = el.closest("[class*='woo-pk-']");
    if (g) {
      var m = /(?:^|\s)woo-pk-(\S+)/.exec(g.getAttribute("class"));
      if (m && DATA[m[1]]) return { el: g.closest("a") || g, key: m[1] };
    }
    var a = el.closest("a[href*='#']");
    if (a && a.closest(".md-content")) {
      var h = decodeURIComponent((a.getAttribute("href") || "").split("#")[1] || "");
      if (DATA[h]) return { el: a, key: h };
    }
    return null;
  }

  function fix(s) { return s.replace(/@R\//g, ROOT); }

  function content(key) {
    if (built[key]) return built[key];
    var d = DATA[key], box = document.createElement("div");
    box.className = "woo-pojem-in";
    var html = (d.t ? '<p class="woo-pojem-title">' + fix(d.t) + "</p>" : "") + fix(d.b);
    if (d.u) html += '<p class="woo-pojem-go"><a href="' + fix(d.u) + '">Otevřít ve skriptech →</a></p>';
    box.innerHTML = html;
    built[key] = box;
    return box;
  }

  function place(anchor) {
    var r = anchor.getBoundingClientRect(), vw = document.documentElement.clientWidth;
    var vh = window.innerHeight, w = pop.offsetWidth, h = pop.offsetHeight, gap = 8;
    var left = Math.max(gap, Math.min(r.left, vw - w - gap));
    var top = r.bottom + gap;
    if (top + h > vh - gap && r.top - h - gap > gap) top = r.top - h - gap;
    pop.style.left = left + window.scrollX + "px";
    pop.style.top = top + window.scrollY + "px";
  }

  function show(hit) {
    clearTimeout(hideT);
    if (!pop) {
      pop = document.createElement("div");
      pop.className = "woo-pojem md-typeset";
      pop.setAttribute("role", "tooltip");
      pop.addEventListener("mouseenter", function () { clearTimeout(hideT); });
      pop.addEventListener("mouseleave", hideSoon);
      document.body.appendChild(pop);
    }
    var box = content(hit.key);
    if (pop.firstChild !== box) { pop.textContent = ""; pop.appendChild(box); }
    cur = hit;
    pop.classList.add("woo-pojem--on");
    place(hit.el);
    if (!box.getAttribute("data-mj") && window.MathJax && MathJax.typesetPromise) {
      box.setAttribute("data-mj", "1");
      MathJax.typesetPromise([box]).then(function () { if (cur === hit) place(hit.el); });
    }
  }

  function hide() { if (pop) pop.classList.remove("woo-pojem--on"); cur = null; }
  function hideSoon() { clearTimeout(showT); clearTimeout(hideT); hideT = setTimeout(hide, 250); }

  document.addEventListener("mouseover", function (e) {
    if (touch) return;
    var hit = keyOf(e.target);
    if (!hit) return;
    clearTimeout(hideT);
    if (cur && cur.el === hit.el) return;
    clearTimeout(showT);
    showT = setTimeout(function () { show(hit); }, cur ? 80 : 300);
  });
  document.addEventListener("mouseout", function (e) {
    if (touch) return;
    var hit = keyOf(e.target);
    if (hit && !(e.relatedTarget && hit.el.contains(e.relatedTarget))) hideSoon();
  });
  document.addEventListener("focusin", function (e) {
    var hit = keyOf(e.target);
    if (hit) show(hit);
  });
  document.addEventListener("focusout", function (e) { if (keyOf(e.target)) hideSoon(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") hide(); });

  // Dotyk: první klepnutí na pojem ukáže okénko, odkaz „Otevřít ve skriptech“ v něm vede na definici.
  // Pojem bez místa ve skriptech (jen okénko) se neotevírá ani myší.
  document.addEventListener("click", function (e) {
    var hit = keyOf(e.target);
    if (!hit) { if (pop && !pop.contains(e.target)) hide(); return; }
    if (!hit.el.closest("a[href]")) { e.preventDefault(); show(hit); return; }
    if (touch && !(cur && cur.el === hit.el)) { e.preventDefault(); show(hit); }
  });
  window.addEventListener("resize", hide);

  // Pojmy ve vzorcích: MathJax kreslí SVG, kde text-decoration nefunguje – tečkovanou čáru pod každý
  // odkaz dokreslíme sami (souřadnice uvnitř vzorce: 1000 jednotek = 1 em, osa y míří nahoru).
  // Vzorce ve sbaleném řešení nemají rozměry, ty se podtrhnou až po rozbalení.
  var SVGNS = "http://www.w3.org/2000/svg";
  function underline(root) {
    var links = (root || document).querySelectorAll("mjx-container[jax='SVG'] a:not([data-ul])");
    Array.prototype.forEach.call(links, function (a) {
      var bb;
      try { bb = a.getBBox(); } catch (e) { return; }
      if (!bb.width) return;
      var y = Math.min(bb.y - 40, -110);
      var line = document.createElementNS(SVGNS, "line");
      line.setAttribute("x1", bb.x);
      line.setAttribute("x2", bb.x + bb.width);
      line.setAttribute("y1", y);
      line.setAttribute("y2", y);
      line.setAttribute("stroke-width", "45");
      line.setAttribute("stroke-dasharray", "45 75");
      line.setAttribute("class", "woo-ul");
      a.appendChild(line);
      a.setAttribute("data-ul", "1");
    });
  }
  if (window.MathJax && MathJax.startup && MathJax.startup.promise) {
    MathJax.startup.promise.then(function () { underline(); });
  }
  document.addEventListener("toggle", function (e) { if (e.target.open) underline(e.target); }, true);
})();
