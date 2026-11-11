# Artigo de periódico (extensão do SBR/LARS 2026): planejamento e prompt para o novo chat

*Escrito em 23/09/2026. Parte 1 é o planejamento; Parte 2 é o texto para abrir o chat novo, na
minha voz, para colar como primeira mensagem. Complementa `PLANO_CAMERA_READY_SBR2026.md` (a
correção do artigo aceito) e os docs do Projeto `claude/camera-ready-sbr2026.md`,
`claude/backlog-decisao-2026-09.md` e `claude/estado-digitaltwin-refatoracao.md`.*

---

## Parte 1. Planejamento

### 1. Alvo

- Periódico e chamada: *Digital Engineering* (Elsevier, ISSN 2950-550X, open access), Special
  Issue VSI:DTE_DigiTwin2026, aberta a qualquer autor, submissões até 28/02/2027, decisões até
  31/05/2027, APC zero para submissões até 31/12/2026.
- Data-alvo de submissão: **15/12/2026** (folga de duas semanas para a APC zero); limite duro
  28/02/2027.
- Pré-condições externas: camera-ready do SBR entregue (outubro); apresentação no SBR (novembro);
  e-mail de confirmação do executive guest editor (Zhiqiang Wang) sobre extensão de conferência e
  escopo; Qualis/percentil do periódico conferido para o PPGCC; decisão da orientadora sobre a
  rota (D1) e sobre a baseline sintonizada (C3 ou rSim).

### 2. A tese do artigo em um parágrafo

Um gêmeo digital comportamental de um robô omnidirecional pode ser identificado a partir dos
dados operacionais que a equipe já grava, mas só para os graus de liberdade que esses dados
excitam; a identificabilidade é uma propriedade do regime de excitação e da realimentação, não do
grau de liberdade, e pode ser prevista antes de ajustar qualquer parâmetro. O viés do canal de
guinada em malha fechada é acoplamento translação para guinada correlacionado com o comando,
demonstrado in silico e quantificado por um modelo acoplado; uma coleta dedicada curta remove
esse acoplamento. Validado sob um único protocolo pré-registrado, o gêmeo supera a cinemática
ideal, três motores de física da liga sem sintonia (rSim, grSim, ER-Force) e um gêmeo físico em
MuJoCo, com condição inicial justa para todos, e produz jogo em malha fechada com estatística de
comandos indistinguível da competição. O ganho vem do atraso e da constante de tempo, condicional
à velocidade inicial medida, e não se transfere ao heading na mesma proporção.

Duas versões de título para decidir com a orientadora:

1. *Identifiability-aware behavioral digital twins from operational data: a validated grey-box
   plant for an omnidirectional robot with physics-based and league-simulator baselines*
2. *What operational logs can identify: excitation regime, cross-coupling and fair baselines in a
   behavioral digital twin of an omnidirectional robot*

### 3. O que se une (inventário)

