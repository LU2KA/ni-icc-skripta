# NI-ICC skripta ve WooWoo: architektura a pravidla zápisu

Závazná pravidla pro soubory `src/*.woo` (dialekt WooWoo **FIT Math**). Web z nich dělá `tools/woo2mkdocs.py`
(MkDocs Material, stejný vzhled jako skripta NI-UMI). Původní LaTeXová skripta jsou v `../latex-skripta/`
(`main.tex`, `preamble.tex`, `kapitoly/*.tex`) a slouží jako předloha; zdroje předmětu (jen ke čtení!) jsou
v `../ni-icc/` (`lectures/files/NI-ICC-pNN.pdf`, `NI-ICC-prosemNN.pdf`, `tutorials/files/NI-ICC-cvNN.pdf`,
`files/ukazkovy-test.pdf`, `classification.adoc`). **Do `../ni-icc/` ani do `../latex-skripta/` se nic nezapisuje;** `../skripta/` obsahuje jen hotový web `html/`
a `NI-ICC_skripta.pdf` (stejně jako skripta NI-UMI), píšou je `tools/build_web.sh` a `tools/build_pdf.sh`.

Cíl převodu z LaTeXu: **stejný obsah, žádné krácení, žádné vymýšlení**. Mění se jen značkování.

---

## 1. Architektura

```
woowoo/
  PRAVIDLA.md             tento soubor
  src/NN-jmeno.woo        hlavička kapitoly: řádek .Chapter, úvod kapitoly (stránka kapitoly na webu)
  src/NNa-jmeno.woo …     oddíly kapitoly, jeden soubor = jeden .Section = jedna stránka webu
  figures/                rastrové obrázky (.image:), např. výřezy ze slajdů
  tools/tikz/macros.tex   barvy a matematická makra skript (\PP, \NP, \prob, \redp, \enc, …) – NEMĚNIT
  tools/tikz/styles.tex   globální styly a makra obrázků (cell, st, v, e, blok…, \tmtape, \chRtile, \chZpig…) – NEMĚNIT
  tools/tikz/local-NN.tex makra a styly obrázků jedné kapitoly (NN = číslo souboru); vlastní si každá kapitola sama
  tools/preview.sh NN     kontrola + náhled kapitoly NN (viz oddíl 4)
  tools/build_web.sh      celý web do ../skripta/html/
  tools/build_pdf.sh      PDF verze do ../skripta/NI-ICC_skripta.pdf
```

Pořadí v knize = abecední pořadí jmen souborů (`04-…` < `04a-…` < `04b-…` < `05-…`). Tři úrovně:
`.Chapter` (složka webu) > `.Section` (stránka) > `.Subsection` (nadpis na stránce). Čtvrtá úroveň neexistuje:
`\subsubsection` a `\paragraph{X}` jsou odstavec začínající `"X.".notion`.

| záložka webu | soubory | kapitola |
|---|---|---|
| Model a vyčíslitelnost | `01-…`, `02-…` | Problémy a Turingův stroj; Vyčíslitelnost |
| Časová složitost | `03-…`, `04-…` | Třídy P a EXP; Nedeterminismus a třída NP |
| NP-úplnost | `05-…` až `11-…` | Redukce a NP-úplnost; Cook–Levin; Varianty SAT; IS/VC/Clique; Barvení, řezy, MAPF; Přesná pokrytí; Cesty, ILP, čísla |
| Prostorová složitost | `12-…`, `13-…` | Prostorová složitost; PSPACE-úplnost a hry |
| SAT a ILP v praxi | `14-…`, `15-…` | SAT: algoritmy, kódování, řešiče (př. 7); (I)LP: modelování a řešiče (př. 8) |
| Test a přehledy (přílohy A–D) | `16-…` až `19-…` | A Zápočtový test a jak číst skripta; B Typové úlohy; C Ukázkový test; D Graf všech redukcí |

