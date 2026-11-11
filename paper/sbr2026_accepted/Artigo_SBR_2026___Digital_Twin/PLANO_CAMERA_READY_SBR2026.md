# Plano de correção camera-ready: SBR/LARS 2026, submissão #34344

*Escrito em 23/09/2026 a partir dos dois pareceres recebidos em 22/09 (JEMS) e da versão
submetida em `C:\Users\victo\OneDrive\Área de Trabalho\Papers\Artigo_SBR_2026___Digital_Twin`
(export do Overleaf; os `.tex` são a versão aprovada, mas a pasta não tem `main.pdf` e o
`main.log` é de 31/07, então a contagem de páginas e a numeração de tabelas do PDF que os
revisores viram têm de ser conferidas no PDF do JEMS). Nada foi alterado no artigo: cada
correção está aqui pronta para colar, para você revisar e aplicar. Números novos citados
abaixo vêm de `results/CHANGELOG.md` (entradas de 07/09, 10/09 e 20/09) e dos artefatos ali
apontados; nenhum número foi recomputado nesta sessão.*

## 0. Resumo executivo

Aceito com R1 = Neutral (não especialista) e R2 = Weak Accept (familiar com a área). Os dois
pareceres convergem em quatro pontos: (i) acoplamento entre canais ignorado (estrutura
desacoplada), (ii) validação rotacional ausente (hold-out 99,6 % translacional), (iii) comparação
com rSim não sintonizado, (iv) apresentação (abstract em dois parágrafos, cabeçalhos "colados",
tabelas II e III duplicadas). R2 acrescenta: figura do robô e do aparato experimental, vídeos do
procedimento de medição e do gêmeo em execução, e discussão de slip, saturação e não linearidades.

O que fazer, em três faixas:

| Faixa | Item | Custo em página | Seção |
|---|---|---|---|
| A (obrigatório no camera-ready) | A1 abstract em um parágrafo · A2 cabeçalhos `\paragraph` → `\subsubsection` · A3 tabela duplicada · A4 proofreading (12 itens, um deles factual: a frase do rSim "adjusted parameters") · A5 desanonimização, título, URL real · A6 figura robô + aparato · A7 vídeos suplementares (link) · A8 limitações explícitas: desacoplamento, slip, saturação · A9 rSim: frase consistente em III-G, Fig. 2 e V-B | +0,45 pág. antes dos cortes | §2 |
| B (recomendado, se o limite permitir; decisão D1 congelada com a orientadora) | B1 parágrafo do mecanismo do viés de ω (acoplamento translação → guinada, C1b) · B2 uma frase com grSim/ER-Force no harness (C2b2) · B3 checagem MIMO barata (código pronto) · B4 rSim sintonizado (só na extensão) | +0,25 pág. | §3 |
| C (extensão para periódico) | tudo de B com profundidade, validação em malha fechada (C4), gêmeo físico (C2a/C3), material do backlog JINT | n/a | §4 e §5 |

