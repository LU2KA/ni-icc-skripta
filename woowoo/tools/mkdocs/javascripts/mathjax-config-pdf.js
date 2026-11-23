// Nastavení MathJaxu pro PDF verzi (makra = kopie z mathjax-config.js, drž je stejná): vzorce se sázejí písmem (výstup CHTML), ne křivkami jako na webu.
// V PDF je pak text vzorců ostrý při každém zvětšení, dá se vybrat a soubor je několikrát menší.
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
    macros: {
      textsc: ["\\mathrm{#1}", 1],          // MathJax nezná kapitálky
      cls: ["\\mathsf{#1}", 1],
      PP: "\\mathsf{P}", NP: "\\mathsf{NP}", NPhat: "\\widehat{\\mathsf{NP}}", EXP: "\\mathsf{EXP}",
      NEXP: "\\mathsf{NEXP}", DTIME: "\\mathsf{DTIME}", NTIME: "\\mathsf{NTIME}", DSPACE: "\\mathsf{DSPACE}",
      NSPACE: "\\mathsf{NSPACE}", PSPACE: "\\mathsf{PSPACE}", NPSPACE: "\\mathsf{NPSPACE}",
      LL: "\\mathsf{L}", NL: "\\mathsf{NL}", coNP: "\\mathsf{coNP}", coNL: "\\mathsf{coNL}",
      redp: "\\le_{p}", enc: ["\\langle #1\\rangle", 1], prob: ["\\textsf{#1}", 1],
      qA: "q_{A}", qR: "q_{R}", qhalt: "q_{\\mathrm{halt}}", blank: "\\sqcup", Sig: "\\Sigma",
      N: "\\mathbb{N}", Lft: "\\leftarrow", Rgt: "\\rightarrow", Stay: "\\bullet",
      ANO: "\\mathbf{\\color{##2E7D32}ANO}", NE: "\\mathbf{\\color{##C62828}NE}",
      dist: "\\operatorname{dist}", polylog: "\\operatorname{polylog}",
      clr: ["\\textcolor{#1}{#2}", 2]
    }
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex",
    enableMenu: false,
    enableAssistiveMml: false,    // skrytá kopie vzorce pro čtečky by se v PDF vybírala a hledala dvakrát
    menuOptions: { settings: { assistiveMml: false } }
  },
  chtml: {
    fontURL: "javascripts/mathjax-chtml/woff-v2",
    mtextInheritFont: true        // český text ve vzorcích (\text{…}) písmem okolního textu, s diakritikou
  }
};
