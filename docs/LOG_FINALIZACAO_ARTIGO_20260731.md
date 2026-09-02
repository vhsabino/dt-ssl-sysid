# Log de finalização do artigo — SBR/LARS 2026 (sessão 2026-07-31)

> Rastreabilidade documentada da sessão de orquestração multiagente que levou o
> artigo do estado "seções III–VI escritas, I/II/VII stubs, bib vazio" ao PDF
> submissível de 6 páginas. Cada iteração, agente, decisão editorial e corte
> está registrado abaixo. Deliverables: `latex/paper_sbr2026_20260731.pdf`,
> `docs/REVISAO_ESPECIALISTA_20260731.md`, `slr/CANDIDATOS_CITACAO.md`,
> `slr/EXTRACAO_CITAVEIS.md`, `docs/BACKLOG_EXTENSAO_JINT.md`.

## Resumo executivo (3 linhas)

1. Artigo fechado em **6 páginas IEEE A4 double-blind**, 0 erros de compilação,
   0 referências indefinidas, 0 `\todocite`, 0 `[A VERIFICAR]`, checklist A1–A12
   aprovado, 18 referências todas verificadas contra PDF em `slr/pdfs/`.
2. **Título invertido** para a tese vigente; Introduction/Related Work/Abstract/
   Conclusion escritos do zero na narrativa de identificabilidade por regime de
   excitação; 4 afirmações enfraquecidas após revisão cética (decisão do autor).
3. Nenhum resultado foi removido: os cortes (~2 páginas) condensaram texto e
   removeram 2 figuras de apoio + 2 referências redundantes, tudo realocado em
   `docs/BACKLOG_EXTENSAO_JINT.md`.

---

## Iteração 1 — Leitura de estado + Agentes 1 e 3 (paralelo)

**Leitura obrigatória concluída:** `docs/REVISAO_SECOES_20260724.md`,
`docs/PLANO_PAPER_SBR2026.md`, `results/identificacao_omega_20260724.md`,
`results/reidentificacao_20260724.md`, `results/qc_rotate_20260724_125828.md`,
`config/robot_geometry.json`, `results/CHANGELOG.md`, `latex/**`.

**Estado encontrado:** III–VI escritas na narrativa correta; 00/01/02/07 stubs
com instruções internas *desatualizadas* (diziam "ω não identificável" e
"coleta dedicada = trabalho futuro"); `references.bib` vazio; título afirmando
o inverso do achado; 1 `[A VERIFICAR]`; 2 `\todocite`.

### Agente 1 (bibliografia, fase 1)
- Notion DB `74fe3d83-...`, filtro `Status = "Recommended Full Read"` → **367
  registros** extraídos; **44 aderentes** aos eixos (a)–(d) + Temas A/B;
  13 prioridade alta. Produziu `slr/CANDIDATOS_CITACAO.md`.
- **Lacunas críticas detectadas:** Tema A (closed-loop ID clássico) com **0**
  candidatos; eixo (d) sem o paper do rSoccer/grSim — **o baseline do artigo**.

### Agente 3 (análise)
- **(a) `[A VERIFICAR]` de e_ang — RESOLVIDO, não era inconsistência.**
  Auditoria de `phase0_replay/metrics.py`: e_pos e e_ang são *sempre*
  calculados; `use_se2=false` controla apenas a tabulação do escalar combinado
  `e_se2`. A re-âncora é SE(2) completa independentemente da flag. São dois
  papéis legítimos (gate de promoção MATLAB usa SE(2) combinado; harness Python
  separa e_pos/e_ang). Faltava só tabular: gerado
  `results/window_errors_eang_twin_vs_ideal_20260731_023856.csv` (+ summary).
  **Validação:** as medianas de e_pos desse run reproduzem
  `results/phase0_metrics_report_20260724_1729.md` exatamente.
- **(b) Figura twin-vs-rSim NÃO regenerável fielmente:** as trajetórias do run
  `20260617_0030` nunca foram persistidas e `robosim` está indisponível
  (bloqueio pré-existente). Ver iteração 3 para a solução adotada.
- **(c) Figura de fit hold-out vx/vy gerada** (`scripts/fig_fit_holdout_vxvy.py`);
  fits Python reproduzem os do MATLAB a **≤0,05 p.p.** (86,66 vs 86,7 etc.).
- **(d)** Figura de degrau de ω já existia; copiada como candidata.

### ⛔ Ponto de parada 1 — decisões do usuário
| Questão | Decisão |
|---|---|
| Escopo de refs | 13 alta + lacunas críticas (~17–19 refs) |
| Tema A | pesquisar e solicitar clássicos (máx. 5 papers) |
| Eixo (d) | usuário deposita rSoccer **e** grSim |
| Tema B | **reformular** para o que os candidatos sustentam (sem afirmar escassez como fato de survey) |

Pesquisa web executada para o Tema A → 5 clássicos indicados
(Forssell & Ljung 1999; Van den Hof 1998; Gustavsson et al. 1977; Ljung 1999;
Åström & Hägglund 1995). Usuário depositou **20 PDFs** em `slr/pdfs/`.