**Hlavička kapitoly** (`NN-jmeno.woo`): řádek `.Chapter Název` se štítkem, první odstavec `Zdroje: přednáška N, proseminář N, cvičení N.`,
pak rámeček `.Concept:` s `title: 'Proč to děláme'` (3–5 konkrétních vět: jaký problém kapitola řeší a jak navazuje
na předchozí; vyjdi z úvodu kapitoly v předloze, nic nevymýšlej), pak zbytek úvodu kapitoly z předlohy (text před
první `\section`). Každý `\section` je vlastní soubor `NNa-`, `NNb-`, … v pořadí předlohy; `\section*{Shrnutí kapitoly}`
je poslední oddíl `.Section Shrnutí kapitoly`. Krátké jméno souboru bez diakritiky (`08b-anatomie-redukci.woo`).

**Látka z proseminářů.** Jádrem skript jsou přednášky; proseminář je obvykle rozšíření. Oddíl nebo pododdíl převzatý
z prosemináře má v nadpisu `(proseminář N)` a hned za nadpisem (u celé kapitoly za rámečkem „Proč to děláme“) rámeček
`.Remark:` s titulkem `'Rozšíření z prosemináře N'`, nebo `'Z prosemináře N: na test potřeba'`, když je látka povinná
(typová úloha testu, problém, který přednáška bere jako známý). Ve 2–3 větách řekne, co v oddílu je, že jde
o rozšíření nad přednášku, a co z toho je potřeba na test (nebo že nic). Řádek `Zdroje:` uvádí proseminář jako
„navíc“; úvod kapitoly a „Co si odnést“ ho jako jádro nestaví. Totéž platí pro budoucí prosemináře.

**Úlohy navíc** (`NNz-ulohy-navic.woo`, kapitoly 01–15): za shrnutím kapitoly následuje oddíl `.Section Úlohy navíc`
se štítkem `<štítek kapitoly>-ulohy-navic` – osm úplně vyřešených úloh nad rámec cvičení (nejsou v LaTeXové předloze
ani ve zdrojích předmětu). Stavba: úvodní odstavec, `.Warning:` s `title: 'Neoficiální úlohy'`, pododdíly
`Rozcvička` / `Základní úlohy` / `Těžší úlohy` (štítky `<štítek kapitoly>-ulohy-navic-…`) a případně
`Úlohy z jiných sbírek` (`…-ulohy-navic-sbirka`: převzatá zadání s uvedeným zdrojem, naše řešení, čísla N.9 dál –
stávající čísla úloh se nepřečíslovávají). Úloha je dvojice
`.Exercise:` (`title: 'Úloha N.k (název)'`, `label: un-N-k`, N = číslo kapitoly) + `.Solution:`; řešení s redukcí má
`label: red-un-N-k` a začíná hlavičkou redukce (2.10). Obrázky `filename: NNz-ulohy-navic-01`, … Typové úlohy
v příloze B (`17a`–`17d`) se číslují `'Typová úloha T.k [6 bodů]'`, `label: typ-T-k`, řešení typu 4 `red-typ-4-k`.
Nová redukce se zapíše i do tabulky „Redukce z úloh navíc a z typových úloh“ v `19a-prehled-redukci.woo`, úloha
blízká některému typu testu do tabulky `tab-test-ulohy-navic` v `16a-jak-cist.woo` a do seznamu „Kde to ve skriptech
je“ v příslušném `17x`. Platí pravidla oddílu 3: každé číslo ověřit skriptem, co není z přednášky, označit.

### Štítky (label)

Každá `.Chapter`, `.Section`, `.Subsection` **musí** mít `label`. Povolené znaky `a–z`, `0–9`, `-`. Štítky jsou jedinečné
v celé knize. Štítek z LaTeXu se převádí **mechanicky** (malá písmena; `:`, `.`, `_` → `-`), takže odkazy mezi kapitolami
sedí, i když je píše někdo jiný:

