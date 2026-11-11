# Camera-ready SBR/LARS 2026 (#34344): o que mudou e o que falta

*Preparado em 23/09/2026 sobre a versão aceita copiada para `paper/sbr2026_accepted/`. Esta pasta
(`paper/sbr2026_camera_ready/`) é a versão corrigida; a pasta da versão aceita não foi tocada.
Plano de origem: `PLANO_CAMERA_READY_SBR2026.md`, Faixa A. Nenhum número ou afirmação da versão
revisada mudou; os números novos do texto (limitações) vêm de artefatos citados em comentário
`% source:` ao lado de cada frase.*

## 1. Estado

- Compila limpo na nuvem (TeX Live, `pdflatex`, `bibtex`, `pdflatex` ×2): 0 erros, 0 referências
  indefinidas, **6 páginas A4**, fontes todas embutidas, só TABLE I e TABLE II no PDF.
- `main_camera_ready_draft.pdf` é o rascunho compilado (com os marcadores `REPLACE-ME` visíveis).
- `camera_ready_vs_accepted.diff` é o diff unificado contra a versão aceita (505 linhas, só `.tex`).
- A versão aceita tinha um erro de TikZ escondido (Fig. 1, nó sem texto em
  `figures/fig_architecture2.tex`): o Overleaf gera o PDF mesmo assim, mas um build estrito para. Linha
  removida; a figura sai igual.

## 2. O que foi aplicado (Faixa A)

| Item | Onde | O que mudou |
|---|---|---|
| A1 | `sections/00_abstract.tex` | abstract em um parágrafo, 250 palavras, sem símbolos; devolve as ressalvas de 99,6 % translacional e rSim sem sintonia |
| A2 | `02_related_work.tex`, `03_method.tex`, `04_results.tex` | `\paragraph` trocado por `\subsection` (Related Work) e `\subsubsection` numerado (Results); "Definition of hold-out fit" virou texto corrido |
| A3 | fonte | só `tab:sysid` e `tab:three` são inputadas; conferir no PDF do JEMS se havia uma terceira tabela (ver §4) |
| A4 | vários | os 12 itens do plano (frase quebrada da introdução, "is classic", "larger", "center-to-wheel-contact", frase de III-F que estava dentro de um comentário, n = 49 janelas, placeholder de yaw definido, "which attains", "Future Work", espaços duplos) e o erro de TikZ |
| A5 | `main.tex`, `07_conclusion.tex` | cabeçalho e comentários de decisão de título limpos; bloco de autores, e-mails, agradecimento e URL com `REPLACE-ME`; título do JEMS mantido (sua decisão de 23/09); linha de copyright IEEE comentada, pronta para ativar |
| A6 | `figures/fig_setup.tex` (novo), chamada em III-C | figura da cadeia de medição em TikZ; as fotos entram sozinhas se você puser `figures/robot_photo.jpg` (e, se quiser, `figures/field_photo.jpg`), com as letras dos painéis e a legenda ajustadas; altura das fotos limitada a 3 cm (testado: continua em 6 páginas com retrato ou paisagem) |
| A7 | nota de rodapé em III-C | link dos dois vídeos (`\videolink` em `main.tex`) |
| A8 | fim de V-B (`05_discussion.tex`) | parágrafo novo: canais desacoplados, sem saturação, sem limite de aceleração, sem zona morta, envelope dos dados (velocidade comandada acima de 2,9 m/s em 0,01 % das amostras de competição; PWM de pico a cerca de um quarto do limite na coleta de yaw), slip só pelos ganhos e atrasos |
| A9 | III-G (`03_method.tex`) | a frase errada "driven at adjusted parameters" saiu; entrou a descrição conferida no código (`src/dtssl/models/rsim.py`): parâmetros de fábrica, comando de corpo direto, subpassos de 1 ms, aquecimento de 15 comandos e re-ancoragem SE(2), sem atraso de transporte |
| Página | `main.tex` (`\keeptrajfigfalse`) | para caber em 6 páginas, a Fig. de trajetórias por rótulo (casos de maior margem, figure* de largura dupla) sai, como o plano recomendava (§6, corte 1); a frase que a citava sai junto. Se o limite do JEMS permitir 7 páginas, troque para `\keeptrajfigtrue` |

## 3. O que depende de você (o checklist procura `REPLACE-ME` e tem de achar zero)

1. `main.tex`: autores na ordem do JEMS, e-mails, e o texto do agradecimento (financiamento,
   RobôCIn, quem fez a coleta de yaw de 04 e 05/07 e quem fez o CAD).
2. `main.tex`: `\repolink` (repositório público + DOI; o D3 do backlog, `dtssl release`, está
   congelado) e `\videolink` (os dois vídeos: coleta de yaw com a extração de velocidade; o gêmeo
   jogando com a estratégia, que é o vídeo 1 do runbook D5).
