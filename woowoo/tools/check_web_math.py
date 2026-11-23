#!/usr/bin/env python3
"""Kontrola vzorců na hotovém webu: každou stránku otevře v Chrome bez okna a spočítá chyby MathJaxu
a vzorce, které zůstaly nevysázené.

Použití: python3 tools/check_web_math.py [složka webu]
"""
import pathlib
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

SITE = pathlib.Path(__file__).resolve().parents[2] / "skripta" / "html"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PARALLEL = 6


def run(job):
    slot, page, prof = job
    try:
        r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
                            f"--user-data-dir={prof}/p{slot}", "--window-size=1300,900",
                            "--virtual-time-budget=25000", "--dump-dom", page.as_uri()],
                           capture_output=True, text=True, timeout=180, errors="replace")
    except subprocess.TimeoutExpired:
        return page, None, None, None
    dom = r.stdout
    return (page, dom.count("<mjx-container"), re.findall(r'data-mjx-error="([^"]*)"', dom),
            len(re.findall(r'class="arithmatex">\\[(\[]', dom)))


def main():
    site = (pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else SITE).resolve()
    pages = sorted(p for p in site.rglob("*.html") if p.name != "404.html")
    total = errors = raw_total = timeouts = 0
    with tempfile.TemporaryDirectory() as prof:
        for k in range(0, len(pages), PARALLEL):          # jeden profil Chrome nesmí běžet dvakrát naráz
            batch = [(i, p, prof) for i, p in enumerate(pages[k:k + PARALLEL])]
            with ThreadPoolExecutor(PARALLEL) as ex:
                results = list(ex.map(run, batch))
            for page, n, errs, raw in results:
                if n is None:                              # druhý pokus sám, bez souběhu
                    page, n, errs, raw = run((0, page, prof))
                if n is None:
                    timeouts += 1
                    print("NEDOBĚHLO", page.relative_to(site))
                    continue
                total += n
                if raw:
                    raw_total += raw
                    print("NEVYSÁZENO", page.relative_to(site), raw)
                for e in errs:
                    errors += 1
                    print("CHYBA", page.relative_to(site), e[:120])
    print(f"stránek {len(pages)}, vysázených vzorců {total}, chyb MathJaxu {errors}, "
          f"nevysázených {raw_total}, nedoběhlo {timeouts}")
    return 1 if errors or raw_total or timeouts else 0


if __name__ == "__main__":
    sys.exit(main())
