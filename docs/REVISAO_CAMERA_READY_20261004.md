# Revisão do camera-ready contra os pareceres: SBR/LARS 2026, #34344

*04/10/2026. Base: `C:\Users\victo\Documents\digitaltwin\latex` como está hoje (suas revisões
pontuais aplicadas). Compilei uma cópia com `pdflatex` + `bibtex` (IEEEtran.cls do projeto,
`IEEEtranM.bst`, que renderiza igual ao `IEEEtran.bst`, e a foto do robô reduzida só para medir o
layout): cada contagem de páginas abaixo vem de uma compilação limpa (aux apagado, quatro passadas).
Nada foi alterado no artigo além do arquivo novo `sections/05_discussion_enxuta.tex`.*

## 1. Páginas

| Variante (compilação limpa) | Páginas | Observação |
|---|---|---|
| Como está hoje | **7** | só as referências [18] e [19] caem na página 7 (4 linhas) |
| Seção V enxuta, nada mais | 6 | cabe, mas sem folga: 2 linhas a mais já viram página 7 |
| Seção V enxuta + correções obrigatórias do §3 | 7 | as correções custam ~5 linhas (frase do rSim, legenda, placeholder) |
| Seção V enxuta + correções + Fig. 5 em `width=0.90\textwidth` | **6** | folga de pelo menos 9 linhas; é a configuração que recomendo |

A Fig. 5 (`trajectory_by_label_en.png`, `figure*` em 0,98 da largura) é o maior item da página 5 e
o que decide onde as referências terminam. Reduzir para 0,90 custa 1,5 cm de altura e nenhuma
legibilidade (os quatro painéis continuam com mais de 7 cm de largura). Alternativa equivalente:
0,85. Se preferir não tocar na figura, a Seção V teria de perder mais 6 linhas; não recomendo,
porque o que sobra lá é o que os revisores pediram.

No Overleaf, use "Recompile from scratch" ao conferir: com `aux` velho o LaTeX chegou a me dar 7
páginas para um fonte que, limpo, dá 6.

## 2. Pareceres: o que já está resolvido e o que falta

| # | Pedido | Estado hoje | O que falta |
|---|---|---|---|
| R2 | abstract em um parágrafo | feito | opcional: "identify the channel using a 71 percent hold-out fit" → "reaching a 71 percent hold-out fit"; e "0.129 for rSim, an ODE simulator widely used across the league" → "0.129 for an untuned rSim, the ODE engine of the league's reinforcement-learning framework" (consistente com a Fig. 4 e com V) |
| R1 | cabeçalhos "colados" ao texto | feito: nenhum `\paragraph` sobrou (Related Work em `\subsection`, Results em parágrafos corridos) | nada |
| R1 | Tab. II = Tab. III | feito: só Tab. I e Tab. II no fonte | conferir no PDF do JEMS que a duplicata vinha de lá |
| R1 | proofreading | parcial | §3 itens 1, 4, 5 (um deles é texto estranho que apareceu no PDF depois da sua edição) |
| R1, R2 | rSim não sintonizado / sintonia | **pendente, e é erro factual**: III-G diz "driven at adjusted parameters for the teams robots", mas o código (`src/dtssl/models/rsim.py`) usa os parâmetros de fábrica, e a Fig. 4, o abstract e V dizem "untuned" | §3 item 2 |
| R1, R2 | acoplamento / MIMO; slip, saturação, não linearidades | **pendente** | entra na V enxuta como limitação explícita (§4); MIMO fica para o periódico, como você decidiu |
| R1, R2 | validação rotacional ausente; yaw de uma sessão; heading | declarado em IV-B e na V | mantido na V enxuta |
| R2 | imagem do robô e do aparato de medição | parcial: Fig. 2 tem a foto, não o aparato | legenda com a cadeia de medição (§3 item 3); se tiver foto do campo com as câmeras, melhor ainda |
| R2 | vídeos do procedimento e do gêmeo | **pendente**: nenhuma menção no texto | §3 item 6; gravação pelo runbook D5 |
| R2 | limitações "destacadas" | parcial: o `\subsection{Limitations}` foi comentado e o parágrafo ficou sem rótulo | a V enxuta abre o parágrafo com `\textit{Limitations.}` (custo zero) |

## 3. Correções obrigatórias (fora da Seção V), com o texto exato

