# `docs/` — índice (02/09/2026)

Uma linha por documento, por categoria. Datas = quando o documento foi produzido; **HISTÓRICO** =
mantido só por rastreabilidade (o estado atual está em `CLAUDE.md` e em `docs/SPEC_DTSSL.md`).
Proveniência de cada número do projeto: `results/CHANGELOG.md`.

## Contrato e decisões (SPEC / ADR)

| Documento | Uma linha |
|---|---|
| `SPEC_DTSSL.md` | **Contrato de arquitetura** da refatoração de 02/09/2026: decisões D1–D7, layout do repo, convenções físicas, interfaces obrigatórias (`models`, `sim`, `eval`, `bridge`, `gui`, `physics`, CLI), testes e ferramentas externas. Vence qualquer outro documento. |
| `ADR-*.md` | registros de decisão de arquitetura da refatoração (escritos pelo orquestrador; ADR-001 cita apenas os 20 PDFs da SLR + 3 novos). |
| `../CLAUDE.md` | estado real do projeto (θ oficial com ω promovido), estrutura, convenções, guardrails, *definition of done*. |

## Notas de refatoração (`refactor_notes/`, 02/09/2026)

| Documento | Uma linha |
|---|---|
| `refactor_notes/core.md` | núcleo do harness: `units/config/geometry/kinematics`, `eval/` dividido (metrics/stats/verdict/report), `rollout` com cache `.npz`, CLI; caveats (CIs do bootstrap mudam nos últimos dígitos; grade de janelas ancorada no θ oficial). |
| `refactor_notes/analysis.md` | os 21 scripts do artigo migrados para `dtssl.analysis` (`run(root, out)` + `main()`), cabeçalho de proveniência, `dtssl analysis`/`dtssl fig`, `tools/make_release.py`. |
| `refactor_notes/etl.md` | ETL dos logs `.log.gz` → parquet (`recordio`, `_proto`, `extract`, `rotate`, `dtssl etl`), substituindo `python/` e os notebooks. |
| `refactor_notes/bridge.md` | `TwinWorld` (bola 2 fases, colisões, dribbler, watchdog), servidor ssl-simulation-protocol (visão/controle/simcontrol), `fake_strategy`, `recorder`, protos versionados; **como rodar contra o ssl-unification e rede no WSL2**; replay via protocolo (`ProtocolPlant`: grSim/ER-Force no harness, C2b). |
| `refactor_notes/physics.md` | backend MuJoCo: builder MJCF (rota a: FOPDT dirige o ego; rota b: rodas + roletes), `MuJoCoWorld`, `dtssl mjcf`, testes. |
| `refactor_notes/matlab_docs.md` | MATLAB (`matlab/dtssl` vivo × `matlab/legacy` arquivado, `bootstrap_paths` sem `cd`, `export_plant_golden` com θ), `legacy/`, manifesto de moves/deletes do PC, `.gitignore`/`.gitattributes`, `tools/ssl_unification/`, docs — com a entrada proposta para o CHANGELOG. |

## Definição da pesquisa e planos (HISTÓRICO, exceto onde indicado)