| LaTeX | WooWoo |
|---|---|
| `\label{ch:np}`, `\label{sec:cv3}`, `\label{fig:grafredukci}` | `ch-np`, `sec-cv3`, `fig-grafredukci` |
| `\begin{definice}{T}{nphard}` (štítek `def:nphard`) | `.Definition:` se `label: def-nphard` |
| `veta` → `thm:x`, `lemma` → `lem:x`, `dusledek` → `cor:x`, `problem` → `prob:x`, `priklad` → `ex:x` | `thm-x`, `lem-x`, `cor-x`, `prob-x`, `ex-x` |
| `\redukce[is]{…}`, `\redukceor[tspopt]{…}`, `\hypertarget{red:mario}{}` | štítek `red-is`, `red-tspopt`, `red-mario` (viz 2.10) |
| `\begin{cviceni}{3.2}` | `.Exercise:` se `label: cv-3-2` (cvičení 3, úloha 2) |

Kde předloha štítek nemá (většina oddílů), vymysli ho: `<štítek kapitoly>-<slug nadpisu bez diakritiky>`,
např. `ch-is-anatomie-redukci`. Vymyšlené štítky proto vždy začínají štítkem vlastní kapitoly a nemohou se srazit.
Prázdný druhý argument rámečku (`\begin{veta}{T}{}`) a hvězdičková varianta (`definice*`) = bez štítku
(hvězdičková navíc s `nonumber: true`).

---

## 2. Syntaxe

### 2.1 Bloky a prázdné řádky

- **Dva prázdné řádky** oddělují bloky (odstavce a objekty) na nejvyšší úrovni a přímo v těle objektu.
  **Jeden prázdný řádek** odděluje části téhož bloku (text, vnější prostředí, další text) a odstavce uvnitř
  vnějších prostředí (`.item:`, `.row:` …) – tam dva prázdné řádky být nesmí.
- Odsazení vždy **2 mezery na úroveň**, žádné tabulátory. Pokračovací řádky odstavce se neodsazují víc.
- Meta-blok (YAML) je hned na dalším řádku po hlavičce, odsazený o 2 mezery; mezi ním a tělem jeden prázdný řádek.
  Před `.Chapter/.Section/.Subsection` i za jejich meta-blokem jsou dva prázdné řádky.
- Řádek textu nesmí začínat znakem `.`, `!` ani `* `.

```
.Section Nezávislá množina
  label: ch-is-nezavisla-mnozina


První odstavec. Pokračuje na dalším řádku
bez odsazení.


Druhý odstavec s rovnicí uprostřed

.equation:

  \sum_{i=1}^{n} x_i \le k

a pokračováním téhož odstavce.


.Definition:
  title: 'Dobře formulovaná úloha'
  label: def-uloha

  Tělo objektu je odsazené o 2 mezery.

  .itemize:

    .item:

      "počáteční stav".notion (např. $q_0$),

    .item:

      první odstavec položky.

      Druhý odstavec téže položky (jeden prázdný řádek).


  Druhý odstavec uvnitř objektu (dva prázdné řádky).
```

### 2.2 Objekty (velké písmeno) se nevnořují

`.Definition:`, `.Theorem:`, `.Lemma:`, `.Corollary:`, `.Proof:`, `.Example:`, `.Exercise:`, `.Solution:`, `.Remark:`,
`.Warning:`, `.Procedure:`, `.Concept:`, `.Question:`, `.Algorithm:`, `.Figure:`, `.Table:` stojí vždy **na nejvyšší
úrovni** (odsazení 0) a nikdy uvnitř jiného objektu. Uvnitř objektu smí být jen text a prostředí s malým písmenem
(`.itemize:`, `.enumerate:`, `.description:`, `.table:`, `.equation:`, `.align:`, `.gather:`, `.centered:`, `.image:`,
`!tikz:`, `!pseudocode:`, `!codeblock:`). Když předloha rámečky vnořuje (příklad v řešení, obrázek s popiskem
v rámečku), vnitřní rámeček se rozpustí: tučný úvod `"Příklad.".notion` a text; obrázek jako `.centered:` + `!tikz:`
a popisek jako odstavec pod ním.

### 2.3 Text se escapuje, LaTeX v textu není

