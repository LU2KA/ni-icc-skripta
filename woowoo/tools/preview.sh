#!/bin/sh
# Kontrola a náhled jedné nebo několika kapitol (nezasahuje do ostatních, dá se pouštět souběžně):
#   tools/preview.sh 04          soubory src/04*.woo
#   tools/preview.sh 14,15       víc kapitol naráz
# Udělá: check_woo (struktura), check_tikz (obrázky), check_tikz --math (vzorce a pseudokód v LaTeXu),
# náhled webu do .build/preview-NN/site/ a kontrolu vzorců MathJaxu v prohlížeči (check_web_math).
# Na konci vypíše, kde náhled je. Návratový kód 0 = bez chyb.
cd "$(dirname "$0")/.."
[ -n "$1" ] || { echo "použití: tools/preview.sh NN[,NN...]"; exit 2; }
MKDOCS="${MKDOCS:-.venv/bin/mkdocs}"
FILES=""
for n in $(echo "$1" | tr ',' ' '); do FILES="$FILES $(ls src/${n}*.woo 2>/dev/null)"; done
[ -n "$(echo $FILES)" ] || { echo "žádné soubory src/$1*.woo"; exit 2; }
TAG=$(echo "$1" | tr ',' '-')
RC=0
echo "== check_woo";  python3 tools/check_woo.py $FILES || RC=1
echo "== check_tikz"; python3 tools/check_tikz.py $FILES || RC=1
echo "== check_tikz --math"; python3 tools/check_tikz.py --math $FILES || RC=1
echo "== woo2mkdocs --only=$1"; python3 tools/woo2mkdocs.py --only="$1" || RC=1
NO_MKDOCS_2_WARNING=1 "$MKDOCS" build -q -f ".build/preview-$TAG/mkdocs/mkdocs.yml" || RC=1
if [ "$2" != "nomath" ]; then
  echo "== check_web_math"; python3 tools/check_web_math.py ".build/preview-$TAG/site" || RC=1
fi
echo "náhled: $PWD/.build/preview-$TAG/site/index.html   (návratový kód $RC)"
exit $RC