Antes de tudo: confirmar no JEMS (https://jems3.sbc.org.br/submissions/34344/) o **prazo do
camera-ready** e o **limite de páginas** (6 páginas no CFP dos anos anteriores; alguns anos
aceitam até 2 extras pagas). O orçamento de página decide quanto de B entra.

Special issue (§5): é do periódico *Digital Engineering* (Elsevier, open access, EIC Fei Tao),
"organized in conjunction with" a DigiTwin 2026, **aberta a qualquer autor** ("You are invited to
submit your manuscript at any time before the submission deadline"), article type
`VSI:DTE_DigiTwin2026`, submissões até 28/02/2027, decisões até 31/05/2027, APC gratuita para
submissões até 31/12/2026 (depois USD 1.830). A única cláusula que pede cuidado é a de
originalidade ("must not have been previously published"): a extensão tem de ser um trabalho novo
que cita o artigo do SBR, e vale confirmar com o executive guest editor (e-mail pronto em §5.4).
Recomendação: enviar a extensão para lá em dezembro, e não para a JINT, com a divisão de conteúdo
proposta em §5.3.

## 1. Mapa parecer → ação

| # | Rev. | Comentário (resumo) | Ação | Faixa |
|---|---|---|---|---|
| 1 | R1 | "core premise breaks down": yaw precisou de coleta open-loop | Reforçar no abstract e na Conclusão que isso é o achado (o log identifica o que excita; a triagem C4 diz qual canal precisa de coleta). Já está no texto; A1 deixa explícito na primeira frase de resultado | A1 |
| 2 | R1, R2 | três canais desacoplados ignoram acoplamento; R2 pede MIMO | A8 (limitação explícita) + B1 (mecanismo medido in silico) + B3 (checagem MIMO com critério pré-registrado; entra uma frase se rodar, senão vai para a extensão) | A8, B1, B3 |
| 3 | R1, R2 | hold-out quase todo translacional; gêmeo rotacional não validado | Já declarado em IV-B e V-B; A8 mantém; extensão precisa de distribuição rica em rotação (backlog JINT, pendência 2) | A8, C |
| 4 | R1, R2 | fitted × untuned rSim não é benchmark; R2 pede rSim sintonizado | A9 (corrigir a frase de III-G que diz "adjusted parameters", que contradiz Fig. 2 e V-B) + B2 (grSim e ER-Force no harness, 10/10) + B4 (sintonia: extensão) | A9, B2, B4 |
| 5 | R1 | cabeçalhos de seção "incorretamente fundidos ao corpo" | São os `\paragraph{}` run-in do IEEEtran (itálico, dois-pontos, texto na mesma linha). A2 troca por `\subsubsection{}` numerado ou remove | A2 |
| 6 | R1 | Tabela II e Tabela III idênticas | O fonte atual só tem duas tabelas (`tab:sysid`, `tab:three`). Conferir no PDF do JEMS; provável `\input{tables/tab_twin_vs_rsim}` residual (mesmas colunas model/rSim da Tab. II a menos de arredondamento) | A3 |
| 7 | R1 | "thorough proofreading" | A4: lista de 12 correções localizadas | A4 |
| 8 | R2 | slip, saturação, não linearidades não discutidos | A8, com dois números do repositório (0,01 % das amostras acima de 2,9 m/s; PWM de pico a cerca de um quarto do limite por roda na coleta de yaw) | A8 |
| 9 | R2 | yaw de uma sessão; heading pouco validado | Já em V-B; manter | (ok) |
| 10 | R2 | sem imagem do robô nem do aparato de medição de velocidade | A6: figura com foto do robô + diagrama da cadeia de medição (visão → pose → derivada) | A6 |
| 11 | R2 | vídeos do procedimento de medição e do gêmeo simulando | A7: dois vídeos curtos, link em nota de rodapé (o runbook D5 já tem os scripts do segundo) | A7 |
| 12 | R2 | abstract em um único parágrafo | A1 (a versão submetida tem linha em branco após "hold-out fit.") | A1 |

## 2. Faixa A: correções obrigatórias, prontas para colar

### A1. Abstract em um parágrafo (`sections/00_abstract.tex`)

Substituir todo o ambiente `abstract` por (um parágrafo, ~250 palavras, sem símbolos nem citações,
mantendo os números já publicados e devolvendo as duas ressalvas que a versão de 6 páginas
perdeu: 99,6 % translacional e rSim não sintonizado):

```latex
\begin{abstract}
Teams in the RoboCup Small Size League develop and validate control software largely in simulation, where simplified physics leaves a reality gap to the field. This paper asks what behavioral model of an omnidirectional soccer robot can be identified from the competition logs that teams already record, and what those logs cannot supply. Each body-frame degree of freedom is modeled as a first-order-plus-dead-time channel. The two translational channels identify directly from in-game logs and reach roughly 87 percent hold-out fit. The yaw channel does not: in play the yaw command is a median of one percent of the per-wheel actuation and explains only 56 percent of the measured rotation, so a short dedicated open-loop campaign restores the excitation and identifies the channel at 71 percent hold-out fit. Fidelity is then evaluated in free run over horizons from 0.1 to 1.5 seconds, with every plant scored under an identical harness. Over 73.5 seconds of held-out motion from ten events, the model reaches a median position error of 0.039 meters at the 0.4-second horizon, against 0.101 for ideal kinematics and 0.129 for rSim, the ODE engine of the rSoccer framework, which runs untuned and is reported as context; the model is lower in all ten events, and an order-independent ablation attributes the gain in comparable parts to the time constant and the dead time, conditional on the measured initial velocity. Since 99.6 percent of the hold-out windows are translation-dominated, rotational fidelity remains unvalidated, and a screening rule computable from the logs alone predicts which channels a log can identify.
\end{abstract}
```

Se precisar de espaço, a última frase pode cair até "unvalidated" e a menção ao rSim pode virar
"and 0.129 for an untuned ODE simulator".

### A2. Cabeçalhos run-in (R1: "section headers incorrectly merged into the body text")

Diagnóstico: no IEEEtran (conferência) tanto `\paragraph` quanto `\subsubsection` são cabeçalhos
*run-in* (itálico, dois-pontos automáticos, texto na mesma linha). O `\paragraph` não é numerado,
então aparece como uma frase em itálico colada ao parágrafo, que foi o que R1 leu como erro. A
troca mais barata e dentro do template é `\subsubsection`, que sai numerado ("1) Título: texto"),
formato padrão IEEE. Se quiser cabeçalho em linha própria, use `\subsection` (custa uma linha cada
e letra A, B, C).

Ocorrências na versão submetida e substituição:

| Arquivo | Linha atual | Trocar por |
|---|---|---|
| `02_related_work.tex` | `\paragraph{Behavioral twins of mobile robots}` | `\subsection{Behavioral twins of mobile robots}` |
| `02_related_work.tex` | `\paragraph{SSL simulators and league context}` | `\subsection{SSL simulators and league context}` |
| `02_related_work.tex` | `\paragraph{Closed-loop identification}` | `\subsection{Closed-loop identification}` |
| `03_method.tex` | `\paragraph{Definition of hold-out fit}` | apagar a linha; a frase seguinte já começa com "Throughout, \emph{fit} measures..." |
| `04_results.tex` | `\paragraph{What produces the improvement}` | `\subsubsection{What produces the improvement}` |
| `04_results.tex` | `\paragraph{The improvement needs the measured initial velocity}` | `\subsubsection{The role of the measured initial velocity}` |
| `04_results.tex` | `\paragraph{The ODE simulator}` | `\subsubsection{The untuned ODE simulator}` |
| `04_results.tex` | `\paragraph{Heading error}` | `\subsubsection{Heading error}` |
| `04_results.tex` | `\paragraph{Why the logs cannot constrain yaw}` | `\subsubsection{Why the logs cannot constrain yaw}` |
| `04_results.tex` | `\paragraph{The same structure, different data}` | `\subsubsection{The same structure on dedicated data}` |

Custo: as três `\subsection` de Related Work custam ~3 linhas; as `\subsubsection` custam zero.
Depois da troca, conferir que nenhum `\paragraph` sobrou (`grep -rn "\\\\paragraph" sections/`).

### A3. Tabelas II e III duplicadas

1. Baixar o PDF submetido no JEMS e localizar "TABLE III".
2. No fonte exportado só há dois `\input` de tabela (`tab_sysid_params` = Tab. I e
   `tab_three_models` = Tab. II). A explicação mais provável é que o PDF submetido ainda tinha
   `\input{tables/tab_twin_vs_rsim}` (colunas twin/rSim praticamente iguais às de `tab:three`,
   0.0382/0.1312 vs 0.039/0.129 em h_ref), ou um `\input{tables/tab_three_models}` repetido.
3. Manter apenas `tab:sysid` e `tab:three`; garantir que `\ref{tab:three}` é citada (IV-C, IV-C
   "Heading error", V-B) e que `tab_twin_vs_rsim.tex`, `tab_omega_regime.tex`, `tab_units.tex`
   e `tab_validation_composition.tex` não são inputados (ficam no diretório para a extensão).
4. Recompilar e conferir a sequência TABLE I, TABLE II no PDF.

### A4. Proofreading localizado (versão submetida)

| # | Arquivo | Como está | Como fica |
|---|---|---|---|
| 1 | `00_abstract.tex` | "Degree of Freedom (DoF)" | usar "degree of freedom (DOF)" como no corpo (o novo abstract em A1 já resolve) |
| 2 | `01_introduction.tex` | "...per parameter group \cite{giro2023otbot}, and real-time\nThe estimation for twins assumes informative operating data" | "...per parameter group \cite{giro2023otbot}, real-time estimation for twins assumes informative operating data" (o "and" fica só antes de "offline sim-to-real calibration", como no repositório) |
| 3 | `01_introduction.tex` (C4) | "This robot separates identifiable channels from unidentifiable ones before fitting a single parameter." | "On this robot it separates the identifiable channels from the unidentifiable one before a single parameter is fitted." |
| 4 | `02_related_work.tex` | "That feedback correlates the input with unmeasured disturbances, breaking methods that work in open loop are classic" | "That feedback correlates the input with unmeasured disturbances, breaking methods that work in open loop, is classic" |
| 5 | `03_method.tex` | "the \emph{plant layer} of a greater digital-twin effort" | "of a larger digital-twin effort" |
| 6 | `03_method.tex` (III-E) | "the ratio of the cennter to wheel-contact radius" | "the ratio of the center-to-wheel-contact radius" |
| 7 | `03_method.tex` (III-F) | a frase "$\epos$ is the claim of this paper; $\eang$ is reported but bounded by the population of rotation-rich windows available (Sec.~\ref{sec:results:bins})." está **dentro do comentário** `% source: config/metrics.json ...` e não aparece no PDF | mover para a linha seguinte, fora do comentário, e corrigir "(Sec .~\ref {" para "(Sec.~\ref{" |
| 8 | `03_method.tex` (III-G) | "It is driven at adjusted parameters for the teams robots." | ver A9 (erro factual) |
| 9 | `04_results.tex` (IV-C) | "the pre-registered window-level test agrees and is the less conservative of the two" | ok, mas acrescentar o n: "over the 49 non-overlapping windows" |
| 10 | `04_results.tex` (IV-D) | "Scored against the same placeholder on the same competition population" (placeholder nunca definido nesta versão) | "Scored against the same no-dynamics placeholder ($K=1$, $\tau=\SI{0.1}{s}$, $\Td=0$) on the same competition population" |
| 11 | `07_conclusion.tex` | "This paper presented a per-DOF FOPDT model of an omnidirectional SSL robot, identified mostly from closed-loop competition logs, attains validated translational fidelity:" | "This paper presented a per-DOF FOPDT model of an omnidirectional SSL robot, identified mostly from closed-loop competition logs, which attains validated translational fidelity:" |
| 12 | `07_conclusion.tex` | `\section{Conclusion and Further Works}` | `\section{Conclusion and Future Work}` |

Também: espaços duplos em "in  free run" (01), "one specific  physical asset" (01), "(b) The same   comparison" e "one of the   ten" (legenda da Fig. 2 em 04); `\SI{1}{s}` na legenda da Tab. II está correto. Rodar `chktex` ou o "Check" do Overleaf depois das trocas.

### A5. Desanonimização e metadados (camera-ready)

1. **Título.** O JEMS registrou "A Behavioral Model for Reality-Gap Mitigation in Digital Twins
   of Omnidirectional Soccer Robots" e é esse que está no `main.tex` submetido (a alternativa
   "…: Diagnosing Identifiability from Competition Logs" ficou comentada). As três revisões
   internas de agosto apontaram que "mitigation" promete transferência que o artigo não mede.
   Opções: (a) manter o título aceito (zero risco com os chairs); (b) trocar para o do repositório
   e avisar os chairs na submissão do camera-ready (mudanças de título costumam ser aceitas se
   comunicadas). Se escolher (b), copiar o `\title{}` de `Documents\digitaltwin\latex\main.tex`.
   Em qualquer caso o título do JEMS e o do PDF têm de coincidir.
2. **Autores e afiliações** no lugar de "Anonymous Author(s)":

```latex
\author{\IEEEauthorblockN{[Nome completo]\IEEEauthorrefmark{1},
[Coautor(a)]\IEEEauthorrefmark{1}}
\IEEEauthorblockA{\IEEEauthorrefmark{1}Centro de Inform\'atica, Universidade Federal de Pernambuco (CIn-UFPE), Recife, Brazil\\
RobôCIn Robotics Team \\ \{vhssa, ...\}@cin.ufpe.br}}
```

3. **Agradecimentos** (antes das referências): financiamento, RobôCIn, quem fez a coleta de
   rotação pura (04 e 05/07/2026, robô yellow #6) e o CAD.
4. **Repositório**: trocar `https://anonymous.4open.science/r/dt-ssl-sbr26-4207` pelo GitHub real
   + DOI Zenodo (`dtssl release` gera o pacote; item D3 do backlog, congelado). Se o DOI não sair a
   tempo, publicar o GitHub e reservar o DOI (Zenodo permite reservar antes de publicar).
5. **Keywords**: a versão submetida tem "digital twin, system identification, robot modeling,
   omnidirectional robot, robot soccer". Sugestão: acrescentar "grey-box modeling" e "excitation
   design" (estão no repositório) se couber na linha.
6. Retirar o bloco de comentários de decisão de título do `main.tex` (não afeta o PDF, mas o
   fonte vai para o Overleaf compartilhado).
7. Conferir os requisitos de IEEE Xplore no JEMS: formulário de copyright (eCF), PDF eXpress se
   exigido, fontes embutidas, tamanho de papel (o CFP de anos anteriores pedia A4; o `main.tex`
   já usa `a4paper`).

### A6. Figura do robô e do aparato (R2)

Inserir em III-C (Data and pre-processing), com a frase de chamada logo após a definição da
velocidade medida. Painel (a): foto do robô RobôCIn 2025 (quatro rodas omni visíveis, com escala).
Painel (b): foto do campo com as câmeras ou apenas o diagrama TikZ abaixo (compila sem foto).
Custo: ~0,25 página em coluna simples.

```latex
% III-C, apos "...and rotating the result into the body frame."
Fig.~\ref{fig:setup} shows the robot and the measurement chain: body velocity is never measured on board; it is derived offline from the vision pose, both for the competition logs and for the dedicated yaw collection.

\begin{figure}[!t]
  \centering
  \includegraphics[width=0.46\columnwidth]{robot_photo.jpg}\hfill
  \includegraphics[width=0.50\columnwidth]{field_photo.jpg}\\[3pt]
  \begin{tikzpicture}[
    every node/.style={font=\scriptsize},
    blk/.style={draw, rounded corners=2pt, align=center, inner sep=2.5pt, minimum height=0.6cm},
    ar/.style={-{Latex[length=1.5mm]}, semithick},
    arD/.style={-{Latex[length=1.5mm]}, semithick, dashed}
  ]
    \node[blk, text width=1.5cm] (cam)   at (0,0)    {SSL-Vision\\ 4 cameras, \SI{60}{Hz}};
    \node[blk, text width=1.5cm] (sw)    at (2.3,0)  {Team software\\ (closed loop)};
    \node[blk, text width=1.5cm] (radio) at (4.6,0)  {Radio base\\ station};
    \node[blk, text width=1.5cm] (robot) at (6.9,0)  {Robot: per-wheel\\ PI loops};
    \draw[ar] (cam) -- (sw)    node[midway, above] {pose};
    \draw[ar] (sw)  -- (radio) node[midway, above] {$v_x, v_y, \omega$};
    \draw[ar] (radio) -- (robot);
    \draw[ar] (robot.north) -- ++(0,0.5) -| (cam.north);
    \node[fill=white, inner sep=1pt] at (3.45,0.8) {motion observed on the field};
    \node[blk, dashed, text width=2.1cm] (log)   at (1.15,-1.15) {Protocol logger\\ commands + poses};
    \node[blk, dashed, text width=2.5cm] (stair) at (5.2,-1.15)  {Scripted yaw staircase\\ (open loop, $v_x=v_y=0$)};
    \draw[arD] (sw.south) -- (log.north);
    \draw[arD] (stair.north) -- (radio.south);
  \end{tikzpicture}
  \caption{(a) The four-wheeled omnidirectional SSL robot used in this work. (b) The field and its overhead vision cameras. (c) Measurement chain: the league vision system reports the field-frame pose at \SI{60}{Hz}; the team software closes the loop over radio; the protocol logger records commands and poses, which is all the identification consumes. Body velocities are derived offline from the vision pose (Sec.~\ref{sec:method:data}). For the dedicated yaw collection the same chain is driven open loop by a scripted staircase of yaw commands.}
  \label{fig:setup}
\end{figure}
```

Se só houver a foto do robô, apague a segunda `\includegraphics` e ajuste a legenda para (a)/(b).
Colocar as imagens em `figures/` (JPG com ~1000 px de largura basta; conferir legibilidade em
escala de cinza). O diagrama mede ~8,6 cm; se estourar a coluna, envolver o `tikzpicture` em
`\resizebox{\columnwidth}{!}{...}`.

### A7. Vídeos suplementares (R2)

O PDF só precisa do link; os vídeos ficam no YouTube (não listado) ou no Zenodo junto com o
pacote de reprodução. Dois vídeos de 2 a 3 minutos:

1. **Medição de velocidade e coleta de yaw.** Se existir filmagem da coleta de 04 e 05/07 (robô
   girando na escada de comandos), usar; se não, gravar a tela do `dtssl gui --mode replay` num
   evento de hold-out (`rotate_01_07`, +2,5 rad/s) mostrando, lado a lado, a pose de visão, a
   velocidade derivada (Savitzky-Golay + diferença central) e a resposta do modelo, e narrar a
   cadeia da Fig. de A6. Dizer explicitamente que a velocidade não é medida a bordo.
2. **Gêmeo em execução.** É o vídeo 1 do runbook D5 (`tools/demo/video1_dropin.sh gui`): a
   estratégia do RobôCIn jogando contra o gêmeo como se fosse o grSim, com a janela do gêmeo
   (campo 2D, aba Robot). Complementar com 30 s do replay de um evento de hold-out (trajetória
   real × modelo × ideal), que é a Fig. 2(b) em movimento.

Nota de rodapé para III-C (ou na Conclusão, junto do repositório):

```latex
\footnote{Supplementary videos (yaw collection and velocity extraction; the twin driven by the team's strategy): \url{https://youtu.be/XXXXXXXX}.}
```

### A8. Limitações explícitas: desacoplamento, slip, saturação, não linearidades (R1, R2)

Acrescentar ao fim de V-B (`05_discussion.tex`, subseção Limitations), depois de "...which the
matched-delay ablation narrows but does not remove.":

```latex
The model is also deliberately simple, and three simplifications bound where it applies. The channels are decoupled: no term maps a translational command into yaw or a yaw command into translation, although the $44\%$ of the measured rotation that the yaw command does not explain in play is, at least in part, translation-induced yaw (slip, contact and traction asymmetry), which is exactly what a coupled model would have to capture; a coupled (MIMO) identification on the same data is the natural next step and is not attempted here. The plant is linear, with no saturation, acceleration limit or dead-zone: it is fitted and scored inside the envelope of the logs, where the commanded speed exceeds $\SI{2.9}{m/s}$ (the rated limit is $\SI{3}{m/s}$) in $0.01\%$ of the competition samples and the dedicated yaw steps peak at about a quarter of the per-wheel PWM limit, so its validity in aggressive or mixed-motion regimes is unverified. Slip enters only through the identified gains and lags, never as a state.
% source: results/closed_loop_stats_20260907_2137.md (|v| > 2.9 m/s em 0.01 % do pool de competicao);
%   results/qc_rotate_20260724_021248.md sec. anomalia 2 (PWM max ~20.4 vs limite +-80 por roda);
%   config/robot_limits.json (v_max 3.0, sem a_max: "the published behavioral plant has NO saturation");
%   firmware ssl-embedded PID_Controller.cpp:157-164 (saturacao +-80 PWM), CHANGELOG 2026-06-13.
```

Custo: ~9 linhas. Se o orçamento apertar, cortar a última frase ("Slip enters...") e "(the rated
limit is 3 m/s)".

### A9. rSim: uma única afirmação, consistente (R1, R2)

Erro factual na versão submetida, III-G (Baselines): "It is driven at adjusted parameters for the
teams robots." O código (`src/dtssl/models/rsim.py`) instancia `robosim.SSL(...)` com os
parâmetros de fábrica do rSim; a Fig. 2 diz "an untuned rSim", V-B diz "fitted-versus-untuned" e o
abstract diz que roda sem sintonia. Trocar a frase por:

```latex
The second is \textbf{rSim}, the ODE-based physics engine of the rSoccer environment, run with its stock robot parameters and no fitting to these logs, so the comparison is between a plant fitted to this robot and an untuned engine; it is reported as context, not as the primary comparison. The recorded body-frame commands enter it directly, with its wheel-speed input and motion controller disabled, and it is stepped in \SI{1}{ms} substeps interpolated back onto the $1/60\,\si{s}$ grid. rSim has no velocity setter at reset, so each window warms it up over the $15$ real pre-anchor commands before a rigid $\SEtwo$ re-anchor at $t_0$; the dead-time term of the twin has no counterpart in it.
% source: src/dtssl/models/rsim.py (robosim.SSL(field_type,1,0,sub_ms,...); wheel_speed=False; warm-up Lw=15)
```

Se a frase original tinha a intenção de dizer que os parâmetros do rSim descrevem uma geração
anterior do robô do próprio time (o rSoccer é do mesmo grupo), isso pode entrar como "whose stock
parameters describe an earlier generation of this team's robot", desde que seja verdade e
verificável no rSoccer; caso contrário, deixar como acima.

## 3. Faixa B: recomendadas (dependem do orçamento de páginas e da decisão D1)

### B1. O mecanismo do viés de ω medido in silico (responde ao "acoplamento ignorado" com dado)

Parágrafo curto para V-A, depois de "...because the dedicated collection removes both at once.":

```latex
An in-silico check makes the coupling explicit. Replaying the competition commands through a physics simulation of the same robot with rolling omni wheels (four wheels, twelve rollers each, no tuning) and re-identifying yaw with the estimator of this paper inflates the yaw gain by $16$ to $27\%$, in the direction of the closed-loop bias, whereas the same commands with the translational components zeroed show no inflation (gains between $0.93$ and $0.99$), and the dedicated staircase returns $0.996$. The bias is therefore translation-induced yaw correlated with the strategy's yaw commands: a coupling the decoupled channel cannot represent and the dedicated collection removes.
% source: results/identifiability_insilico_mujoco-rollers-delay_v2_20260907_2044.json (K_w R1 none/off 1.160 = +16.5 %,
%   R1 vision/on 1.270 = +27.4 %, R1-wonly none/off 0.988, R1-wonly vision/on 0.930, R2-rotate 0.996) e
%   ..._mujoco-rollers_v2_20260907_2048.json (+16.1 % / +14.7 %, R1-wonly 0.988);
%   CHANGELOG 2026-09-07 20:45 (C1b v2, pre-registro docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_V2_20260907.md)
```

Custo: ~7 linhas. É resultado novo em relação à versão revisada; camera-ready costuma admitir
acréscimos desse tamanho, mas é a decisão D1 (congelada com a orientadora em 11/09).

### B2. Simuladores da liga no mesmo harness (responde ao "untuned rSim" sem sintonizar nada)

Uma frase para IV-C, no parágrafo "The untuned ODE simulator", ou para V-B:

```latex
The finding does not hinge on rSim: grSim and the ER-Force simulator, driven through the league simulation protocol on the same windows, with grSim pre-rolled over the real command prefix so that it reaches the anchor with its own dynamics rather than from rest, give per-event median errors of $\SI{0.098}{m}$ and $\SI{0.100}{m}$ at $h_{\mathrm{ref}}$ against $\SI{0.042}{m}$ for the model, ten wins out of ten each ($p = 9.8\times10^{-4}$). None of the three engines is tuned to this robot, which is the limitation the comparison carries.
% source: results/protocol_holdout_20260920_1143.md (grsim+preroll 0.0975 m, erforce 0.0995 m por evento, gemeo 0.0421 m,
%   10/10, Wilcoxon p = 9.8e-4, rank-biserial +1.00); CHANGELOG 2026-09-20 11:43 (C2b2) e 2026-09-10 02:11 (C2b)
```

Atenção às unidades: esses são medianos **por evento** (a Tab. II é por janela; por janela os
valores são 0,0809 e 0,0874 m contra 0,0388 m). Custo: ~6 linhas.

### B3. Checagem MIMO barata, com critério fixado antes de rodar

R2 pede "joint or coupled identification (e.g., a MIMO model)". A versão completa é assunto da
extensão (§4); a checagem abaixo cabe numa tarde e produz uma frase para o camera-ready, em
qualquer dos dois desfechos. Regra do projeto: pré-registro antes de rodar, artefato em `results/`,
entrada no CHANGELOG, e o θ oficial não muda.

**Pré-registro (salvar como `docs/PREREGISTRO_MIMO_CHECK_<data>.md` antes de executar):**

- Pergunta: acrescentar termos cruzados de comando (b_ij, i ≠ j) ao mesmo modelo de primeira ordem
  melhora o fit de hold-out sobre a estrutura desacoplada, com o mesmo estimador e os mesmos dados?
- Dados: os 46 eventos de competição, grade legada 1/60 s (`C.legacy_uy_series`, posições mm → m),
  hold-out = os 10 eventos congelados de `config/holdout_events.json`; treino = os outros 36.
- Modelo por saída i: v_i[k] = a_i v_i[k-1] + Σ_j b_ij u_j[k − m_i], com m_i = ceil(Td_i/dt) do θ
  promovido (atrasos não reestimados). Braço desacoplado: b_ij = 0 para i ≠ j, mesmo estimador.
  Terceiro braço: o FOPDT promovido, simulado na mesma grade, como âncora dos números publicados.
- Estimador: mínimos quadrados por saída (erro de equação) no treino. Pontuação: simulação livre
  da velocidade a partir dos comandos no hold-out, v inicializado no y medido, fit % da Eq. (2)
  por DOF e por evento; opcionalmente e_pos por evento no harness (planta acoplada abaixo).
- Critério: o acoplamento "importa" se o braço acoplado melhora o fit médio de hold-out em ≥ 3 p.p.
  em algum DOF **e** algum ganho estático cruzado g_ij = b_ij/(1 − a_i) excede 10 % do ganho
  diagonal da mesma saída em módulo. Caso contrário, "não importa neste envelope".
- Frase para o artigo, desfecho 1 (importa): "A coupled first-order model with cross-command
  terms, fitted on the same training events, raises the hold-out fit of [DOF] by [x] p.p.; the
  cross gains are [valores], so coupling is measurable and is left to a full MIMO identification."
  Desfecho 2 (não importa): "A coupled first-order model with cross-command terms, fitted with the
  same estimator on the same training events, changes the hold-out fit by less than [x] p.p. on
  every DOF and its cross gains stay below [y] % of the diagonal ones, so within the envelope of
  these logs the decoupled structure loses nothing measurable; aggressive mixed motion is where a
  coupled model would have to be tested."

**Módulo (`src/dtssl/analysis/coupled_mimo_check.py`, segue o padrão de `r3_closedloop_omega_fit`
e `loo_translational`; registrar em `dtssl.analysis` como os demais):**

```python
"""Coupled (MIMO) first-order check: do cross-command terms between vx, vy and w
improve hold-out fit over the per-DOF (decoupled) structure, same data, same estimator?

Model per output i (uniform grid dt, ZOH):
    v_i[k] = a_i v_i[k-1] + sum_j b_ij u_j[k - m_i]        coupled: full B (3x3)
    diagonal arm: b_ij = 0 for i != j                       same least-squares estimator
m_i = ceil(Td_i/dt) from the promoted theta (delays NOT re-estimated). Third arm: the
promoted per-DOF FOPDT simulated on the same grid (anchor for the published fits).
Train = all competition events except the frozen hold-out; test = config/holdout_events.json.
Pre-registration: docs/PREREGISTRO_MIMO_CHECK_<date>.md. Does NOT touch config/twin_params.json.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from dtssl.analysis import common as C

NAME = "coupled_mimo_check"
KIND = "analysis"
CLAIM = "Cross-coupling check: coupled 3x3 first-order model vs per-DOF on the frozen hold-out"
REQUIRES = ("data",)
SEED = 42
LABELS = ("front_to_back", "side_to_side", "shoot_to_goal", "square")
DOFS = ("vx", "vy", "w")
POS_SCALE = 1e-3            # logged mm -> m (same as loo_translational)
GAIN_RATIO_MIN = 0.10       # pre-registered: cross gain >= 10 % of the diagonal gain
FIT_GAIN_MIN_PP = 3.0       # pre-registered: >= 3 p.p. on some DOF


def _uy_all(cmd, rob, dt, min_len=60):
    """(U, Y) as N x 3 arrays on the shared legacy grid, or None if too short."""
    cols = []
    for d in DOFS:
        s = C.legacy_uy_series(cmd, rob, d, dt, min_len=min_len, pos_scale=POS_SCALE)
        if s is None:
            return None
        cols.append(s)
    n = min(len(u) for u, _ in cols)
    return np.column_stack([u[:n] for u, _ in cols]), np.column_stack([y[:n] for _, y in cols])


def _delayed(U, m):
    Ud = np.zeros_like(U)
    if 0 < m < len(U):
        Ud[m:] = U[: len(U) - m]
    elif m == 0:
        Ud[:] = U
    return Ud


def fit_ls(events, m, coupled: bool):
    """Per-output least squares on the training events (equation error)."""
    A = np.zeros(3); B = np.zeros((3, 3))
    for i in range(3):
        rows, rhs = [], []
        for U, Y in events:
            Ud = _delayed(U, m[i])
            cols = [Y[:-1, i]] + [Ud[1:, j] for j in (range(3) if coupled else (i,))]
            rows.append(np.column_stack(cols)); rhs.append(Y[1:, i])
        th, *_ = np.linalg.lstsq(np.vstack(rows), np.concatenate(rhs), rcond=None)
        A[i] = th[0]
        if coupled:
            B[i, :] = th[1:]
        else:
            B[i, i] = th[1]
    return A, B


def simulate(U, y0, A, B, m):
    """Free-run velocity simulation driven only by the commands (v[0] = measured y[0])."""
    n = len(U); V = np.zeros((n, 3)); V[0] = y0
    Ud = [_delayed(U, m[i]) for i in range(3)]
    for k in range(1, n):
        for i in range(3):
            V[k, i] = A[i] * V[k - 1, i] + B[i] @ Ud[i][k]
    return V


def compute(ctx: C.Ctx, min_len: int = 60) -> dict:
    dt = ctx.ts
    ho_ids = {(e["label"], e["event"]) for e in ctx.holdout_cfg["events"]}
    train, test = [], []
    for label in LABELS:
        for ev in C.list_events(ctx.splits_dir, label):
            cmd, rob = C.read_event_csv(label, ev, dataset=ctx.dataset, data_root=ctx.data_root)
            s = _uy_all(cmd, rob, dt, min_len)
            if s is None:
                continue
            (test if (label, ev) in ho_ids else train).append((label, ev) + s)
    P = ctx.params
    m = [int(math.ceil(P[d].Td / dt)) for d in DOFS]           # legacy alignment
    ev_tr = [(U, Y) for _, _, U, Y in train]
    A_c, B_c = fit_ls(ev_tr, m, coupled=True)
    A_d, B_d = fit_ls(ev_tr, m, coupled=False)
    G_c = B_c / (1.0 - A_c)[:, None]                            # steady-state gains
    G_d = B_d / (1.0 - A_d)[:, None]

    fits = {"coupled": [], "diagonal": [], "promoted": []}
    for label, ev, U, Y in test:
        Vc = simulate(U, Y[0], A_c, B_c, m)
        Vd = simulate(U, Y[0], A_d, B_d, m)
        Vp = np.column_stack([C.simulate_fopdt(U[:, i], dt, P[d].K, P[d].tau, P[d].Td,
                                               ic=Y[0, i] / P[d].K, align="legacy")
                              for i, d in enumerate(DOFS)])
        for key, V in (("coupled", Vc), ("diagonal", Vd), ("promoted", Vp)):
            fits[key].append(dict(label=label, event=ev,
                                  **{d: C.fit_percent(Y[:, i], V[:, i]) for i, d in enumerate(DOFS)}))
    mean = {k: {d: float(np.mean([f[d] for f in v])) for d in DOFS} for k, v in fits.items()}
    delta = {d: mean["coupled"][d] - mean["diagonal"][d] for d in DOFS}
    ratio = {DOFS[i]: max(abs(G_c[i, j]) / max(abs(G_c[i, i]), 1e-9) for j in range(3) if j != i)
             for i in range(3)}
    verdict = any(delta[d] >= FIT_GAIN_MIN_PP for d in DOFS) and any(ratio[d] >= GAIN_RATIO_MIN for d in DOFS)
    return dict(n_train=len(train), n_test=len(test), m=m, A_c=A_c.tolist(), B_c=B_c.tolist(),
                G_c=G_c.tolist(), A_d=A_d.tolist(), G_d=G_d.tolist(), fits=fits, mean=mean,
                delta_pp=delta, cross_gain_ratio=ratio, coupling_matters=bool(verdict))


def render(ctx: C.Ctx, r: dict) -> list[str]:
    L = C.result_header("Checagem MIMO: termos cruzados vs. estrutura por DOF", ctx,
                        generator=f"dtssl.analysis.{NAME}", seed=SEED,
                        extra=f"m={r['m']} (ceil(Td/dt), atrasos fixos)")
    L += [f"- treino {r['n_train']} eventos / hold-out {r['n_test']} (config/holdout_events.json)", "",
          "| braco | fit vx | fit vy | fit w |", "|---|---|---|---|"]
    for k in ("promoted", "diagonal", "coupled"):
        L.append(f"| {k} | " + " | ".join(f"{r['mean'][k][d]:.1f} %" for d in DOFS) + " |")
    L += ["", "Ganhos estaticos do braco acoplado G = B/(1-A) (linha = saida, coluna = comando):", ""]
    for i, d in enumerate(DOFS):
        L.append(f"- {d}: " + ", ".join(f"{g:+.3f}" for g in r["G_c"][i]))
    L += ["", f"- delta acoplado - diagonal (p.p.): " + ", ".join(f"{d} {r['delta_pp'][d]:+.1f}" for d in DOFS),
          f"- razao |g_ij|/|g_ii| maxima por saida: " + ", ".join(f"{d} {r['cross_gain_ratio'][d]:.2f}" for d in DOFS),
          f"- **criterio pre-registrado (>= {FIT_GAIN_MIN_PP} p.p. e razao >= {GAIN_RATIO_MIN}): "
          f"{'ACOPLAMENTO IMPORTA' if r['coupling_matters'] else 'nao importa neste envelope'}**"]
    return L


def run(root: Path | None = None, out: Path | None = None, *, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out, seed=SEED)
    r = compute(ctx)
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    if not quiet:
        print("\n".join(L)); print(f"\nartefato: {p}")
    r["path"] = p
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
```

Execução: `dtssl analysis run coupled_mimo_check` (ou `python -m dtssl.analysis.coupled_mimo_check`).
Verificação de sanidade antes de acreditar no resultado: o braço `promoted` deve reproduzir os fits
publicados nos eventos de hold-out de `front_to_back`/`side_to_side` (86,7 % e 87,1 % na média dos
eventos daqueles rótulos; aqui a média é sobre os 10 eventos, então compare por evento com
`results/fit_holdout_vxvy_20260731_024049.csv`).

**Para pontuar e_pos no harness (opcional):** uma planta acoplada com a mesma interface
`Plant` (reset / prime_delay / step), depois `C.ros(segs, factory)` e `C.paired_table(ctx, ros_coupled, ros_promoted)`
+ `C.per_event_medians(table, k_ref)` como em `backends_holdout.py`:

```python
import math
import numpy as np
from dtssl.models.base import Plant


class CoupledFirstOrderPlant(Plant):
    """v[k] = A v[k-1] + B u_d[k], u_d delayed per OUTPUT by m_i samples; trapezoidal pose
    integration identical to AnalyticFOPDTPlant."""

    def __init__(self, A, B, m):
        self.A = np.asarray(A, float).reshape(3)
        self.B = np.asarray(B, float).reshape(3, 3)
        self.m = [int(x) for x in m]

    def reset(self, pose0, velb0=(0.0, 0.0, 0.0)):
        self.x, self.y, self.th = (float(v) for v in pose0)
        self._vbody = np.asarray(velb0, float).reshape(3).copy()
        c, s = math.cos(self.th), math.sin(self.th)
        self._gx_prev = c * self._vbody[0] - s * self._vbody[1]
        self._gy_prev = s * self._vbody[0] + c * self._vbody[1]
        self._vw_prev = float(self._vbody[2])
        self._hist, self._base, self._k = [], 0, 0

    def prime_delay(self, prev_cmds):
        self._hist = [np.asarray(c, float).reshape(3) for c in prev_cmds]
        self._base = len(self._hist)

    def step(self, cmd, dt):
        j = self._k
        self._hist.append(np.asarray(cmd, float).reshape(3))
        v_new = np.empty(3)
        for i in range(3):
            pos = j - self.m[i] + self._base
            ud = self._hist[pos] if 0 <= pos < len(self._hist) else np.zeros(3)
            v_new[i] = self.A[i] * self._vbody[i] + self.B[i] @ ud
        th_new = self.th + 0.5 * dt * (v_new[2] + self._vw_prev)
        c, s = math.cos(th_new), math.sin(th_new)
        gx, gy = c * v_new[0] - s * v_new[1], s * v_new[0] + c * v_new[1]
        self.x += 0.5 * dt * (gx + self._gx_prev)
        self.y += 0.5 * dt * (gy + self._gy_prev)
        self.th = th_new
        self._vbody, self._gx_prev, self._gy_prev, self._vw_prev = v_new, gx, gy, float(v_new[2])
        self._k = j + 1
        return (self.x, self.y, self.th)
```

Atenção ao alinhamento do atraso: `fit_ls` usa a convenção legada (m = ceil(Td/dt), comando atrasado
no mesmo índice); a planta do harness usa a convenção "plant" (comando de k−1 produz v em k), então
para levar (A, B) ao harness use `m_plant = m_legacy - 1` (ver docstring de `common.simulate_fopdt`).

**Alternativa em MATLAB (System Identification Toolbox), se preferir o mesmo estimador do artigo:**

```matlab
% iddata multicanal na grade uniforme Ts = 1/60 (mesmo pre-processamento de identify_trans_dof.m):
% saidas [vx vy w] medidas no corpo, entradas [ux uy uw] comandadas; um iddata por evento,
% merge dos de treino em z e o hold-out em zho. Atrasos do theta promovido, FIXOS (valor numerico
% em tfest e tratado como fixo; NaN mandaria estimar).
Td0 = [0.0691 0.0565 0.0890];
opt = tfestOptions('InitialCondition', 'estimate');
for i = 1:3
    sysDiag{i} = tfest(z(:, i, i), 1, 0, Td0(i), opt);                                % so o proprio comando (P1D)
    sysMIMO{i} = tfest(z(:, i, :), ones(1,3), zeros(1,3), Td0(i)*ones(1,3), opt);     % os tres comandos, 1 polo cada
    [~, fitDiag(i)] = compare(zho(:, i, i), sysDiag{i});     % compare = simulacao, nao predicao
    [~, fitMIMO(i)] = compare(zho(:, i, :), sysMIMO{i});
    G = dcgain(sysMIMO{i});                                   % ganhos estaticos [g_i1 g_i2 g_i3]
end
```

(`compare` devolve o fit em % da Eq. (2); usar a media sobre os eventos de hold-out como no artigo.)

### B4. rSim sintonizado (R2)

Sintonizar os poucos parâmetros do rSim (aceleração máxima, massa, atrito) contra os eventos de
treino com a mesma otimização bayesiana usada no controle negativo, e pontuar no hold-out. É o
análogo do C3 (calibrar a rota b do MuJoCo), congelado até a orientadora decidir. Não cabe no
camera-ready; vai para §4 como experimento da extensão. No camera-ready, B2 já mostra que o
resultado não depende do rSim e A9 declara a assimetria fitted-vs-untuned sem ambiguidade.

## 4. O que fica para a extensão (qualquer periódico)

Conteúdo novo suficiente para uma extensão substancial (a regra de bolso da Elsevier e da IEEE é
30 a 50 % de material novo, citando explicitamente o artigo do SBR):

1. Identificação acoplada (MIMO) completa: B3 com atrasos reestimados por par (i, j), IC por
   bootstrap sobre eventos, e_pos no harness; mais o mecanismo in silico (C1 e C1b, com as duas
   plataformas e o padrão robusto R1 inflado / R1-wonly ≈ 0,99 / R2-rotate 0,996).
2. Baselines justas: grSim e ER-Force via protocolo com pré-rolagem (C2b/C2b2), gêmeo físico
   MuJoCo sem sintonia e com atraso (C2a: 0,073 e 0,048 m), e, se a orientadora aprovar, a rota b
   ou o rSim sintonizados (C3/B4) como "gêmeo físico sintonizado".
3. Validação em malha fechada (C4): a estratégia jogando contra o gêmeo produz estatísticas de
   comando indistinguíveis do rótulo de jogo (5/5 contra `shoot_to_goal`), e o round trip
   gravador → harness fecha ao nível do mm (B3 sessão gravada).
4. O gêmeo como instrumento: servidor ssl-simulation-protocol, drop-in do ssl-unification (185 s a
   60 Hz, watchdog 0), qualquer simulador externo pontuado pelo mesmo harness.
5. Tudo do `docs/BACKLOG_EXTENSAO_JINT.md`: limitações completas, figura de fit vx/vy, painel de
   bins, Modo B, controle negativo em detalhe, related work com os eixos (a)/(c) e a SLR.
6. Validação rotacional numa distribuição rica em rotação e o braço open-loop com translação
   superposta: dependem de coleta nova no laboratório (pergunta 5 da reunião de 11/09).

## 5. Special issue "Digital Twin International Conference 2026" (ScienceDirect 334590)

*Atualizado em 23/09 com o texto integral da página, colado pelo Victor.*

### 5.1 Fatos verificados

- Periódico: **Digital Engineering** (Elsevier, ISSN 2950-550X, open access, EIC Prof. Fei Tao).
  Article type no Editorial Manager: **`VSI:DTE_DigiTwin2026`**. Datas: submissão aberta desde
  01/07/2026, **fecha em 28/02/2027**, editorial deadline 31/05/2027 (decisões até lá). Revisão por
  pelo menos dois pareceristas independentes.
- Elegibilidade: **aberta**. O texto diz "You are invited to submit your manuscript at any time
  before the submission deadline", "organized in conjunction with" a DigiTwin 2026 e "welcomes
  original research articles, reviews, and industrial case studies". Não há nenhuma cláusula de
  "papers presented at" nem "by invitation"; ter ido a Oxford não é requisito.
- Contato para dúvida de adequação de tema: executive guest editor **Zhiqiang Wang** (ESILV,
  Zhiqiang.wang@devinci.fr). Há um guest editor brasileiro (Fábio José Pinheiro Sousa, UFRN), útil
  como segundo contato, mas o canal oficial é o Wang.
- APC: a página do periódico informa APC gratuita para submissões até 31/12/2026 e USD 1.830
  depois. Indexação: EI Compendex e CiteScore 5.7 (Scopus); JCR/WoS não localizado. Conferir no
  Scopus Sources o percentil do CiteScore e, na Sucupira, o Qualis que o PPGCC reconhece.
- Escopo: o artigo cai em três tópicos da lista: "Physics-based, data-driven, and hybrid digital
  twin modeling" (grey-box = híbrido), "Verification, validation, uncertainty quantification, and
  reliability" (protocolo de fidelidade, gates pré-registrados, identificabilidade) e
  "Cyber-physical systems and virtual-physical integration" (o gêmeo como drop-in via protocolo da
  liga). Robótica não aparece na lista de tópicos, mas "interdisciplinary applications" sim, e o
  escopo da conferência cita robótica explicitamente. As keywords da SI puxam para IA/ML e
  manufatura: a extensão deve se apresentar como metodologia de modelagem e validação de gêmeos a
  partir de dados operacionais, com o robô de futebol como caso, e não como artigo de robótica.

### 5.2 A única cláusula que exige cuidado

"Submitted manuscripts should present original contributions and must not have been previously
published nor be currently under consideration for publication elsewhere." É a cláusula padrão de
originalidade da Elsevier e não proíbe versões estendidas de artigo de conferência, mas também não
as menciona. Três providências fecham o risco:

1. Perguntar ao Wang antes de submeter (e-mail em §5.4); guardar a resposta.
2. Fazer da extensão um trabalho novo, não uma versão longa: título e abstract novos, texto
   reescrito (o texto do SBR terá copyright IEEE; figuras próprias podem ser reutilizadas com
   citação), pelo menos metade do conteúdo novo (§4 dá mais do que isso), e o artigo do SBR citado
   na introdução: "A preliminary version of this work appeared in [SBR 2026]; this article adds ...".
3. Declarar a versão de conferência na carta de submissão (modelo em §5.6) e anexar o PDF do SBR
   como material para os editores, se o Editorial Manager permitir.

Enquanto o manuscrito estiver na *Digital Engineering* ele não pode estar em nenhum outro lugar
(JINT incluída).

### 5.3 Leitura e recomendação

Prós: aberta a não apresentadores; prazo confortável; APC zero se submeter até 31/12/2026;
comunidade de gêmeos digitais, que é o tema da tese; não depende de convite (a JINT do LARS/SBR
convida só artigos selecionados, e com R1 neutro e R2 weak accept o convite não é garantido);
decisão até maio de 2027, que cabe no calendário da qualificação. Contras: periódico novo (2024),
sem JCR conhecido, e possivelmente com menos peso num comitê de robótica do que JINT ou RAS; o
prazo de dezembro colide com a SLR (M3 em 02/10) e com a qualificação; a lista de tópicos não
nomeia robótica, então a adequação de tema deve ser confirmada com o Wang.

Recomendação: sim, mandar a extensão para essa SI, com o eixo "identificabilidade por regime +
acoplamento + baselines justas" (§4 itens 1, 2, 3 e 5), submetida em dezembro; o eixo "gêmeo como
instrumento" (§4 item 4) vira um artigo de ferramenta separado (RoboCup Symposium 2027 ou JINT se
o convite vier), sem sobreposição de resultados. Decidir com a orientadora junto com D1.