Mimo matematiku (`$…$`, `.equation:`) a mimo `!tikz:`, `!pseudocode:`, `!codeblock:` **nesmí být žádný LaTeXový příkaz**.

| LaTeX v textu | WooWoo |
|---|---|
| `\textbf{X}` | `"X".notion` |
| `\emph{X}`, `\textit{X}` | `"X".emphasize` |
| `\texttt{X}` | `"X".code` |
| `\uv{X}`, ``` ``X'' ``` | `„X“` (české uvozovky jako znaky) |
| `\prob{3-SAT}` v textu | `$\prob{3-SAT}$` (vždy v matematice) |
| `\NP`, `\PP`, `\EXP`, `\PSPACE`, `\NL`, `\coNP`… v textu | `$\NP$`, `$\PP$`, … |
| `\ANO`, `\NE`, `\enc{M}`, `\blank`, `\qA`, `\qR` v textu | `$\ANO$`, `$\NE$`, `$\enc{M}$`, `$\blank$`, `$\qA$`, `$\qR$` |
| `--`, `---` | `–`, `—` |
| `např.\ `, `\ `, `\,`, `\-` | mezera / nic; `~` smí zůstat (nedělitelná mezera) |
| `\dots`, `\ldots` v textu | `…` |
| `\%`, `\&`, `\#`, `\_` | `%`, `&`, `#`, `_`; literál `$` → `\$` |
| `\\` (zalomení řádku) | samostatné odstavce nebo seznam |
| `\textcolor{c}{X}` v textu, `\faXxx` ikony, `\small`, `\noindent`, `\centering`, `\vspace`, `\medskip`, `\hfill`, `\clearpage` | barvu / příkaz vypustit, text ponechat |
| symboly `\to`, `\Rightarrow`, `\checkmark`, `\times`, `\le` v textu | v matematice: `$\to$`, `$\Rightarrow$`… |
| `\footnote{X}` | `"X".footnote` |
| inline `\tikz …` v textu | nahraď slovem / symbolem v matematice, nebo samostatným `!tikz:` |

- Znak `"` (ASCII uvozovka) je syntaxe, v textu smí být **jen** jako ohraničení vnitřního prostředí.
- Vnitřní prostředí se nevnořují (`\textbf{\emph{X}}` → `"X".notion`); matematika uvnitř smí být (`"stav $q_0$".notion`).
  Odkaz uvnitř `"…".emphasize` nepiš.
- V `"…".code` není matematika.

### 2.4 Matematika

- Řádková `$…$`; vysazená (`\[ \]`, `$$`, `equation*`) je `.equation:`, `align*` → `.align:`, `gather*` → `.gather:`
  (jen obsah, bez `\begin`/`\end`).
- **Makra skript zůstávají** (zná je MathJax i kontrola): `\PP \NP \NPhat \EXP \NEXP \DTIME \NTIME \DSPACE \NSPACE
  \PSPACE \NPSPACE \LL \NL \coNP \coNL \cls{X} \redp \enc{x} \prob{Název} \qA \qR \qhalt \blank \Sig \N \Lft \Rgt
  \Stay \ANO \NE \dist \polylog`. Jiné vlastní makro (`\newcommand` v předloze) rozepiš.
- Barva: `\textcolor{acc}{x}` zůstává (jména barev skript `defc thmc exc intc warnc sumc cvc solc acc rej hl tT tF tB gr`
  i výrazy `defc!70!black` převodník přeloží).
- `\text{…}` ponech, `\mbox` → `\text`, `\textsc{X}` → `\prob{X}` nebo `\mathrm{X}`. V matematice nesmí být `\ref`, `\uv`,
  `\ensuremath`, `\label`.
- Nadpis s matematikou (`.Section $\prob{3-SAT}\redp\prob{IS}$`) je v pořádku; kdyby byl text v navigaci nečitelný,
  přidej meta `pdf_string: '3-SAT ≤p IS'`.

### 2.5 Seznamy

```
.enumerate:
  type: a

  .item:

    První položka.

  .item:
    bullet: '(iii)'

    Položka s vlastní značkou.
```

