#!/bin/sh
# Sestaví PDF verzi skript: z .woo souborů udělá jednu dlouhou stránku (MkDocs Material, stejný vzhled
# jako web, řešení rozbalená) a Chrome ji vytiskne do PDF formátu A4 se záložkami a čísly stránek.
#   tools/build_pdf.sh          výstup: ../skripta/NI-ICC_skripta.pdf (jinam: SKRIPTA_OUT=/cesta)
# Potřebuje totéž co tools/build_web.sh a navíc Google Chrome (jinde než ve výchozím umístění: CHROME=/cesta).
set -e
cd "$(dirname "$0")/.."
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUT="${SKRIPTA_OUT:-$(cd .. && pwd)/skripta}"
PDF="$OUT/NI-ICC_skripta.pdf"
mkdir -p "$OUT" .build/chrome
python3 tools/woo2mkdocs.py --pdf
NO_MKDOCS_2_WARNING=1 .venv/bin/mkdocs build -q -f .build/mkdocs-pdf/mkdocs.yml
# Okno 666 px = šířka sazebního obrazce (A4 s okraji 64 px, viz pdf.css); --virtual-time-budget nechá doběhnout MathJax.
"$CHROME" --headless=new --disable-gpu --no-first-run --user-data-dir="$PWD/.build/chrome" \
  --window-size=666,900 --no-pdf-header-footer --generate-pdf-document-outline \
  --virtual-time-budget=600000 --print-to-pdf="$PDF" "file://$PWD/.build/site-pdf/index.html" 2>/dev/null
rm -rf .build/chrome          # dočasný profil prohlížeče
python3 tools/check_pdf.py "$PDF"
echo "pdf: $PDF"
