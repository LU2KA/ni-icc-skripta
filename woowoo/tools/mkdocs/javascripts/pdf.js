// PDF verze skript: na papíře se nedá posouvat do strany, takže co je širší než sazební obrazec
// (tabulka, vysazený vzorec, dlouhý vzorec v textu), se po vysázení vzorců zmenší, aby se vešlo.
// Bez toho by Chrome při tisku zmenšil kvůli jediné široké tabulce celý dokument.
(function () {
  function inner(el) {      // šířka, kterou má obsah prvku k dispozici
    var cs = getComputedStyle(el);
    return el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  }
  function block(el) {      // nejbližší předek, který není řádkový
    for (var a = el.parentElement; a; a = a.parentElement) {
      var d = getComputedStyle(a).display;
      if (d !== "inline" && d !== "contents") return a;
    }
    return document.body;
  }
  function shrink(el, width, avail) {
    if (width > avail + 0.5) { el.style.zoom = (avail / width).toFixed(4); return 1; }
    return 0;
  }
  function fit() {
    var n = 0;
    document.querySelectorAll(".md-typeset table:not([class])").forEach(function (t) {
      var wrap = t.closest(".md-typeset__scrollwrap") || t;
      n += shrink(t, t.offsetWidth, inner(block(wrap)));
    });
    document.querySelectorAll(".md-typeset mjx-container").forEach(function (m) {
      if (m.closest("[style*='zoom']")) return;       // už zmenšeno s tabulkou
      var math = m.querySelector("mjx-math, svg");
      if (!math) return;
      var disp = m.getAttribute("display") === "true";
      var host = disp ? m.parentElement : block(m);
      var w = math.getBoundingClientRect().width;
      // vysazený vzorec o více řádcích (align) má šířku 100 % a skutečnou šířku hlídá přes min-width
      if (disp) w = Math.max(w, m.getBoundingClientRect().width, m.scrollWidth);
      n += shrink(m, w, inner(host));
    });
    // Vysoký rámeček (postup, typické chyby, definice pojmů) se smí zalomit: jinak celý odskočí na další
    // stránku a nechá za sebou i půl stránky prázdné. Nízké rámečky zůstávají vcelku.
    document.querySelectorAll(".md-typeset .admonition").forEach(function (a) {
      if (a.offsetHeight > 330) a.classList.add("woo-tall");
    });
    document.documentElement.setAttribute("data-woo-fit", String(n));
  }
  function start() {
    var fonts = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    var math = window.MathJax && MathJax.startup && MathJax.startup.promise ? MathJax.startup.promise : Promise.resolve();
    math.then(function () { return fonts; }).then(fit);
  }
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start);
})();