1. **`03_method.tex`, III-F, texto estranho no PDF.** Ao tirar a frase do comentário, o fragmento
   `(horizons, h\_ref)` ficou vivo e aparece impresso: "are reported separately; (horizons, h ref)
   e_pos is the claim of this paper". Trocar

   ```latex
   with reference horizon $h_{\mathrm{ref}}=24$ ($\SI{0.4}{s}$) are reported separately; % source: config/metrics.json 
   (horizons, h\_ref) $\epos$ is the claim of this paper; $\eang$ is reported but bounded by the population of rotation-rich windows available (Sec.~\ref{sec:results:bins}).
   ```
   por
   ```latex
   with reference horizon $h_{\mathrm{ref}}=24$ ($\SI{0.4}{s}$) are reported separately. $\epos$ is the claim of this paper; $\eang$ is reported but bounded by the population of rotation-rich windows available (Sec.~\ref{sec:results:bins}).
   ```

2. **`03_method.tex`, III-G (Baselines), frase do rSim.** Trocar
   ```latex
   The second is \textbf{rSim}, the ODE-based physics engine of the rSoccer environment. It is driven at adjusted parameters for the teams robots.
   ```
   por
   ```latex
   The second is \textbf{rSim}, the ODE-based physics engine of the rSoccer environment, run with its stock robot parameters and no fitting to these logs, so the comparison is fitted-versus-untuned and is reported as context; the recorded body-frame commands drive it directly and, since it has no velocity setter, each window warms it up over the real pre-anchor commands before a rigid $\SEtwo$ re-anchor.
   % source: src/dtssl/models/rsim.py (robosim.SSL com parametros de fabrica; wheel_speed=False; warm-up Lw=15)
   ```
   Se a intenção da frase original era dizer que os parâmetros de fábrica do rSim descrevem uma
   geração anterior do robô do próprio time, isso pode entrar como "whose stock parameters
   describe an earlier generation of this team's robot", desde que seja verificável no rSoccer.

3. **`03_method.tex`, Fig. 2 (aparato, R2).** Trocar a legenda
   ```latex
   \caption{The four-wheeled omnidirectional SSL robot used in this work.}
   ```
   por
   ```latex
   \caption{The four-wheeled omnidirectional SSL robot used in this work; its pose comes from the league vision system (four overhead cameras, \SI{60}{Hz}), from which body velocity is derived offline.}
   ```
   e apagar o `\hfill` solto depois do `\includegraphics` (não faz nada). Se houver foto do campo
   com as câmeras, um segundo painel de 0,50 da coluna responde ao pedido por completo.

4. **`04_results.tex`, IV-D, "placeholder" nunca definido.** Trocar
   ```latex
   Scored against the same
   placeholder on the same competition population
   ```
   por
   ```latex
   Scored against the same no-dynamics placeholder ($K=1$, $\tau=\SI{0.1}{s}$, $\Td=0$) on the same competition population
   ```

5. **`07_conclusion.tex`.** `\section{Conclusion and Further Works}` → `\section{Conclusion and Future Work}`;
   e "identified mostly from closed-loop competition logs, attains validated translational
   fidelity:" → "identified mostly from closed-loop competition logs, which attains validated
   translational fidelity:" (a frase atual não tem verbo principal).