---

## Iteração 2 — Agente 1 (fase 2) e Agente 2

### Agente 1 fase 2 — `references.bib`
20 entradas criadas **exclusivamente a partir dos PDFs depositados**, campo a
campo. Nenhum metadado preenchido de memória; campos ausentes no PDF ficaram
omitidos e sinalizados. Produziu `slr/EXTRACAO_CITAVEIS.md`.

**Correções de ano vs. Notion (verificadas no PDF):** Brennan 2024→**2025**;
Yang 2024→**2025**; Freiberger 2025→**2024**; grSim 2016→**2012**.
**Metadados incompletos declarados:** `machado2025planning` (preprint sem venue/
ano), `katyara2024benchmarking` (capítulo sem editora), `martins2021rsoccer`
(versão arXiv), `giro2023otbot` (arXiv).
**Double-blind:** identificado que `martins2021rsoccer` também é do mesmo grupo
→ marcado † (4 entradas †, todas citadas em 3ª pessoa neutra).
**Nenhum caso de "NÃO SUSTENTA"**; 4 ressalvas de escopo registradas.

### Agente 2 — redação
- **Título** (3 alternativas propostas; recomendada aplicada, 2 preservadas em
  comentário no `main.tex`): *"Excitation Regime, Not the Degree of Freedom:
  Identifiability in Grey-Box Digital Twinning of an Omnidirectional Soccer
  Robot"*. Justificativa: lidera com a tese em vez de escondê-la atrás do
  método; contém os termos de indexação; elimina o "from Closed-Loop
  Competition Logs" que afirmava o **inverso** do achado de ω.
- **01_introduction** reescrita (reality gap → logs como dado disponível →
  lacuna com refs reais → achado de regime → C1–C4). **C4 reescrita**: de
  "não-identificabilidade de yaw" para "caracterização da identificabilidade de
  yaw como função do regime de excitação". Os **três tópicos do CFP** ("robot
  soccer", "robot modeling", "robot simulation and visualization tools")
  aparecem explicitamente no texto.
- **02_related_work** escrita nos eixos (A)–(E), só com chaves do `.bib`.
- **05_discussion**: os 2 `\todocite` substituídos —
  (a) → `\cite{gustavsson1977identification,vandenhof1998closedloop,forssell1999closedloop}`;
  (b) **Tema B reformulado** conforme decisão: afirma que logs de malha fechada
  são o recurso naturalmente abundante na liga (documentado por
  `melo2023dataset`) e que a campanha dedicada exige acesso fora dessa rotina —
  **sem** afirmação de escassez tipo-survey.
- **07_conclusion** e **00_abstract** (179 palavras) escritos.

---

## Iteração 3 — Agente 4 (conformidade) e cortes

**Primeira medição: 8 páginas** (limite 6). Achados mecânicos corrigidos:

| # | Achado | Correção aplicada |
|---|---|---|
| 1 | `\documentclass[conference]` → **US letter**, CFP exige A4 | `[conference,a4paper]` |
| 2 | 8× `! Double subscript` (`\Td_i` → `T_{d}_i`) | `\Td{}_i` em 03/04 |
| 3 | macro `\todocite` ainda definida | removida |
| 4 | "(UFPE/RoboCIn)" em comentário do `.bib` | removido (A1/A2) |
| 5 | Tabela III não dizia qual tentativa closed-loop reporta | nota de rodapé |
| 6 | Declaração D5 atribuía a grade MATLAB só ao gate de yaw | ampliada p/ gates por DOF |

**Checklist A1–A12: aprovado** (nenhum achado no PDF renderizado; metadados sem
Author/Title).

### ⛔ Ponto de parada 2 — pacote de corte (aprovado integralmente: A–F)
| Item | Corte | Decisão |
|---|---|---|
| A | Limitations 9→4 §§ | **todas as limitações permanecem mencionadas**, apenas condensadas |
| B | bayesopt: subseção IV-E + V-D → parágrafo "Negative control" | números (+0.0041 m, p=0.040, −0.098 m, ρ=0.999) preservados |
| C | Figura de distribuição de bins removida | números 264/265/99,6% permanecem no texto |
| D | Discussão V-A e V-E encolhidas | argumento preservado |
| E | Mode B / twin-vs-ideal / heading → 1–2 frases | todos os números preservados |
| F | Related Work eixos (a)/(c) comprimidos | — |
| reserva | Figura ganho×amplitude removida | claim permanece no texto |
| figs novas | fit vx/vy e degrau ω **não entram** | → backlog JINT |

Cortes adicionais de redação (sem perda de conteúdo): equações (2)–(4) do
Method viraram prosa; venues do `.bib` abreviados ao padrão IEEE;
contribuições C1–C4 de `itemize` para parágrafo compacto; `address` de livros
removido. **Referências `kosmaga2026digital` e `katyara2024benchmarking`
removidas** — a primeira por sobreposição de claim com `brennan2025greybox`, a
segunda por ser fora de domínio (manufatura ágil) e com metadados não
verificáveis no PDF depositado (crítica antecipada pelo revisor).