| Fonte | Conteúdo | Estado |
|---|---|---|
| Artigo SBR (6 pág.) | planta FOPDT por DOF; regime de excitação; regra de triagem pré-ajuste; protocolo de fidelidade; 0,039 vs 0,101 vs 0,129 m; Shapley τ 55 % / Td 43 % / K 2 %; ablação da condição inicial; controle negativo bayesiano | publicado (reescrever, não copiar) |
| Pareceres do SBR | acoplamento/MIMO; slip, saturação, não linearidades; baseline sintonizada; validação rotacional; figura do aparato; vídeos | camera-ready cobre a parte de apresentação; o resto é o artigo novo |
| C1 (`identifiability_insilico_20260907_1552`) | gerador linear recupera θ* em todas as 60 células com excitação; H1/H4 falsificadas; fit % mede SNR, não recuperação | feito |
| C1b v2 (`identifiability_insilico_mujoco-rollers-delay_v2_20260907_2044` e `_rollers_v2_..._2048`) | gerador físico reproduz a inflação de K_ω em malha fechada (+16,5 % / +27,4 %), controle sem translação 0,988 / 0,930, rotate 0,996: mecanismo = acoplamento translação para guinada | feito |
| C2a (`backends_holdout_20260907_1515`) | MuJoCo rota a 0,0388 (embedding = gêmeo); rota b 0,0729; rota b + atraso 0,0477; ideal 0,1005; 10/10 e 9/10 | feito |
| C2b (`protocol_holdout_20260910_0211`) | grSim e ER-Force via protocolo da liga: 0,2389 / 0,0881 por janela; +delay 0,2335 / 0,0555; instrumento válido (critério V) | feito |
| C2b2 (`protocol_holdout_20260920_1143`) | pré-rolagem: grsim+preroll 0,0809 / 0,0975 por evento; erforce+preroll 0,0940 / 0,1114; fopdt+preroll 0,0406; gêmeo vence as 4 em 10/10 | feito |
| C4 (`closed_loop_stats_20260907_2137`) e B3 (`session_report_sessao_01_20260907_2059`) | sessão da estratégia contra o gêmeo: 5/5 contra `shoot_to_goal`; round trip ao mm | feito |
| Ablação de atraso do rSim (`eval_rsim_delay_ablation_20260809_2154`), decomposição por Shapley (`ablation_orderfree_20260810_1021`), IC causal (`causal_ic_check_20260810_1102`), LOO (`loo_translational_20260810_1743`), fit closed-loop (`r3_closedloop_omega_fit_20260810_1036`) | robustez já feita para o SBR, cortada por espaço | feito, entra inteiro |
| Backlog JINT (`docs/BACKLOG_EXTENSAO_JINT.md`) | limitações completas, figuras de fit vx/vy e de bins, Modo B, controle negativo em detalhe, related work eixos (a)/(c) | feito, entra |
| SLR (RQ1, RQ2 fechada com 23 incluídos) | related work de gêmeos de robôs móveis e fidelidade | em curso no outro chat; consumir só o que estiver decidido |
| Novo: acoplamento (MIMO) | `coupled_mimo_check` (código em `PLANO_CAMERA_READY_SBR2026.md` §B3) e versão completa | a fazer (WP2) |
| Novo: baseline sintonizada | rota b calibrada (C3) ou rSim sintonizado | a fazer se a orientadora aprovar (WP3) |
| Novo, opcional: comparação em malha fechada nos três simuladores | a estratégia jogando contra grSim, ER-Force e o gêmeo, mesma estatística do C4 | só se sobrar tempo (WP3b) |

### 4. Estrutura do artigo (elsarticle, referências numéricas [1], [2]) e de onde vem cada parte

| Seção | Conteúdo | Fonte | Novo? |
|---|---|---|---|
| 1 Introduction | reality gap; a camada de planta de um gêmeo; dados operacionais; seis contribuições | SBR I reescrita | parcial |
| 2 Related work | gêmeos de robôs móveis; identificação grey-box; identificação em malha fechada; calibração sim-to-real; simuladores da liga | SBR II + backlog F + SLR | ampliado |
| 3 Robot, data and instrumentation | robô, campo, visão 60 Hz, logs de competição, coleta dedicada, sessões gravadas; figura do aparato e cadeia de medição | camera-ready A6 + B3 | parcial |
| 4 Models | FOPDT por DOF; modelo acoplado (MIMO); discretização; estimadores; regra de triagem pré-ajuste | SBR III + WP2 | novo (acoplado) |
| 5 Validation protocol | harness free-run, bins, gate pré-registrado, unidade por evento; replay via protocolo e pré-rolagem; validade do instrumento (critério V); pré-registros e desvios | SBR III + C2b/C2b2 | ampliado |
| 6 Results I: identifiability by regime | closed-loop vs dedicado; diluição; C1 (gerador linear); C1b (mecanismo físico) | SBR IV-D + C1 + C1b | novo (C1/C1b) |
| 7 Results II: cross-coupling | modelo acoplado vs desacoplado, mesmo estimador e dados; ganhos cruzados; e_pos no harness | WP2 | novo |
| 8 Results III: fidelity | ideal, rSim, grSim, ER-Force (cru e pré-rolado), MuJoCo a/b, baseline sintonizada; Shapley; condição inicial; heading; LOO; controle negativo | SBR IV + C2a + C2b + C2b2 + WP3 | ampliado |
| 9 Results IV: closed-loop plausibility | sessão contra o gêmeo vs competição (C4); o que o gêmeo produz como ambiente | C4 + B3 | novo |
| 10 Discussion | o que o modelo compra; identificabilidade como propriedade do dado; quando um gêmeo físico é necessário; regra de triagem | SBR V | ampliado |
| 11 Limitations and threats | as sete do SBR + desacoplamento/slip/saturação + escopo do instrumento + envelope | `06_limitations.tex` completo + camera-ready A8 | ampliado |
| 12 Conclusion; Data and code availability; CRediT; Declarations | | | |