6. **Vídeos (R2).** Sem nota de rodapé (custa 3 linhas): dobrar na frase de disponibilidade da
   Conclusão, "Code, configurations, both datasets and supplementary videos (yaw collection,
   velocity extraction and the twin in operation) are released at \url{https://github.com/vhsabino/dt-ssl-sbr26}",
   e colocar os links dos vídeos no README do repositório. Os dois vídeos: (1) coleta de yaw e
   extração de velocidade (replay de `rotate_01_07` na GUI, pose de visão, velocidade derivada e
   modelo lado a lado; se existir filmagem da coleta, usar); (2) o gêmeo em operação, que é o
   vídeo 1 do runbook D5 (`tools/demo/video1_dropin.sh gui`) mais 30 s do replay de um evento de
   hold-out. Só prometa no texto o que estiver publicado.

7. **`04_results.tex`, Fig. 5.** `width=0.98\textwidth` → `width=0.90\textwidth` (ver §1).

## 4. A Seção V enxuta (`sections/05_discussion_enxuta.tex`)

Para usar: em `main.tex`, trocar `\input{sections/05_discussion}` por
`\input{sections/05_discussion_enxuta}` (ou copiar o conteúdo por cima do original).

De 418 para 343 palavras (−18 %), dois parágrafos em vez de três:

- Saiu o que IV-D já diz com números: os dois ajustes closed-loop ("a direct high-rotation fit
  and a regime-restricted linear fit"), o limiar que engaja em ~2 % das amostras ("removes the
  reading that the actuation threshold simply switches yaw off"), e a frase do braço open-loop com
  translação superposta, que já está no Future Work da Conclusão.
- Ficou tudo que os revisores podem cobrar: o achado central; o mecanismo (diluição, 56 %,
  realimentação, as três citações clássicas); e as sete limitações da versão avaliada (seis
  eventos de uma sessão; um robô, uma superfície, um split; campanhas que diferem em três fatores
  de uma vez; estimadores closed-loop não tentados; Ljung-Box e ausência de intervalos; razão de
  raios 3,3 %; 99,6 % translacional, heading e rSim fitted-versus-untuned com a condição inicial).
- Entrou, abrindo o parágrafo `\textit{Limitations.}`, a limitação que R1 e R2 pediram: canais
  desacoplados (o yaw induzido por translação é exatamente o que o modelo não representa e o que
  um MIMO teria de capturar), modelo linear sem slip, saturação ou limite de aceleração, validade
  restrita ao envelope dos logs. Fonte da ausência de saturação: `config/robot_limits.json`
  ("the published behavioral plant has NO saturation/acceleration limit").

Sem travessões; nenhum número novo.

## 5. Opcionais, por ordem de valor

1. **`figures/fig_architecture2.tex`, caixa das baselines.** Está "rSim (ODE)"; o comparador
   primário do artigo é a cinemática ideal. Trocar por `{Ideal kinematics\\ rSim (ODE)}`. Custo zero.
2. **`figures/robot_photo.png` tem 9,2 MB (3260 × 2357 px).** O PDF fica com ~1,4 MB mesmo com a
   foto reduzida; com a original vai a ~10 MB. Reduzir antes de compilar:
   `imwrite(imresize(imread('robot_photo.png'),0.4),'robot_photo.jpg','Quality',90)` e apontar o
   `\includegraphics` para o `.jpg` (1300 px de largura bastam para 4 cm impressos).
3. **Bloco de autores.** Os dois `\thanks` repetem o endereço completo e ocupam 6 linhas de rodapé
   na página 1. O formato padrão do IEEEtran para conferência é mais curto e libera ~3 linhas:
   ```latex
   \author{\IEEEauthorblockN{Victor Araújo and Edna Barros}
   \IEEEauthorblockA{Centro de Informática, Universidade Federal de Pernambuco, Recife, Brazil\\
   \{vhssa, ensb\}@cin.ufpe.br}
   \thanks{This work was supported by Centro de Informática, Universidade Federal de Pernambuco.}}
   ```
4. **`refs/references.bib`, `machado2025planning`.** Sai como "Preprint" sem ano nem venue (é a
   referência [3]). O PDF do Projeto é a versão LNCS sem cabeçalho; vocês são coautores, então
   preencher venue e ano da versão publicada (não de memória) ou deixar como está, declarado.
5. **`main.pdf` no repositório é de 31/07** (versão antiga, double-blind). Recompilar e
   substituir, ou apagar, para não confundir a cópia que vai ao JEMS.
6. Comentários de decisão de título no `main.tex` (40 linhas) podem sair do fonte compartilhado.

## 6. Checklist final antes de subir no JEMS

- [ ] §3 itens 1 a 7 aplicados; `05_discussion_enxuta` no build; compilação limpa em 6 páginas.
- [ ] `grep -rn "\\\\paragraph\|Anonymous\|withheld\|TODO\|horizons, h" sections/ main.tex` vazio.
- [ ] Título do PDF igual ao do JEMS; autores, e-mails e agradecimento conferidos.
- [ ] Vídeos publicados e linkados no README antes de prometê-los no texto.
- [ ] Foto reduzida; PDF com fontes embutidas; A4 (o `main.tex` já usa `a4paper`); IEEE PDF
      eXpress e formulário de copyright se o JEMS pedir.
