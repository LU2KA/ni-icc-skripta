# NI-ICC – skripta (web)

Skripta k předmětu NI-ICC (Úvod do výpočetní složitosti, FIT ČVUT) psaná ve WooWoo a sestavovaná do webu
přes MkDocs Material, stejným postupem jako skripta NI-UMI. Hotový web je o složku výš:
`../skripta/html/index.html` (funguje i bez internetu včetně hledání), PDF verze `../skripta/NI-ICC_skripta.pdf`.

- `src/` – zdroj skript (jediný zdroj pravdy webu); kapitola = soubor `NN-…woo` + oddíly `NNa-…`, `NNb-…`
  - 01–13: převod LaTeXových skript `../latex-skripta/kapitoly/*.tex` (přednášky 1–6, prosemináře 1–6, cvičení 1–5)
  - 14–15: SAT a ILP v praxi (přednášky 7–8, proseminář 7, cvičení 7–8)
  - 16–19: přílohy A–D (zápočtový test a jak číst skripta, typové úlohy, ukázkový test s řešením, graf redukcí)
  - `NNz-ulohy-navic.woo` (01–15): oddíl „Úlohy navíc“ na konci každé kapitoly – 8 vyřešených úloh navíc, nejsou
    z předlohy ani ze zdrojů předmětu; pravidla v `PRAVIDLA.md`, oddíl 1
- `PRAVIDLA.md` – pravidla zápisu, štítky, převod rámečků a obrázků, kontroly
- `tools/build_web.sh` – sestaví celý web do `../skripta/html/`
- `tools/build_pdf.sh` – PDF verze do `../skripta/NI-ICC_skripta.pdf` (`tools/build_web.sh serve` = náhled na localhost)
- `tools/preview.sh NN` – kontrola a náhled jedné kapitoly do `.build/preview-NN/site/`
- `tools/woo2mkdocs.py` – převod `.woo` → MkDocs (čísluje kapitoly, definice, věty a obrázky; `!tikz:` → SVG)
- `tools/check_woo.py`, `tools/check_tikz.py`, `tools/check_web_math.py` – kontroly struktury, obrázků a vzorců
- `tools/tikz/` – preambule obrázků: `macros.tex` a `styles.tex` (z `../latex-skripta/preamble.tex` a `kapitoly/makra.tex`),
  `local-NN.tex` (makra jedné kapitoly)
- `tools/mkdocs/` – styly, skripty a MathJax webu (makra `\PP`, `\NP`, `\prob`, `\redp`… v `javascripts/mathjax-config.js`)
- `src/pojmy.yaml` + `tools/link_terms.py` – vyskakovací definice na webu: po sestavení obalí pojmy v textu a ve vzorcích
  odkazem a okénkem s definicí (`tools/mkdocs/javascripts/pojmy.js`); `build_web.sh serve` je nemá

Zdroje předmětu jsou v `../ni-icc/` (klon repozitáře předmětu, **jen ke čtení** – nic se tam nezapisuje,
necommituje ani nepushuje).

Sestavení potřebuje `python3` s PyMuPDF, `lualatex`, prostředí s MkDocs a pro kontrolu vzorců Google Chrome:

```
python3.11 -m venv .venv && .venv/bin/pip install mkdocs-material
tools/build_web.sh
```

Mezivýsledky jsou v `.build/` (dá se smazat, obrázky se pak přeloží znovu).
