// Nastavení MathJaxu: zpracovává se jen obsah prvků s třídou "arithmatex" (vzorce z převodníku).
// Makra odpovídají tools/tikz/macros.tex (stejná makra zná lualatex při překladu obrázků a kontrole vzorců).
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
    processHtmlClass: "arithmatex"
  },
  svg: { fontCache: "global" }
};
