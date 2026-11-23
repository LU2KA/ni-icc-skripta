#!/bin/sh
# Sestaví web skript (MkDocs Material) z .woo souborů.
#   tools/build_web.sh          výstup: ../skripta/html/index.html (jinam: SKRIPTA_OUT=/cesta)
#   tools/build_web.sh serve    sestaví a spustí náhled na http://127.0.0.1:8000 (při změně .woo spusť znovu)
# Potřebuje: python3 s PyMuPDF, lualatex (obrázky TikZ) a .venv s mkdocs-material
#   (python3.11 -m venv .venv && .venv/bin/pip install mkdocs-material).
# Mezivýsledky jdou do .build/ (dá se kdykoli smazat, jen se pak obrázky překládají znovu).
set -e
cd "$(dirname "$0")/.."
OUT="${SKRIPTA_OUT:-$(cd .. && pwd)/skripta}"
# main.woo je páteř pro builder woo (.include v pořadí kapitol); web bere pořadí přímo ze jmen souborů
ls src/*.woo | sed 's/^/.include /' > main.woo
python3 tools/woo2mkdocs.py
if [ "$1" = "serve" ]; then
  NO_MKDOCS_2_WARNING=1 .venv/bin/mkdocs serve -f .build/mkdocs/mkdocs.yml
else
  NO_MKDOCS_2_WARNING=1 .venv/bin/mkdocs build -q -f .build/mkdocs/mkdocs.yml
  echo "web: $OUT/html/index.html"
fi