Alvo de tamanho: 9 a 11 mil palavras, 8 a 10 figuras, 6 a 8 tabelas. O harness e o servidor de
protocolo aparecem como método (Seção 5), não como contribuição de plataforma; a plataforma
(GUI, drop-in, telemetria, MuJoCo) fica para o artigo de ferramenta separado.

### 5. Pacotes de trabalho

| WP | O quê | Entradas | Saídas | Quem executa | Esforço | Gate |
|---|---|---|---|---|---|---|
| WP0 Camera-ready | Faixa A do `PLANO_CAMERA_READY_SBR2026.md` (mais B se couber) | fonte no OneDrive; PDF do JEMS | PDF final no JEMS; fonte copiado para `latex/` do repo; CHANGELOG | Claude prepara o patch dos `.tex`; Victor revisa, fotos, vídeos, submete | 1 bloco de revisão + 3 h de Victor | prazo do JEMS |
| WP1 Consolidação | transformar C1, C1b, C2a, C2b, C2b2, C4, ablações e LOO em seções de artigo: tabelas e figuras em inglês no tamanho do periódico, estatística por evento, texto-rascunho | artefatos em `results/`, `dtssl analysis`/`dtssl fig` | `docs/journal/` com rascunhos por seção, `latex_journal/` com figuras; nenhum número novo | Claude sozinho na nuvem (sem dataset: só a partir dos artefatos `.md/.csv/.json`) | 3 a 4 dias de Claude | nenhum |
| WP2 Acoplamento (MIMO) | pré-registro; `coupled_mimo_check` (B3); versão completa: atrasos por par (i, j) em grade inteira, IC bootstrap por evento, `CoupledFirstOrderPlant` no harness, e_pos por evento | dataset no PC | `docs/PREREGISTRO_MIMO_*.md`, módulo + testes, artefato em `results/`, CHANGELOG, texto da Seção 7 | Claude escreve e testa sem dados; Victor roda no PC (minutos) | 2 dias de Claude + 30 min de Victor | pré-registro aprovado por Victor antes de rodar |
| WP3 Baseline sintonizada | opção A: rota b calibrada (atrito, roletes, `impratio`) por otimização bayesiana nos eventos de treino, pontuada no hold-out (C3); opção B: rSim sintonizado (aceleração, ganhos) com o mesmo procedimento; pré-registro com as duas leituras possíveis (inclusive a de a física sintonizada empatar ou vencer o gêmeo) | C2a, `robosim` no PC | módulo, artefato, CHANGELOG, texto da Seção 8 | Claude prepara; Victor roda (horas de máquina) | 1 a 2 semanas | decisão da orientadora (C3 congelado); se não, o artigo declara os quatro motores sem sintonia e a rota b + atraso como o mais perto de sintonizado |
| WP3b (opcional) Malha fechada nos simuladores | estratégia jogando contra grSim e ER-Force com a mesma estatística do C4 | scripts do D5 e do C2b | artefato, texto curto na Seção 9 | Victor roda no WSL; Claude analisa | 1 dia + 1 h de máquina | só se WP2 e WP3 fecharem antes de novembro |
| WP4 Texto | esqueleto elsarticle; introdução e contribuições; related work com a SLR; seções 3 a 11; figuras finais; limitações; carta de submissão; highlights | WP1 a WP3, camera-ready, SLR | manuscrito completo em Overleaf (`elsarticle`, `elsarticle-num`) | Claude rascunha na minha voz; Victor edita | 2 semanas de Claude, 15 a 20 h de Victor | revisão da orientadora |
| WP5 Reprodutibilidade | `dtssl release` anonimizado ou não; Zenodo DOI; data availability (logs de competição, `rotate`, sessão B3 via DVC); um `dtssl analysis run` por número | D3 (congelado) | pacote + DOI + declaração | Claude prepara, Victor publica | 1 dia | decisão de licença e autoria com a orientadora |
| WP6 Submissão | Editorial Manager, VSI:DTE_DigiTwin2026, carta com a declaração da versão de conferência, CRediT, declarações, sugestão de revisores | WP4, WP5 | submissão | Victor | 2 h | e-mail do Wang respondido |