---

## Iteração 4 — Agente 5 (revisão especialista) e correções de claim

Revisão independente do PDF: `docs/REVISAO_ESPECIALISTA_20260731.md`.
**Recomendação simulada: borderline, inclinado a weak accept.** Notas:
originalidade 3,5 · solidez técnica 2,5 · rigor 3,0 · clareza 3,5 ·
relevância 4,0 · reprodutibilidade 2,5.

### ⛔ Ponto de parada 3 — afirmações que excediam a evidência
O revisor apontou 4 casos em que a única saída era **enfraquecer a afirmação**
(gatilho de parada obrigatória). Usuário aprovou **todas as 4**:

| # | Afirmação original | Como ficou | Onde |
|---|---|---|---|
| B1 | abstract afirmava viés de correlação como fato | "which we read as evidence that…" + limitação nova declarando que regime, amplitude e sessão co-variam | `00_abstract`, `06_limitations` |
| B2 | "statistically indistinguishable from unity" | IC declarado como assintótico/model-based sobre 4 eventos, que limita **precisão do estimador**, não variabilidade entre sessões; leitura de "near unity" nesse sentido restrito | `04_results` §Interpretation |
| B5/B6 | "gap cresce ⇒ vantagem dinâmica" | admite que erro de velocidade inicial também acumula com h e que o rSim roda em parâmetros default → o resultado **limita o que um simulador de referência não sintonizado entrega**, não estabelece vantagem dinâmica geral | `05_discussion` §C |
| B3 | não se tentavam estimadores closed-loop-aware | limitação explícita: IV/two-stage/joint I-O não tentados; questão declarada em aberto | `06_limitations` |

**Cherry-picking de heading corrigido (decisão do usuário):** o texto agora
declara que, contra o rSim, o e_ang do gêmeo é **pior** em horizontes longos —
"the position claim does not transfer to heading".

### Figura: reconstruída em inglês e sem o painel obsoleto
A única figura tinha **rótulos em português** e marcador interno de pipeline
(`[TODOS] (N=265, indep=49)`), e seu painel e_ang fora gerado com o
**placeholder de ω**. O SVG-fonte usa glifos vetorizados (texto não editável).
Solução adotada (aprovada pelo usuário): `scripts/fig_twin_vs_rsim_epos_en.py`
**replota apenas o painel e_pos**, com medianas e IC bootstrap **transcritos
verbatim** de `results/eval_twin_vs_rsim_modeA_20260617_0030.md`
(seção *trans-dominado*) — nenhum dado recomputado. Isso resolve
simultaneamente o idioma, o marcador interno e a inconsistência do painel
gerado com placeholder. Saída:
`results/figs/twin_vs_rsim_epos_en_20260731_145834.{png,pdf}` →
`latex/figures/twin_vs_rsim_epos_en.png`.

---

## Estado final vs. critérios de conclusão

| # | Critério | Status |
|---|---|---|
| 1 | PDF compila, ≤6 páginas, IEEE A4 | ✅ 6 páginas, 595×842 pt (A4), 0 erros |
| 2 | Zero `\todocite`, `[A VERIFICAR]`, refs cruzadas quebradas | ✅ 0 / 0 / 0 undefined |
| 3 | `.bib` verificado contra PDF em `slr/pdfs/` | ✅ 18 citadas, todas com PDF depositado |
| 4 | Checklist A1–A12 | ✅ aprovado (varredura full-text + metadados) |
| 5 | Todo número rastreável a `results/` ou `config/` | ✅ comentários `% source:` em todos |
| 6 | Narrativa coerente do título à conclusão | ✅ título, abstract, C4, discussão e conclusão alinhados à tese de regime |

### ⚠️ Ressalva de build (obrigatório verificar antes de submeter)
A contagem de páginas foi obtida no ambiente sandbox com **dois substitutos**:
um shim mínimo de `siunitx` e `IEEEtranM.bst` no lugar de `IEEEtran.bst`
(ambos ausentes no sandbox). O build oficial (Overleaf, template IEEE) usará os
pacotes reais e **pode deslocar a paginação em alguns milímetros**. Recompilar
no Overleaf e confirmar 6 páginas antes do envio; havendo estouro marginal, o
próximo corte recomendado é a Tabela II (twin vs rSim), cujos números por
horizonte estão agora duplicados na Fig. 1 e no texto.

### Pendências deixadas para o autor
1. Recompilar no Overleaf (ver ressalva acima) e conferir metadados do PDF final.
2. Completar venue/ano de `machado2025planning` se publicado até a submissão.
3. Declarar os 3 tópicos no JEMS: *Robot soccer*, *Robot modeling*,
   *Robot simulation and visualization tools*.
4. Fraquezas (iii) "sugestões" do revisor não aplicadas por orçamento de página
   estão em `docs/BACKLOG_EXTENSAO_JINT.md`.