| Documento | Uma linha |
|---|---|
| `01_definicao_pesquisa.md` | definição formal (10/06/2026): problema, lacuna, tese em 1 frase, QPs, objetivos, hipóteses, escopo — Gate G1 do plano de junho. |
| `../ROADMAP.md` | plano de junho/2026 (trilha do artigo de qualificação + doutorado); banner HISTÓRICO. |
| `../DESIGN.md` | exploração/contrato de dados (15/06/2026) que originou o harness `phase0_replay` (hoje `dtssl`); a §2 (contrato dos logs) continua válida; banner HISTÓRICO. |
| `PLANO_PAPER_SBR2026.md` | planejamento de escrita do paper SBR/LARS 2026 (23/06, atualizado 24/07 com V10 = ω promovido). |
| `PREREGISTRO_OMEGA_20260724.md` | **pré-registro** dos critérios de promoção de ω (gravado antes da estimação; ainda válido como defesa metodológica). |
| `PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md` | **pré-registro** do experimento C1 (identificabilidade in-silico com θ conhecido: regime × ruído × zona morta, hipóteses H1–H4, estimador e regra de decisão) — executado por `dtssl analysis run identifiability_insilico` (VIGENTE). |
| `PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_20260907.md` / `…_C1B_V2_…` | **pré-registros** do C1b (gerador físico; v1 falhou pela célula de referência e foi mantida; v2 re-registrada). |
| `PREREGISTRO_C4_MALHA_FECHADA_20260908.md` | **pré-registro** do C4 (sessão em malha fechada × competição, critérios P1–P5). |
| `PREREGISTRO_C2B_SIMULADORES_LIGA_20260910.md` | **pré-registro** do C2b (grSim/ER-Force no hold-out via ssl-simulation-protocol: H1–H3 e critério V de validade do instrumento) — executado por `dtssl analysis run protocol_holdout` (10/09). |
| `PREREGISTRO_C2B2_PREROLAGEM_20260916.md` | **pré-registro** do C2b2 (pré-rolagem no replay via protocolo: o simulador chega a t0 pela própria dinâmica sob o prefixo real de comandos, trajetória re-ancorada em t0; H1' a H4' e V'); código em `dtssl.sim.preroll` e `preroll=` do `protocol_holdout`; executado em duas sessões, 18/09 (`protocol_holdout_20260918_1326`, registro tardio no CHANGELOG em 23/09) e 20/09 (`protocol_holdout_20260920_1143`). |
| `PREREGISTRO_MIMO_CHECK_20260923.md` | **pré-registro** da checagem MIMO (acoplamento entre canais nos logs de competição: M1 primária, M2 mecanismo, M3 harness, controles C- e C+; estimador de mínimos quadrados separáveis em erro de saída) para o artigo de periódico; módulo `dtssl.analysis.coupled_mimo_check`; **executado em 14/10/2026** (`results/coupled_mimo_check_20261014_1211` e os dois controles; CHANGELOG 2026-10-14 12:11: M1 não importa, M2 falsificada, M3 não melhora, C- OK, C+ com premissa não reproduzida). |
| `journal/MAPEAMENTO_ARTIGO.md` | mapa do artigo de periódico (extensão do SBR/LARS 2026 para a Digital Engineering, VSI:DTE_DigiTwin2026): seção, conteúdo, artefato, número, tabela ou figura gerada e estado; discrepâncias encontradas e decisões pendentes. Esqueleto `elsarticle` em `../latex_journal/`. |
| `INVENTARIO_RL_2026-07-24.md` | inventário do repo `planning-rl-greybox` (WSL2): experimento de gap de dinâmica com SAC+FSCAPS — fora de escopo nesta rodada. |
| `RSIM_EXPLORATION.md` | viabilidade do `RSimReplay` (rSoccer/rSim) — bloqueios encontrados (16/06). |
| `TASKS_CLAUDE_CODE.md` | pendências que exigiam execução para o paper (07/08); parte executada em 09–10/08 (ver CHANGELOG). |
| `BACKLOG_EXTENSAO_JINT.md` / `TRIAGEM_BACKLOG_JINT.md` | conteúdo cortado do paper de 6 páginas e sua triagem (a/b/c) para a extensão JINT. |
| `CORTES_SUGERIDOS.md` / `CORTES_PARA_6_PAGINAS.md` | candidatos e plano de cortes para caber em 6 páginas (07–10/08). |
| `PLANO_ACCEPT_SBR2026.md` / `PLANO_V2_EXECUTADO.md` / `PLANO_V3_EXECUTADO.md` | planos derivados das revisões independentes e o que foi executado em 10/08 (V2 encerra R1 — a matriz `K_inv` está correta). |
| `GUIA_ANONIMIZACAO_REPO.md` | checklist verificado de anonimização do pacote público (double-blind); hoje automatizado por `tools/make_release.py`. |
| `D3_RELEASE_CHECKLIST_20261014.md` | dry-run do pacote de reprodução (D3 / WP5) em 14/10/2026: o que o pacote contém (8,5 MB, artefatos de junho a outubro, pré-registros, CHANGELOG), o que mudou para a varredura fechar (cabeçalhos das malhas CAD, manifesto, scrub), limites e as decisões que faltam (anonimizado ou identificado, dados, DOI, autoria). |

## Revisões e cartas (HISTÓRICO)

| Documento | Uma linha |
|---|---|
| `REVISAO_ESPECIALISTA_20260731.md` | revisão especialista simulada do PDF de 31/07 (borderline / weak accept). |
| `CARTA_RESPOSTA_REVISORES.md` | carta-resposta à revisão de 31/07 (07/08). |
| `REVISAO_MAIOR_20260807_RODADA2.md` | revisão maior, rodada 2 (07/08), alvo *strong accept*. |
| `REVISAO_MANUAL_ARTIGO.md` | documento anotável do artigo com IDs estáveis por parágrafo (09/08). |
| `REVISAO_INDEPENDENTE_SBR2026.md` / `…_V2_…` / `…_V3_…` | três revisões independentes (10/08) só sobre o PDF compilado — weak reject → weak accept → weak reject com bloqueadores corrigíveis. |
| `REVISAO_SECOES_20260724.md` | revisão editorial da inversão narrativa de ω (24/07). |
| `REGISTRO_DESVIOS.md` | desvios brief × executado na sessão de 07/08. |

## Relatórios e reuniões

| Documento | Uma linha |
|---|---|
| `RELATORIO_TECNICO_DESENVOLVIMENTO.md` | **relatório técnico vivo** (até 24/07): arquitetura do `pid_v3`, métrica canônica, dados, defeitos corrigidos, campanha de junho, identificação de vx/vy e ω, bayesopt, decisões e pendências. |
| `LOG_FINALIZACAO_ARTIGO_20260731.md` | log da sessão multiagente que levou o artigo ao PDF submissível (31/07). |
| `REUNIAO_MODELO_E_LITERATURA.md` | verificação arquivo-a-arquivo do modelo/MATLAB/literatura para reunião (26/06). |
| `REUNIAO_FIGURAS.md` | índice e roteiro das figuras da reunião de 26/06. |
| `RESUMO_ORIENTACAO_20260909.pdf` | resumo de 2 páginas para a orientadora (09/09): infraestrutura, resultados C2a/C1/C1b/B3/C4/C5-C6 com proveniência, leitura, próximos passos e as duas decisões pedidas. |
| `DEMO_ORIENTACAO_20260911.md` | roteiro da demonstração de 30 min para a orientadora (11/09): blocos com comando, fala e plano B, próximos passos, perguntas a fazer, números de bolso. |
| `RUNBOOK_VIDEOS_D5_20260916.md` | passo a passo único dos dois vídeos que faltaram na demo (drop-in do ssl-unification; ER-Force rodando e avaliado pelo gêmeo), com os scripts `tools/demo/video1_dropin.sh` e `tools/demo/video2_erforce.sh` (check, run/start, probe, replay, strategy, stop), fala, plano B e falhas comuns. |
| `RUNBOOK_B1_CENARIO62.md` | passo a passo do B1 (cenário 6.2: gêmeo + GUI + DualSense no Windows, estratégia no WSL2 por unicast ou `mirrored`), com o script `tools/demo/b1_scenario62.ps1` (prepare, firewall, gui, wsl), o que observar e as falhas comuns (14/10/2026). |
| `../legacy/apresentacao/orientacao_20260612.m` | roteiro executável da reunião de orientação de 12/06 (só artefatos salvos). |

## Fora de `docs/`

`results/CHANGELOG.md` (proveniência), `results/*.md` (relatórios gerados: `identificacao_omega_20260724.md`,
`qc_rotate_*`, `reidentificacao_20260724.md`, gates e ablações de 08/2026), `slr/protocolo_slr.md`
(+ `CANDIDATOS_CITACAO.md`, `EXTRACAO_CITAVEIS.md`), `paper/outline_artigo.md` (outline IMRaD de junho),
`latex/` (artigo do SBR, build de 10/08; bibliografia única `latex/refs/references.bib`), `paper/sbr2026_accepted/`
(fonte aceito, cópia do OneDrive) e `paper/sbr2026_camera_ready/` (patch do camera-ready, `CAMERA_READY_NOTES.md`),
`latex_journal/` (artigo de periódico, `elsarticle`; tabelas e figuras geradas por `dtssl analysis run journal_tables` e
`dtssl fig fig_journal_*`), `matlab/legacy/README.md`,
`legacy/README.md`, `tools/ssl_unification/README.md`, `tools/external_sims/README.md` (grSim/ER-Force no WSL2 e o experimento C2b), `tools/apply_refactor_manifest.json`.