`itemize` → `.itemize:`, `enumerate` → `.enumerate:` (`type: a` pro a., b., c.), `description` → `.description:` s `.ditem:`
(`bullet: 'Pojem:'` je povinný). Vnořený seznam je prostředí uvnitř `.item:` (o další 2 mezery).

### 2.6 Tabulky

Vždy `.table:`; každý řádek `.row:`, **každá buňka je jeden řádek textu**, buňky odděluje jeden prázdný řádek.

```
.table:
  columns: 'lcp{4cm}'

  .row:
    head: true

    problém

    třída

    poznámka

  .row:

    $\prob{2-SAT}$

    $\NL$

    implikační graf
```

- `columns` je specifikace sloupců LaTeXu v jednoduchých uvozovkách (`l`, `c`, `r`, `p{4cm}`); `@{}`, `>{…}` vypusť.
  Počet buněk v každém řádku = počet sloupců. Prázdná buňka: `~`. Tabulka bez hlavičky: meta `noheader: true`.
- `\multicolumn{n}{…}{X}`: `X` do první buňky, do zbylých `~`. `\midrule`, `\rowcolor`, `\cline` vypusť.
- `.table:` se neobaluje do `.centered:`. `longtable` i `landscape` jsou obyčejná `.table:`.
- Tabulka s popiskem (`table` + `\caption`) je objekt `.Table:` na nejvyšší úrovni: uvnitř `.table:` a `.caption:`, štítek `tab-…`.

### 2.7 Obrázky TikZ

Každý `!tikz:` se překládá **samostatně** lualatexem (třída `standalone`, 11pt) s preambulí
`tools/tikz/macros.tex` + `tools/tikz/styles.tex` + `tools/tikz/local-NN.tex`. Globální styly skript
(`cell`, `st`, `stacc`, `v`, `vsel`, `e`, `blok`, `blokd`, `flow`, `note`, `chRlit`, `chZv`…), barvy a makra
(`\tmtape`, `\chRtile`, `\chZpig`, `\chZcross`, `\prob`, `\NP`…) tedy **fungují beze změny**. Knihovny: arrows.meta,
positioning, automata, calc, fit, backgrounds, shapes.geometric, shapes.misc, shapes.multipart,
decorations.pathreplacing/markings/pathmorphing, patterns, matrix, quotes, trees; balíky forest, pgfplots, fontawesome5.

```
.Figure:
  label: fig-is-priklad

  !tikz:
    filename: 08a-nezavisla-mnozina-01
    options: 'scale=0.9, node distance=2cm'

    \node[v] (a) at (0,0) {$a$};
    \node[vsel] (b) at (2,0) {$b$};
    \draw[e] (a)--(b);

  .caption:

    Popisek obrázku. "Všimni si:".emphasize …
```

1. `filename` je povinný a jedinečný: `<jméno .woo souboru bez přípony>-<pořadové číslo dvojmístně>`.
2. Tělo **neobsahuje** `\begin{tikzpicture}` / `\end{tikzpicture}`. Volby z `\begin{tikzpicture}[…]` patří do meta
   `options: '…'` (jeden řádek, jednoduché uvozovky; apostrof uvnitř zdvoj). Bez voleb meta `options` vynech.
   Výjimka: tělo, které celé tvoří `\begin{forest} … \end{forest}`, se do tikzpicture nebalí.
3. Obsah obrázku (souřadnice, popisky, barvy) **neměň**. Uvnitř `!tikz:` je surový LaTeX (`\textbf`, `\prob`, `--` zůstávají).
4. Uvnitř těla **nesmí být prázdný řádek** (prázdné řádky z předlohy vypusť; komentáře `%` smí zůstat) a nesmí tam být
   `\ref`/`\cref` (číslo napiš ručně nebo text přeformuluj). `\hyperlink`, `\hyperref` uvnitř obrázku jsou neškodné (jen vysadí text).