### 5.4 E-mail ao executive guest editor (em inglês)

> Subject: Scope and eligibility question, VSI:DTE_DigiTwin2026 (Digital Engineering)
>
> Dear Dr. Wang,
>
> I am a PhD student at CIn-UFPE (Brazil) working on behavioral digital twins of omnidirectional robots. We have a paper accepted at the IEEE Latin American Robotics Symposium / Brazilian Symposium on Robotics 2026 (grey-box identification of a per-DOF plant from competition logs, with a data-driven identifiability diagnosis and a pre-registered fidelity validation protocol) and we are preparing a substantially extended journal version: coupled (MIMO) identification, in-silico identifiability analysis, physics-based and league-simulator baselines scored under the same protocol, and closed-loop validation of the twin.
>
> Two questions before we submit to the Special Issue: (1) is a substantially extended version of a conference paper acceptable, with the conference version cited and more than half of the material new? (2) Is the topic, a data-driven and hybrid twin of a mobile robot with a validation and identifiability methodology, within the scope you have in mind for the issue?
>
> Thank you for your time.

### 5.5 Cronograma proposto

| Quando | O quê |
|---|---|
| até o prazo do JEMS (outubro) | camera-ready (Faixa A, mais B se couber); e-mail ao Wang; conferir Qualis/percentil |
| outubro | rodar B3 (MIMO) e B4 (rSim ou rota b sintonizada, se a orientadora aprovar C3); fechar C2b2 e C4 como seções |
| novembro | apresentação no SBR (os vídeos do camera-ready servem para a fala); esqueleto da extensão |
| dezembro | texto completo, revisão da orientadora, submissão até 31/12 (APC zero) |
| até 28/02/2027 | prazo final se dezembro não fechar |