3. Fotos (opcionais, mas R2 pediu): `figures/robot_photo.jpg` e, se quiser, `figures/field_photo.jpg`.
4. JEMS: limite de páginas, prazo, se a Tabela III duplicada aparece no PDF submetido, formulário de
   copyright (eCF), PDF eXpress se for exigido, e a linha de copyright (descomentar `\IEEEpubid`
   em `main.tex` só com o texto exato que a organização mandar).
5. Título: mantido o do JEMS. Se decidir trocar, o `\title{}` e o JEMS têm de coincidir.

## 4. Nota para os chairs (se o JEMS tiver campo de resumo das mudanças)

> Changes for the camera-ready: the abstract was rewritten as a single paragraph; run-in paragraph headings were replaced by IEEE subsections and numbered subsubsections; a figure of the measurement chain (and of the robot) was added, with a link to two supplementary videos; the description of the rSim baseline was corrected to state that it runs with its stock parameters, untuned; the Limitations subsection now states the decoupled structure and the absence of slip, saturation and other nonlinearities, with the envelope of the data; the figure of best-case trajectory overlays was removed to stay within the page limit, its evidence remaining in Fig. 4 and Table II; [the duplicated table was removed;] typographical corrections throughout. No number or claim of the reviewed version was changed.

(Manter o trecho entre colchetes só se a Tabela III duplicada estiver no PDF do JEMS.)

## 5. Faixa B pronta para colar, se a orientadora aprovar o D1

Não aplicada: depende da decisão D1. Custo estimado de cada trecho entre parênteses; com 6
páginas já cheias, entrar B exige 7 páginas ou outro corte.

**B1** (fim do segundo parágrafo de V-A, ~7 linhas):

```latex
An in-silico check makes the coupling explicit. Replaying the competition commands through a physics simulation of the same robot with rolling omni wheels (four wheels, twelve rollers each, untuned, with the identified transport delay) and re-identifying yaw with the estimator of this paper inflates the yaw gain by $16$ to $27\%$, in the direction of the closed-loop bias, whereas the same commands with the translational components zeroed show no inflation (gains of $0.93$ to $0.99$) and the dedicated staircase, replayed through the same simulation, returns $0.996$. The bias is therefore translation-induced yaw correlated with the strategy's yaw commands: a coupling the decoupled channel cannot represent and the dedicated collection removes.
% source: results/identifiability_insilico_mujoco-rollers-delay_v2_20260907_2044.json (K_w R1 none/off 1.160 = +16.5 %,
%   R1 vision/on 1.270 = +27.4 %, R1-wonly 0.988 / 0.930, R2-rotate 0.996); CHANGELOG 2026-09-07 20:45 (C1b v2)
```

**B2** (em "The untuned ODE simulator", ~6 linhas). Corrigida em relação ao plano: são duas sessões
do C2b2 (18/09 e 20/09) e duas variantes do ER-Force, e a faixa cobre todas:

```latex
The finding does not hinge on rSim: grSim and the ER-Force simulator, driven through the league simulation protocol on the same windows, give per-event median errors between $\SI{0.097}{m}$ and $\SI{0.111}{m}$ at $h_{\mathrm{ref}}$ in two independent sessions (grSim pre-rolled over the real command prefix, so that it reaches the anchor with its own dynamics rather than from rest; ER-Force with and without pre-roll), against $\SI{0.042}{m}$ for the model, which is lower in all ten events for every simulator and session (one-sided Wilcoxon $p = 9.8\times10^{-4}$). None of these engines is tuned to this robot, which is the limitation the comparison carries.
% source: results/protocol_holdout_20260918_1326.md (grsim+preroll 0.1106, erforce 0.1023, erforce+preroll 0.1114); minimo exato 0.09746 (json de 20/09) -> 0.097
%   e results/protocol_holdout_20260920_1143.md (0.0975, 0.0995, 0.1114); gemeo 0.0421 nas duas; 10/10, p = 9.8e-4
```

A sessão de 18/09 só entra no CHANGELOG com o lote 1 deste chat (entrada nova); antes disso, a B2
não pode citar a faixa inteira.

**B3** (uma frase, depois de rodar o `coupled_mimo_check` no PC): as duas redações estão no
pré-registro `docs/PREREGISTRO_MIMO_CHECK_20260923.md` (§8).

## 6. Checklist do envio

- [ ] `REPLACE-ME` zerado: `findstr /s /n "REPLACE-ME" *.tex` na pasta (ou `grep -rn`).
- [ ] Autores e título iguais aos do JEMS.
- [ ] Compilar no Overleaf: 0 erros, 6 páginas (ou 7, se o limite permitir e `\keeptrajfigtrue`).
- [ ] Fotos com resolução suficiente (JPG com ~1000 px de largura basta).
- [ ] Vídeos publicados e link testado; repositório público e DOI.
- [ ] Copyright IEEE (eCF) e, se pedido, PDF eXpress.
- [ ] Depois do envio: copiar a versão final para `latex/` do repositório e registrar no CHANGELOG.