5. **Makra a styly kapitoly** (`\newcommand`, `\tikzset`, `\definecolor`, `\colorlet`, `\def` definované v předloze mimo obrázek,
   např. `\tspnodes`, `\chNPgraph`, `\savrow`) opiš přesně do `tools/tikz/local-NN.tex` (NN = číslo kapitoly = začátek jména
   tvých .woo souborů). Makro definované uvnitř jednoho `tikzpicture` nech v těle obrázku. Cizí `local-*.tex` needituj.
6. Umístění: obrázek s `\caption` je objekt `.Figure:` (na nejvyšší úrovni, se štítkem `fig-…`, uvnitř `!tikz:` přímo a `.caption:`).
   Obrázek bez popisku (`center` + `tikzpicture`) je `.centered:` s `!tikz:` – samostatný blok, i uvnitř objektu.
   Víc obrázků vedle sebe (`minipage`, `\hfill`): jedno `.centered:` / `.Figure:` s několika `!tikz:` oddělenými jedním
   prázdným řádkem. `minipage` „obrázek vlevo, text vpravo“: nejdřív obrázek, pod ním text.
7. `\vsimni`-styl: větu, co z obrázku vyčíst, piš do popisku jako `"Všimni si:".emphasize …`.
8. Rastrový obrázek: soubor do `figures/` (jméno začíná číslem kapitoly), v textu `.image:` s tělem = jméno souboru
   (uvnitř `.Figure:` nebo `.centered:`).
9. Širší obrázek než ~17 cm dostane meta `include_options: 'width=\linewidth'`.

### 2.8 Pseudokód a kód

`.Algorithm:` (`title`, `label`) a v něm `!pseudocode:` s příkazy balíku `algorithmic` velkými písmeny:
`\STATE`, `\IF{c}` … `\ELSIF{c}` … `\ELSE` … `\ENDIF`, `\FOR{c}` … `\ENDFOR`, `\FORALL{c}` … `\ENDFOR`,
`\WHILE{c}` … `\ENDWHILE`, `\RETURN x`, `\REQUIRE`, `\ENSURE`, `\COMMENT{t}`, `\PROCEDURE{F}{a}` … `\ENDPROCEDURE`.
Uzavírací příkazy jsou povinné; tělo `\IF/\FOR/\WHILE` začíná příkazem (`\STATE` …); komentář k hlavičce se píše
`\FOR[komentář]{…}`. V pseudokódu používej jen `\textbf`, `\textit`, `\textsc`, `\texttt`, `\gets`, `\to` a matematiku.
Zdrojový kód (Python, DIMACS, LP formát): `!codeblock:` s meta `language: python` (nebo `text`); tělo doslova.

### 2.9 Odkazy

| LaTeX | WooWoo |
|---|---|
| `kapitola~\ref{ch:cook}`, `oddíl~\ref{sec:cv3}` | `kapitola .reference:ch-cook`, `oddíl .reference:sec-cv3` (vypíše číslo) |
| `obr.~\ref{fig:x}`, `věta~\ref{thm:x}`, `definice~\ref{def:x}`, `\cref{…}` | `obr. .reference:fig-x`, `věta .reference:thm-x` (vypíše číslo objektu; slovo napiš sám) |
| `\hyperlink{red:setcover}{\textbf{Set Cover}}`, odkaz s vlastním textem | `"Set Cover"#red-setcover` |
| `str.~\pageref{…}` | vypustit |

`"text"#štítek` jen pro objekty (ne pro kapitoly a oddíly); `.reference:štítek` pro cokoli. Za štítkem smí hned být interpunkce.
Odkazy do jiných kapitol piš podle mechanického pravidla pro štítky, i když cílový soubor ještě neexistuje.

