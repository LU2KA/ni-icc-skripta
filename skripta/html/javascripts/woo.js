// Tlačítko "Rozbalit všechna řešení / důkazy" na stránkách, kde nějaké rozbalovací rámečky jsou.
(function () {
  function init() {
    var sols = Array.prototype.slice.call(document.querySelectorAll("details.woo-solution, details.woo-proof"));
    var nSol = document.querySelectorAll("details.woo-solution").length, nPf = sols.length - nSol;
    var whatAll = nSol && nPf ? "všechna řešení a důkazy" : nPf ? "všechny důkazy" : "všechna řešení";
    var h1 = document.querySelector(".md-content__inner h1");
    if (!sols.length || !h1) return;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "woo-toggle";
    function allOpen() { return sols.every(function (d) { return d.open; }); }
    function label() {
      var open = allOpen();
      btn.textContent = open ? "Sbalit " + whatAll : "Rozbalit " + whatAll + " (" + sols.length + ")";
      btn.setAttribute("aria-pressed", open ? "true" : "false");
    }
    btn.addEventListener("click", function () {
      var open = !allOpen();
      sols.forEach(function (d) { d.open = open; });
      label();
    });
    sols.forEach(function (d) { d.addEventListener("toggle", label); });
    label();
    h1.insertAdjacentElement("afterend", btn);
  }
  // Odkaz může mířit na tabulku nebo vzorec uvnitř sbaleného řešení (nebo na sbalený důkaz): rozbal ho.
  function reveal() {
    var id = decodeURIComponent(location.hash.slice(1));
    var el = id && document.getElementById(id);
    if (!el) return;
    var opened = false;
    for (var d = el.closest("details"); d; d = d.parentElement && d.parentElement.closest("details")) {
      if (!d.open) { d.open = true; opened = true; }
    }
    if (opened) el.scrollIntoView();
  }
  // Světlý / tmavý režim se u webu otevřeného ze souboru přenáší v odkazech (?mode=dark / ?mode=light),
  // protože některé prohlížeče tam mají úložiště pro každou stránku zvlášť (viz overrides/main.html).
  function mode() { return document.body.getAttribute("data-md-color-scheme") === "slate" ? "dark" : "light"; }
  function carry(a) {
    var raw = a.getAttribute("href");
    if (!raw || raw.charAt(0) === "#") return;
    var u;
    try { u = new URL(a.href); } catch (e) { return; }
    if (u.protocol !== "file:" || !/\.html$/.test(u.pathname) || u.pathname === location.pathname) return;
    if (u.searchParams.get("mode") === mode()) return;
    u.searchParams.set("mode", mode());
    a.href = u.href;
  }
  function carryAll() { Array.prototype.forEach.call(document.querySelectorAll("a[href]"), carry); }
  function theme() {
    if (location.protocol !== "file:") return;      // na serveru stačí úložiště prohlížeče
    // úložiště nedostupné: režim z adresy se nastaví až teď přepínačem motivu
    var want = new URLSearchParams(location.search).get("mode");
    var nav = performance.getEntriesByType && performance.getEntriesByType("navigation")[0];
    if ((want === "dark" || want === "light") && want !== mode() && !(nav && nav.type === "reload")) {
      var input = document.getElementById(want === "dark" ? "__palette_1" : "__palette_0");
      if (input) { input.checked = true; input.dispatchEvent(new Event("change", { bubbles: true })); }
    }
    carryAll();
    new MutationObserver(carryAll).observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
    // odkazy vzniklé později (výsledky hledání) se doplní při kliknutí
    ["click", "auxclick"].forEach(function (ev) {
      document.addEventListener(ev, function (e) {
        var a = e.target && e.target.closest && e.target.closest("a[href]");
        if (a) carry(a);
      }, true);
    });
  }
  function start() { init(); reveal(); theme(); }
  window.addEventListener("hashchange", reveal);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