Divisão entre chats: este chat (artigo) escreve os módulos de análise novos (`coupled_mimo_check`,
o de sintonia) e os scripts de figura, como arquivos novos em `src/dtssl/analysis/` e `tests/`,
entregues em `_to_delete\_apply\` como patches com md5, sem tocar em `sim/`, `bridge/`, `gui/`,
`physics/`, que são do chat do gêmeo. O chat da SLR não é tocado; consome-se apenas a lista de
incluídos quando o Victor a trouxer.

### 6. Cronograma

| Semana | Victor | Claude (chat do artigo) |
|---|---|---|
| 23/09 a 02/10 (SLR é a prioridade) | 1 bloco de 30 min: JEMS (prazo, limite, PDF), e-mail ao Wang, respostas do inventário | patch do camera-ready (Faixa A) sobre o fonte do OneDrive; pré-registro e módulo do MIMO com testes; esqueleto do artigo e tabela de mapeamento; figuras em inglês de C1b, C2b2 e C4 a partir dos artefatos |
| 05/10 a 09/10 | aplicar e conferir o camera-ready; fotos; vídeos (runbook D5); submeter; rodar `coupled_mimo_check` no PC; reunião com a orientadora (D1, C3, título, autoria) | fechar WP1; texto da Seção 7 nas duas versões (importa / não importa) |
| 12/10 a 30/10 | rodar WP3 no PC (se aprovado); commit dos artefatos e CHANGELOG | preparar WP3 (pré-registro, módulo, testes); rascunhar seções 3 a 6 e 8 a 9 |
| novembro | apresentação no SBR; editar o texto; SLR RQ1 em paralelo | seções 1, 2, 10, 11; figuras finais; carta; WP5 |
| 01/12 a 10/12 | revisão da orientadora | incorporar |
| 11/12 a 15/12 | submissão | checklist do Editorial Manager |
| até 28/02/2027 | folga se dezembro não fechar | |

### 7. Decisões que só a orientadora ou eu fechamos

1. Rota: SI da *Digital Engineering* para a extensão e artigo de ferramenta separado, ou JINT se
   houver convite (não pode ser os dois com o mesmo texto).
2. Título (uma das duas versões acima ou outra) e autoria (RobôCIn, quem fez a coleta e o CAD).
3. Baseline sintonizada: rota b calibrada (C3), rSim sintonizado, ou nenhuma (declarar).
4. Quanto da Faixa B entra no camera-ready (D1).
5. Licença e forma do pacote de reprodução (anonimizado ou identificado; DOI).
6. Coleta nova no laboratório para validação rica em rotação: se não houver, fica como limitação.

### 8. Riscos e como tratá-los

- O resultado do MIMO pode ser nulo: o pré-registro já traz as duas frases; um resultado nulo é
  argumento a favor da estrutura desacoplada dentro do envelope dos logs.
- A física sintonizada pode empatar ou vencer o gêmeo: pré-registrar as duas leituras; se
  empatar, a mensagem passa a ser "o comportamental entrega o mesmo por uma fração do custo e sem
  parâmetros de contato"; se vencer, o artigo relata e a discussão muda de tom.
- Originalidade: nenhum parágrafo do SBR copiado; figuras regeneradas pelos scripts; o SBR citado
  como versão preliminar na introdução e na carta.
- Tempo: a SLR e a qualificação competem; o cronograma acima cabe em 6 a 8 h semanais de Victor em
  outubro e 10 em novembro; se não couber, o limite duro é 28/02 e o custo é a APC.
- Qualis: se o periódico não atender ao mínimo do programa, a mesma extensão vai para JINT ou
  RAS, com o mesmo conteúdo; a decisão tem de vir antes de outubro.

---

## Parte 2. Prompt para abrir o novo chat (colar como primeira mensagem)

Novo chat do projeto Doutorado, aberto em 23/09/2026, dedicado ao artigo de periódico que estende o
artigo aceito no SBR/LARS 2026 (submissão #34344, JEMS) e ao camera-ready desse artigo. A SLR continua
em outro chat e é a prioridade única do meu trabalho intelectual até o marco M3 (02/10); o gêmeo
(pacote `dtssl`) tem o seu próprio chat, que cuida da engenharia. Este chat existe para transformar o
que já foi medido em um manuscrito para a Special Issue VSI:DTE_DigiTwin2026 da *Digital Engineering*
(Elsevier), com submissão-alvo em 15/12/2026, e para fechar o camera-ready do SBR no caminho.

Antes de responder qualquer coisa, leia no Projeto, nesta ordem: `claude/camera-ready-sbr2026.md`
(estado do aceite, diagnóstico da versão submetida, fatos da special issue),
`claude/plano-artigo-journal-2026-09-23.md` (este planejamento: tese, estrutura, pacotes de trabalho,
cronograma), `claude/backlog-decisao-2026-09.md` (o que está feito e os artefatos, §6 e §8),
`claude/estado-digitaltwin-refatoracao.md` (checkpoints de 07/09 a 20/09, com a leitura de cada
resultado) e `claude/handoff-2026-09-12.md` (§1 feedback da orientadora e §6 regras). Na pasta do artigo
no OneDrive (`C:\Users\victo\OneDrive\Área de Trabalho\Papers\Artigo_SBR_2026___Digital_Twin`): os
`.tex` da versão aceita e `PLANO_CAMERA_READY_SBR2026.md`, que tem o mapa dos pareceres, os trechos
LaTeX prontos, o código da checagem MIMO (§B3) e a avaliação da special issue (§5). No repo
`C:\Users\victo\Documents\digitaltwin`: `CLAUDE.md`, `docs/README.md`, `results/CHANGELOG.md` (51
entradas; as de 07/09, 10/09 e 20/09 são a matéria-prima do artigo), `docs/BACKLOG_EXTENSAO_JINT.md`,
`docs/PREREGISTRO_*.md`, `latex/` (versão longa do artigo, de 10/08) e `sections/06_limitations.tex`.
Em caso de conflito, o handoff vence nas regras e o CHANGELOG vence nos números. Não leia nem escreva
nos docs da SLR (`claude/estado-slr-2026.md`); não edite `claude/backlog-decisao-2026-09.md` nem
`claude/estado-digitaltwin-refatoracao.md`, que são do chat do gêmeo.

Contexto em cinco linhas: o artigo do SBR foi aceito em 22/09 com um Neutral e um Weak Accept; os
pareceres pedem acoplamento (MIMO), discussão de slip e saturação, baseline sintonizada, figura do
aparato, vídeos, abstract em um parágrafo e proofreading. Tudo que o artigo de periódico precisa de
evidência nova sobre mecanismo e baselines já foi medido em setembro: C1 e C1b (identificabilidade in
silico, mecanismo do viés de guinada = acoplamento translação para guinada), C2a (MuJoCo rotas a e
b), C2b e C2b2 (grSim e ER-Force via protocolo da liga, com pré-rolagem), C4 e B3 (sessão em malha
fechada contra o gêmeo). O que falta medir é o modelo acoplado (código pronto para ser executado no
PC) e, se a orientadora aprovar, uma baseline física sintonizada. O repo estava em `f8316d4` no PC
em 20/09, com o lote 2 (aba Robot) extraído e não commitado e o B2 (merge em `main`, tag `v1.0.0`)
pendente; confira o estado antes de assumir qualquer coisa, sem rodar git na VM.

O que este chat entrega, na ordem do planejamento: WP0, o camera-ready (aplicar a Faixa A do plano
aos `.tex` do OneDrive e me devolver o patch para eu revisar; nada vai ao Overleaf sem eu ler); WP1, a
consolidação dos resultados de setembro em seções de artigo, com tabelas e figuras em inglês geradas
pelos scripts do `dtssl` a partir dos artefatos, sem número novo; WP2, o pré-registro e o módulo do
modelo acoplado (`coupled_mimo_check` e a versão completa com planta no harness), que eu rodo no PC;
WP3, o desenho e o pré-registro da baseline sintonizada, implementação só depois da decisão da
orientadora; WP4, o manuscrito em `elsarticle` com referências numéricas, seção a seção, na minha
voz; WP5, o pacote de reprodução com DOI; WP6, a submissão. A ordem dos lotes é essa; o cronograma
está no planejamento.

Regras deste chat:
1. Até 02/10 o meu tempo aqui é um bloco de 30 minutos por semana; em outubro, dois blocos; em
   novembro, o que a escrita pedir. Planeje lotes que você executa sozinho na nuvem e me entrega para
   validar de uma vez; o que depender de mim, pare e peça, e agrupe os pedidos.
2. Nenhum número entra no texto sem estar em `results/CHANGELOG.md` ou num artefato de `results/`
   citado pelo nome; nenhuma referência sem estar em `latex/refs/references.bib` ou vir da lista de
   incluídos da SLR que eu trouxer. Experimento novo só com pré-registro em `docs/PREREGISTRO_*.md`
   antes de rodar, com as falsificações reportadas; o θ oficial e os arquivos de `config/` não mudam.
3. Código novo só como arquivos novos em `src/dtssl/analysis/`, `tests/` e `docs/`, entregues em
   `_to_delete\_apply\` como patch com md5 e script `.ps1` de aplicação e teste, como o chat do gêmeo
   faz; `sim/`, `bridge/`, `gui/` e `physics/` são do outro chat. Git só no Windows, sem push; nada
   apagado no PC; `ruff` limpo (linha 110) e `pytest -m "not requires_data"` nos arquivos tocados. A
   nuvem não tem o dataset: o que precisar de dados eu rodo no PC e te mando os artefatos.
4. Texto do artigo em inglês, na minha voz, sem travessão; documentos meus em português, sem
   travessão; referências numéricas do `elsarticle-num`. Nenhum parágrafo do artigo do SBR copiado: o
   texto é reescrito e o SBR é citado como versão preliminar na introdução e na carta de submissão.
5. O harness, o servidor de protocolo e a pré-rolagem aparecem no artigo como método, não como
   contribuição de plataforma; a plataforma fica para um artigo de ferramenta separado. Não
   proponha experimento fora do escopo do CLAUDE.md (RL, Isaac Sim, robôs reais) sem eu pedir.
6. Este chat é dono de `claude/camera-ready-sbr2026.md` e de um doc novo,
   `claude/estado-artigo-journal.md`, que você cria e mantém a cada lote (o que foi entregue, o que
   espera por mim, decisões registradas). Os docs da SLR e do gêmeo são dos outros chats.

Comece assim: confirme o inventário do planejamento (§3) contra o CHANGELOG e o backlog, me diga o
que discorda ou o que faltou, e me faça de uma vez só as perguntas de que precisa: prazo e limite de
páginas do camera-ready no JEMS; se a "Tabela III duplicada" aparece no PDF submetido; qual título
mantenho; se autorizo a preparação do MIMO agora (pré-registro e módulo, sem rodar); se há resposta
da orientadora sobre D1 e C3; se o e-mail ao Wang foi enviado. Depois proponha o lote 1, executável
sem mim (patch do camera-ready, pré-registro e módulo do MIMO com testes, esqueleto do artigo e
tabela de mapeamento, figuras de C1b, C2b2 e C4 em inglês), com a estimativa do tempo que eu gasto
para validar.