**Vyskakovací definice (jen web).** Pojmy a problémy, které mají definici, se v textu i ve vzorcích samy obalí
odkazem s okénkem po najetí myší. Ve zdroji se kvůli tomu nic nepíše; seznam pojmů je v `src/pojmy.yaml`
a obaluje je `tools/link_terms.py` po sestavení webu (spouští ho `build_web.sh` i `preview.sh`). Nová `.Definition:`
nebo nový problém používaný ve vzorcích (`\prob{…}`) ⇒ přidej záznam do `src/pojmy.yaml`: `box:` se štítkem rámečku,
nebo `id: pojem-…` s vlastní krátkou definicí, když rámeček není; k tomu `prob:` (přesné argumenty `\prob{…}`),
`makro:` (třídy jako `NP`) a `text:` (regulární výrazy pro skloňované tvary v textu); anglické názvy z `prob:` se
v textu hledají samy, `bez_textu:` je vypne (např. obecné slovo „Rozvrh“). Okénko se ukáže i u
každého `.reference:` na definici, větu, lemma nebo důsledek.

### 2.10 Rámečky skript → objekty

| LaTeX | WooWoo | meta |
|---|---|---|
| `definice{T}{x}` | `.Definition:` | `title: 'T'`, `label: def-x` |
| `veta{T}{x}`, `lemma`, `dusledek` | `.Theorem:`, `.Lemma:`, `.Corollary:` | `title: 'T'` (bez slova „Věta“; prázdné T = bez title), `label` |
| `problem{T}{x}` | `.Definition:` s titulkem začínajícím slovem `Problém` | `title: 'Problém $\prob{Independent Set}$ (IS, nezávislá množina)'`, `label: prob-x`; `Vstup:` a `Otázka:` jako dva odstavce začínající `"Vstup:".notion`, `"Otázka:".notion` |
| `priklad{T}{x}` | `.Example:` | `title: 'T'`, `label: ex-x` |
| `dukaz`, `dukaz[Náznak důkazu]` | `.Proof:` | `title` jen když není výchozí |
| `intuice`, `intuice[T]` | `.Concept:` | `title: 'Intuice'` nebo `'T'` |
| `pozor`, `pozor[T]` | `.Warning:` | `title: 'Pozor'` nebo `'T'` |
| `poznamka`, `poznamka[T]` | `.Remark:` | `title: 'Poznámka'` nebo `'T'` |
| `shrnuti`, `shrnuti[T]` | `.Remark:` | `title: 'Co si odnést'` nebo `'T'` (zelený rámeček) |
| `cviceni{3.2}` + `reseni` | `.Exercise:` a hned za ním `.Solution:` (web řešení sbalí) | `title: 'Cvičení 3.2'`, `label: cv-3-2`; text v závorce za číslem patří do titulku |
| `reseni[Nápověda]` apod. | `.Solution:` začínající `"Nápověda.".notion` | |
| číslované „postupy“ a recepty (kuchařky) | `.Procedure:` | `title: 'T'` |

Hvězdičkové varianty (`definice*`) mají navíc `nonumber: true`. `title` vždy v jednoduchých uvozovkách (apostrof zdvoj);
v `title` smí být `$…$`.

**Hlavička redukce** (uživatel ji chce u každé redukce jako první věc – co se převádí na co):

- `\redukce[id]{A}{B}{instance A}{instance B}` **na nejvyšší úrovni**:

```
.Remark:
  title: 'Redukce: $\prob{3-SAT} \redp \prob{IS}$'
  label: red-is

  formule $\Phi$ $\;\longmapsto\;$ $(G,\ k=n+m)$
```

- `\redukceor[id]{A}{B}{jak}` na nejvyšší úrovni: `title: 'Redukce s orákulem: $\prob{TSP}$ – hodnota optima $\to$ $\prob{TSP}$ – rozhodovací verze'`,
  tělo = věta „jak“ (A řešíme pomocí algoritmu pro B).
- **Uvnitř objektu** (typicky v `.Solution:`) objekt být nemůže, proto první odstavec těla:
  `"Redukce:".notion $\prob{Clique} \redp \prob{Subgraph Isomorphism}$, instance $(G,k)$ $\mapsto$ $(G,\ H=K_k)$.`
  (resp. `"Redukce s orákulem:".notion … $\to$ …. Jak: …`) a štítek `red-id` dostane obalující `.Solution:` (`label: red-subiso`).