### 5.6 Carta de submissão (esboço, em inglês)

> This manuscript is submitted to the Special Issue VSI:DTE_DigiTwin2026. A preliminary six-page version of part of this work was accepted at the IEEE Latin American Robotics Symposium / Brazilian Symposium on Robotics 2026 (LARS/SBR 2026) and is cited as [ref]. The present article is a substantial extension: it adds [coupled identification, in-silico identifiability analysis, three additional baselines scored under the same protocol, closed-loop validation], rewrites the text throughout, and more than doubles the experimental material. The manuscript is not under consideration elsewhere.

## 6. Orçamento de páginas e menu de cortes

| Item | Δ estimado |
|---|---|
| A1 novo abstract (mais longo que o submetido) | +4 linhas |
| A2 `\subsection` em Related Work | +3 linhas |
| A4 frase de III-F que estava comentada | +2 linhas |
| A6 figura robô + aparato (coluna simples) | +0,25 pág. |
| A8 limitações | +9 linhas |
| A9 rSim (frase mais longa) | +3 linhas |
| **Subtotal Faixa A** | **≈ +0,45 pág.** |
| B1 + B2 | +13 linhas (≈ +0,15 pág.) |
| B3 (uma frase) | +3 linhas |

Cortes, na ordem, se o limite for 6 páginas:

1. Fig. 3 (`trajectory_by_label_en.png`, figure* de largura dupla, casos "melhor margem" por
   rótulo): ~0,30 pág. É a candidata natural a dar lugar à figura do robô, que foi pedida pelo
   revisor; a Fig. 2(b) e a Tab. II já carregam a mesma evidência.
2. Fig. 1 (arquitetura, figure*): ~0,30 pág.; o parágrafo de escopo de III já a descreve em prosa.
3. Reduzir a Fig. 2 para `width=0.80\textwidth` (~3 linhas) e a nota de rodapé da Tab. I para
   duas linhas.
4. V-A, segundo parágrafo: as duas últimas frases ("This removes the reading... removes both at
   once") podem cair se B1 entrar, porque B1 diz a mesma coisa com um número.

## 7. Checklist do camera-ready (JEMS)

- [ ] Prazo e limite de páginas confirmados no JEMS; título do JEMS = título do PDF.
- [ ] A1 a A9 aplicados; `grep -rn "\\\\paragraph\|anonymous\|Anonymous\|withheld\|TODO" sections/ main.tex` vazio.
- [ ] Tabelas: só TABLE I e TABLE II no PDF; figuras numeradas na ordem de citação.
- [ ] Autores, afiliações, e-mails, agradecimentos, financiamento; URL do repositório real; DOI reservado.
- [ ] Vídeos publicados e link testado; figura do robô com resolução suficiente.
- [ ] Bibliografia: as 19 chaves citadas existem no `.bib` (`katyara2024benchmarking` está no .bib
      e não é citada; inofensivo, o BibTeX ignora). `giro2023otbot`, `machado2025planning` e
      `martins2021rsoccer` são @misc: conferir se têm arXiv/DOI e ano no PDF final.
- [ ] Compilar limpo (0 erros, 0 referências indefinidas, sem `\TODO`), A4, fontes embutidas;
      PDF eXpress e copyright IEEE se o JEMS pedir.
- [ ] Guardar o PDF final e o fonte na pasta do OneDrive e no repositório (`latex/`), com o log.

## 8. Nota para os chairs (se houver campo de "summary of changes")

> Changes for the camera-ready: abstract rewritten as a single paragraph; run-in paragraph headings replaced by numbered IEEE subsubsections; the duplicated table removed; a figure of the robot and of the measurement chain added, with links to two supplementary videos (yaw collection and velocity extraction; the twin driven by the team's strategy); the baseline description of rSim corrected to state that it runs untuned; the Limitations subsection extended to state the decoupled structure, the absence of slip, saturation and other nonlinearities, and the translation-dominated hold-out; typographical corrections throughout. No number or claim of the reviewed version was changed.

## 9. Apêndice: diferenças entre a versão submetida (OneDrive) e o repositório

O `Documents\digitaltwin\latex` tem uma versão mais longa (título de 10/08, keywords com "grey-box
modeling, excitation design", parágrafos "Statistical gate", "Horizon grid", "Baselines" completo
com Modos A/B, controle negativo bayesiano, dedução do limiar por roda, leave-one-out na Tab. I).
A versão submetida cortou isso para caber em 6 páginas e acrescentou a Fig. 3 (`fig:trajlabels`).
Use a **versão do OneDrive como base do camera-ready** (é a que foi avaliada) e puxe do repositório
só o que os itens acima pedem (definição do placeholder, Baselines). Depois do camera-ready, copiar
a versão final para `latex/` no repositório e registrar no CHANGELOG, para a extensão partir dela.