- Bez `[id]` je rámeček bez štítku. `\hypertarget{red:id}{}` u nadpisu → štítek `red-id` dostane ten `.Subsection`
  (má-li už jiný štítek, nech `red-id` na nejbližším objektu). **Každé `red:id` z předlohy musí existovat jako štítek `red-id`**
  (odkazuje na ně graf redukcí v příloze D).
- Každá nově psaná redukce (nové kapitoly, typové úlohy) začíná touto hlavičkou.

Na webu jsou rozbalovací `.Solution:` a `.Proof:`; u `.Example:` zůstane vidět první blok (zadání příkladu) a vše
za ním je rozbalovací „Řešení“ – první blok příkladu proto má být zadání. V PDF je všechno rozbalené.

### 2.11 Co se vypouští

`\clearpage`, `\needspace`, `\vspace`, `center` (jen obal), `\phantomsection`, `\addcontentsline`, `\renewcommand{\arraystretch}`,
komentáře `%`, čísla stran, ikony Font Awesome v textu. Věty o rozložení stránky („obrázek vpravo“) uprav („obrázek níže“).

---

## 3. Styl nově psaného textu (kapitoly 14–15, přílohy)

Česky, stejným tónem jako předloha (tykání čtenáři není nutné; krátké věty, žádná vata). Zdrojem pravdy jsou slajdy,
cvičení a oficiální materiály v `../ni-icc/` – notaci a názvy přebírej odtud, projdi i obrázky ve slajdech (čti PDF po stránkách).
Co ve zdrojích není a je doplněné pro pochopení, označ `"(nad rámec přednášky)".emphasize`. Každé téma: nejdřív proč,
pak definice, malý řešený příklad krok za krokem, typické chyby (`.Warning:` s `title: 'Typické chyby'`), obrázek.
Řešení úloh piš tak, jak by je měl napsat student u testu: celé, s mezikroky a zdůvodněním. **Každé číslo a každý
výsledek ověř** (krátkým skriptem v pracovním adresáři mimo projekt, ne z hlavy). Nic nevymýšlej: co ze zadání neplyne,
řekni otevřeně.

---

## 4. Kontrola

```
tools/preview.sh 08            # všechno pro soubory src/08*.woo: struktura, obrázky, vzorce, náhled webu, MathJax
python3 tools/check_woo.py src/08a-nezavisla-mnozina.woo     # jen struktura jednoho souboru
python3 tools/check_tikz.py src/08a-nezavisla-mnozina.woo    # jen obrázky jednoho souboru
```

Argument je číslo kapitoly: `tools/preview.sh 08z` nebo `17a` (jeden soubor) sice projde kontroly, ale stránku webu
nesestaví – náhled se dělá vždy pro celou kapitolu (`tools/preview.sh 08`, `tools/preview.sh 17`).

`tools/preview.sh NN` musí skončit bez chyb `[E]` (hlášení `[R]` / „neznámý štítek“ o odkazech do kapitol, které ještě
nejsou hotové, nevadí). Náhled je v `.build/preview-NN/site/`; stránku si prohlédni (snímek přes Chrome bez okna):

```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-first-run \
  --user-data-dir=/tmp/chrome-NN --window-size=1300,3000 --virtual-time-budget=20000 \
  --screenshot=/tmp/nahled-NN.png "file://$PWD/.build/preview-NN/site/<složka>/<stránka>.html"
```

Celý web: `tools/build_web.sh` (píše do `../skripta/html/`), PDF: `tools/build_pdf.sh` (`../skripta/NI-ICC_skripta.pdf`).
Pouští se až nakonec, ne souběžně.

Úplnost převodu kapitol 1–13 a přílohy D proti LaTeXové předloze hlídá `python3 tools/check_prevod.py NN`
(štítky podle mechanického pravidla, počty obrázků, cvičení, hlaviček redukce, oddílů, objem textu). Musí skončit
bez `[E]`; každé `[W]` projdi ručně (rozpuštěný vnořený rámeček je v pořádku, chybějící obsah ne).
