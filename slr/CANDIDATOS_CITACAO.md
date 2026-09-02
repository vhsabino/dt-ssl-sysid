# Candidatos a Citação — SBR/LARS 2026 (double-blind)

> **Instrução ao usuário:** para cada candidato escolhido, deposite o PDF em
> `slr/pdfs/` nomeado pelo **Paper ID do Notion** (ex.: `slr/pdfs/SLR-2024-Marvin-250.pdf`).
> A fase seguinte (criação de entradas `.bib` e inserção nos `.tex`) só usará
> referências cujo PDF estiver depositado e verificado.

**Fonte:** Notion DB `74fe3d83-3518-4439-9a97-804a6353a33d` (📚 2026 Literature Review (PhD) — SLR),
consulta em 2026-07-31, filtro `Status = "Recommended Full Read"` → **367 registros** extraídos na íntegra.
A tabela abaixo lista apenas os registros **aderentes** aos eixos do artigo (44 de 367);
os demais 323 estão fora do escopo dos eixos (DT industrial/manufatura, redes, RL genérico,
manipuladores, surveys não relacionados etc.) e foram omitidos deliberadamente.

**Eixos:**
- **(a)** digital twins de robôs móveis (fidelidade, validação, calibração)
- **(b)** identificação grey-box/FOPTD em plataformas omnidirecionais
- **(c)** reality gap / sim-to-real (inclusive RoboCup)
- **(d)** simuladores SSL (grSim, rSoccer/rSim)
- **Tema A** (`\todocite` em 05_discussion.tex §B): identificação em malha fechada / viés de correlação / persistência de excitação sob realimentação
- **Tema B** (`\todocite` em 05_discussion.tex §E): prática de logging no RoboCup SSL / escassez de experimentos dedicados de identificação em robot soccer

**Aviso double-blind (A5/A6/A12):** os candidatos marcados com † são do mesmo grupo/instituição
(UFPE/RobôCIn — Barros et al.); citar SEMPRE em terceira pessoa, nunca como "our prior work".

## Tabela de candidatos

| ID Notion (Paper ID) | Título | Ano | Venue* | Eixo | Qual afirmação do artigo sustenta | Prioridade |
|---|---|---|---|---|---|---|
| SLR-2024-Marvin-250 | Simulation Modeling of Highly Dynamic Omnidirectional Mobile Robots Based on Real-World Data (Wiedemann et al.) | 2024 | n/i | b, c | Intro §1–2 e RW (B): modelagem de simulação de omnidirecionais dinâmicos a partir de dados reais — trabalho mais próximo da proposta do artigo | **alta** |
| SLR-2025-Marvin-1071 | Automated Tuning of Non-Differentiable Rigid Body Simulation Models for Wheeled Mobile Robots (Wiedemann et al.) | 2025 | n/i | b, c | Método/Discussão: calibração automática de parâmetros de simulador rígido (análogo ao bayesopt de 9 params); RW (D) | **alta** |
| SLR-2023-Pere-3366 | The Otbot project: Dynamic modelling, parameter identification, and motion control of an omnidirectional tire-wheeled robot (Giró, Celaya, Ros) | 2023 | n/i | b | RW (B): identificação de parâmetros em robô omnidirecional — baseline de literatura para "ID em omnidirecionais assume experimento dedicado" | **alta** |
| SLR-2024-Robert-002 | Evaluating the use of grey-box system identification for digital twins in manufacturing automation (Brennan, Lesage) | 2024 | n/i | a, b | Intro §2 e RW (A/B): uso de identificação grey-box como via de construção de gêmeos digitais | **alta** |
| SLR-2023-Tiboni-SB001 | DROPO: Sim-to-real transfer with offline domain randomization (Tiboni, Arndt, Kyrki) | 2023 | Robotics and Autonomous Systems 166:104432 | c | Intro §2 e Discussão: estimar parâmetros de simulador a partir de dados offline já disponíveis (paralelo direto ao uso de logs de competição); paper-âncora do protocolo SLR | **alta** |
| SLR-2025-Victor-849 † | Digital Twin-based Architecture and Design for Co-simulation of Omnidirectional Mobile Robots (Araújo, Barros) | 2025 | n/i | a, d | Intro §1 e RW (A/D): gêmeo digital de robô omnidirecional no contexto SSL; citar em 3ª pessoa | **alta** |
| SLR-2024-Hongjiu-762 | Digital Twin-Based Autonomous Navigation and Control of Omnidirectional Mobile Robots (Yang et al.) | 2024 | n/i | a | RW (A): DT de robô omnidirecional (navegação/controle) | **alta** |
| SLR-2024-Wilson-782 | Development and Validation of a Digital Twin for a Commercial Mobile Robot (Barioni et al.) | 2024 | n/i | a | RW (A): como a literatura valida fidelidade de DT de robô móvel (protocolo de validação) | **alta** |
| SLR-2025-Mateus-2445 † | Planning the Path with Reinforcement Learning: Optimal Robot Motion Planning in RoboCup Small Size League Environments (Machado et al.) | 2025 | n/i | c, d | Intro §1: times SSL desenvolvem políticas em simulação (ambiente rSoccer/SSL); consequência do reality gap; 3ª pessoa | **alta** |
| SLR-2023-Joo-2435 † | Dataset and Baseline Experiments for Self-Localization and Tracking in the RoboCup Small Size League (Melo et al.) | 2023 | n/i | Tema B | Discussão §E: o que os logs SSL de fato registram (visão/pose); candidato mais próximo disponível para a prática de logging SSL; 3ª pessoa | **alta** |
| SLR-2025-Andrei-2465 | Implementation of Firmware Based on Real-time Operating System for Small Size League Robot (Freiberger, Maximo, Loubach) | 2025 | n/i | Tema B, b | Resultados/Discussão: cadeia de atuação por roda no firmware SSL (suporta o mecanismo da zona morta elétrica por roda) | **alta** |
| SLR-2025-Sunny-053 | Benchmarking Sim2Real Gap (Katyara et al.) | 2025 | n/i | c | Intro §1: definição/medição do sim2real gap com DTs de alta fidelidade | **alta** |
| SLR-2026-Shinta-855 | Digital twin-enabled real-time parameter estimation of a wheeled mobile robot (Kosmaga et al.) | 2026 | n/i | a, b | RW (A/B): estimação de parâmetros de robô móvel acoplada a DT | **alta** |
| SLR-2024-Sunny-046 | Benchmarking Sim2Real Gap: High-fidelity Digital Twinning of Agile Manufacturing (Katyara et al.) | 2024 | n/i | c | Versão anterior/irmã do SLR-2025-Sunny-053 — usar apenas uma das duas | média |
| SLR-2024-Cludio-3751 | Calibration of Models for Digital Twins (Gomes et al.) | 2024 | n/i | a | RW (A): calibração de modelos como etapa central de engenharia de DT | média |
| SLR-2024-Giuseppe-3583 | Modelling for Digital Twins (Abbiati et al.) | 2024 | n/i | a | RW (A): fundamentos de modelagem para DT | média |
| SLR-2024-Valentina-3758 | Evaluating the Effectiveness of Digital Twins Through Statistical Model Checking with Feedback and Perturbations (Castiglioni et al.) | 2024 | n/i | a | RW (A): como definir/medir "eficácia"/fidelidade comportamental de um DT | média |
| SLR-2025-Valentina-3460 | DT-Stark: a tool for evaluating the effectiveness of digital twins through feedback and perturbations (Castiglioni et al.) | 2025 | n/i | a | Idem acima (versão ferramenta) — usar apenas uma das duas | média |
| SLR-2025-Charles-404 | Building a Digital Twin for Mobile Robots: a Step-By-Step Development Guide (Przechocki, Chauhan) | 2025 | n/i | a | RW (A): prática corrente de construção de DT de robô móvel | média |
| SLR-2024-Ruwen-765 | Digital twin for mobile robot modeling and simulation (Kang, Dong, He) | 2024 | n/i | a | RW (A): DT para modelagem/simulação de robô móvel | média |
| SLR-2025-Binhao-025 | Digital Twin Modeling Method Based on the Dynamic Characteristics of Mobile Robots (Ren et al.) | 2025 | n/i | a, b | RW (A/B): DT construído sobre características dinâmicas (não só cinemática) | média |
| SLR-2024-Renjun-764 | Research on Parameter Compensation Method and Control Strategy of Mobile Robot Dynamics Model Based on Digital Twin (Li et al.) | 2024 | n/i | a, b | RW (A/B): compensação de parâmetros do modelo dinâmico via DT | média |
| SLR-2026-Vladyslav-865 | Mathematical Models of Mobile Robots in the Digital Twin Concept: Comparative Analysis and Research of Usage Trends (Yevsieiev et al.) | 2026 | n/i | a | RW (A): panorama de modelos matemáticos usados em DTs de robôs móveis | média |
| SLR-2026-Hongjiu-952 | Digital Twin-Based Motion Planning and Virtual-Physical Mapping Control for an OMR Through Narrow Corners (Yang et al.) | 2026 | n/i | a | RW (A): DT de robô móvel omnidirecional (grupo de Yang/Xia) | média |
| SLR-2025-Yuanqing-870 | Digital Twin-Based Physical–Virtual Synchronization Control for a Carlike Mobile Robot Under Communication Delays (Xia et al.) | 2025 | n/i | a | Método: relevância do atraso (delay) na sincronização físico-virtual — apoia o termo de dead-time do FOPDT | média |
| SLR-2024-Gustavo-995 | Validação do Conceito Gêmeo Digital na Robótica Móvel (Del Conte et al.) | 2024 | n/i | a | RW (A): validação de DT em robótica móvel (contexto nacional/SBR) | média |
| SLR-2023-Laura-2396 | Improving Domain Transfer of Robot Dynamics Models with Geometric System Identification and Learned Friction Compensation (Schwendeman et al.) | 2023 | n/i | b, c | RW (B/C): identificação de dinâmica + atrito para transferência de domínio | média |
| SLR-2025-X-1803 | Dynamics as Prompts: In-Context Learning for Sim-to-Real System Identifications (Zhang et al.) | 2025 | n/i | b, c | RW (B): identificação de sistemas para sim-to-real (alternativa moderna ao grey-box) | média |
| SLR-2026-Hamidreza-031 | Data-Driven Surrogate Modeling and Dynamic System Identification Toward Digital Twin Realization (Ashrafi) | 2026 | n/i | a, b | RW (A/B): identificação dinâmica como caminho para DT | média |
| SLR-2026-Jhonattan-584 | Experimental Dataset and Servo Motor Modeling for the Quadruped Robot TWINIA (Cordero Pareja et al.) | 2026 | n/i | b, Tema B | Discussão: exemplo de coleta dedicada para modelagem de atuador (contraste com logs de operação) | média |
| SLR-2025-Muhammad-3451 | Optimized System Identification (SI) of BLDC motor using Data-Driven Modeling Methods (Khan et al.) | 2025 | n/i | b | Método: identificação de motor BLDC (nível roda/atuador) | média |
| SLR-2023-Chen-4265 | Bridging the Reality Gap via Progressive Bayesian Optimisation (Yu, Rosendo) | 2023 | n/i | c | Método/Discussão: otimização bayesiana para fechar o reality gap (paralelo ao bayesopt de 9 params) | média |
| SLR-2024-J-1786 | Bridging the Sim-to-Real Gap with Bayesian Inference (Rothfuss et al.) | 2024 | n/i | c | RW (C): inferência bayesiana de parâmetros de simulação | média |
| SLR-2024-Ahmad-2438 | Robots Path Planning in RoboCup Competitions: A Literature Review (Bany Abdelnabi, Rabadi) | 2024 | n/i | c, Tema B | Intro §1: panorama RoboCup; apoio fraco à escassez de experimentos dedicados | média |
| SLR-2025-Joo-4052 † | Onboard Perception and Localization for Resource-Constrained Dynamic Environments: A RoboCup SSL Case Study (Melo et al.) | 2025 | n/i | Tema B | Discussão §E: pipeline de percepção/logging SSL; 3ª pessoa | média |
| SLR-2025-Riei-2446 † | Analysis of the Introduction Trajectory Planning in Control Applied in Small Size League Robots (Rodrigues et al.) | 2025 | n/i | d, Tema B | RW (D): controle/planejamento SSL simulado vs real; 3ª pessoa | média |
| SLR-2024-Bonak-2283 | Digital Twins in Action: Optimizing FuzbAI Through Simulation and Modeling (Bošnak et al.) | 2024 | n/i | a, c | RW (A): DT aplicado a futebol robótico (foosball) — fidelidade comportamental em jogo | média |
| SLR-2025-Tyler-3364 | Wheeled Lab: Modern Sim2Real for Low-cost, Open-source Wheeled Robotics (Han et al.) | 2025 | n/i | c | RW (C): sim2real em robôs com rodas de baixo custo | média |
| SLR-2025-V-1914 | Integration of the TIAGo Robot into Isaac Sim with Mecanum Drive Modeling and Learned S-Curve Velocity Profiles (Schoenbach et al.) | 2025 | n/i | b, c | RW (B): modelagem de tração mecanum/omnidirecional em simulador com perfis de velocidade aprendidos | média |
| SLR-2026-Satoshi-140 | Actuator Reality Shaping for Zero-Shot Sim-to-Real Robot Learning (Yamamori et al.) | 2026 | n/i | c | Discussão: gap no nível do atuador (conecta com zona morta elétrica por roda) | média |
| SLR-2024-Jiri-548 | Low Fidelity Digital Twin for Automated Driving Systems: Use Cases and Automatic Generation (Vlasak et al.) | 2024 | n/i | a | RW (A): noção de níveis de fidelidade de DT | baixa |
| SLR-2025-Xilun-847 | Bridging Sim2Real – Digital Twin for Autonomous Mobile Robots (Ding et al.) | 2025 | n/i | a, c | RW (A/C): DT como ponte sim2real para robôs móveis | baixa |
| SLR-2025-Stefan-4287 | Tech United Eindhoven Middle Size League Winner 2024 (Kempers et al.) | 2025 | n/i (champion paper/TDP MSL) | Tema B | Discussão §E: exemplo de documentação de time RoboCup (MSL, não SSL) — apoio fraco | baixa |
| SLR-2026-Daniyal-059 | A Survey of Sim-to-Real Transfer Methods in Robot Learning (Musadiq) | 2026 | n/i | c | RW (C): survey sim-to-real genérico | baixa |
| SLR-2026-Zhuo-2413 | Kinematics and Comparative Evaluation of a Novel Decoupled, Redundantly-Actuated Four-Wheeled Omnidirectional Mobile Robot with Trajectory Tracking Validation (Zhang et al.) | 2026 | n/i | b | RW (B): validação de trajetória em omnidirecional 4 rodas | baixa |

\* **Venue:** o campo Venue/Qualis não está preenchido nesses registros do Notion (`Type`/`Qualis` majoritariamente vazios); "n/i" = não informado. Único venue explícito vem das Notes do DROPO. Verificar venue no PDF ao depositar.

## Lacunas SEM candidato no Notion (usuário precisa providenciar)

1. **Tema A — CRÍTICO (é um `\todocite`): identificação de sistemas em malha fechada / viés de correlação / persistência de excitação.**
   Nenhum dos 367 registros "Recommended Full Read" cobre a literatura clássica de closed-loop ID.
   Não há Ljung (*System Identification: Theory for the User*), Forssell & Ljung (*Closed-loop identification revisited*, Automatica 1999), Van den Hof (*Closed-loop issues in system identification*), Gevers, nem qualquer survey de identificação sob realimentação ou de persistência de excitação. **O `\todocite` da Discussão §B ficará descoberto sem provisão manual dessas referências** (sugestão: adicionar como entradas "Manual" no Notion antes de citar, para respeitar o guardrail de citar só de `slr/incluidos.bib`).

2. **Tema B — PARCIAL (é um `\todocite`): prática de logging SSL / escassez de experimentos dedicados de ID em robot soccer.**
   Não existe no Notion nenhum TDP/ETDP de time SSL, nenhum survey da liga SSL, nem trabalho que afirme diretamente a escassez de coletas dedicadas de identificação. Os candidatos mais próximos (SLR-2023-Joo-2435, SLR-2025-Joo-4052, SLR-2025-Andrei-2465) documentam o *que* se registra/atua em SSL, mas não sustentam sozinhos a afirmação de escassez. Opções: (i) reformular a frase para o que os candidatos sustentam; (ii) providenciar TDPs/ETDPs (ex.: TDPs publicados no RoboCup Symposium / ssl.robocup.org).

3. **Eixo (d) — CRÍTICO: simuladores SSL (grSim, rSoccer/rSim).**
   O rSim/rSoccer é o **baseline do artigo** e não há no Notion o paper do rSoccer (Martins et al., *rSoccer: A Framework for Studying Reinforcement Learning in Small and Very Small Size Robot Soccer*, 2021) nem do grSim (Monajjemi et al., 2016). Sem essas referências não é possível citar o próprio baseline. Providenciar (e citar em 3ª pessoa — restrição double-blind A5/A6).

4. **FOPDT/procest clássico (Método).** Não há referência clássica para a estrutura FOPDT (first-order plus dead time) nem para identificação de modelos de processo (`procest`/prediction error methods). Se o Método citar a origem da estrutura P1D, será preciso providenciar (ex.: Ljung; ou literatura de process control/PID tuning, Åström & Hägglund).

5. **Cinemática omnidirecional 4 rodas (Método, opcional).** Nenhum candidato clássico para o modelo cinemático de 4 rodas omnidirecionais (ex.: Rojas; Campion et al.). Os registros omnidirecionais do Notion são aplicações recentes, não a referência canônica do modelo.

## LISTA FINAL APROVADA (decisão do usuário, 2026-07-31)

**Decisões:** (1) entram os **13 prioridade alta** + PDFs das lacunas críticas; (2) Tema A resolvido
com clássicos pesquisados abaixo (máx. 5); (3) usuário deposita rSoccer + grSim; (4) Tema B será
**reformulado** para o que os candidatos SSL sustentam (sem afirmação de escassez como fato de survey).

### PDFs a depositar em `slr/pdfs/` (nomear pelo ID)

**Do Notion (13 alta):** SLR-2024-Marvin-250, SLR-2025-Marvin-1071, SLR-2023-Pere-3366,
SLR-2024-Robert-002, SLR-2023-Tiboni-SB001, SLR-2025-Victor-849, SLR-2024-Hongjiu-762,
SLR-2024-Wilson-782, SLR-2025-Mateus-2445, SLR-2023-Joo-2435, SLR-2025-Andrei-2465,
SLR-2025-Sunny-053, SLR-2026-Shinta-855.

**Baseline SSL (lacuna eixo d):**
- `EXT-rsoccer-2021.pdf` — Martins et al., "rSoccer: A Framework for Studying Reinforcement Learning in Small and Very Small Size Robot Soccer", RoboCup 2021 Symposium (LNAI).
- `EXT-grsim-2016.pdf` — Monajjemi et al., "grSim — RoboCup Small Size Robot Soccer Simulator", RoboCup 2011/2016 (LNAI).

**Tema A — clássicos de closed-loop ID (pesquisa 2026-07-31, máx. 5; depositar os que conseguir):**
- `EXT-forssell-ljung-1999.pdf` — Forssell & Ljung, "Closed-loop identification revisited", Automatica 35(7):1215–1241, 1999. **[núcleo do \todocite: viés de correlação em ID direta sob realimentação]**
- `EXT-vandenhof-1998.pdf` — Van den Hof, "Closed-loop issues in system identification", Annual Reviews in Control 22:173–186, 1998. [survey]
- `EXT-gustavsson-1977.pdf` — Gustavsson, Ljung & Söderström, "Identification of processes in closed loop — identifiability and accuracy aspects", Automatica 13(1):59–75, 1977. [clássico de identificabilidade em malha fechada]
- `EXT-ljung-1999-book.pdf` — Ljung, *System Identification: Theory for the User*, 2nd ed., Prentice Hall, 1999. [PEM/persistência de excitação; também cobre a lacuna 4 (procest/PEM)]
- `EXT-astrom-hagglund-1995.pdf` — Åström & Hägglund, *PID Controllers: Theory, Design, and Tuning*, 2nd ed., ISA, 1995. [estrutura FOPDT clássica — cobre a lacuna 4; opcional]

## Resumo quantitativo

- Registros com Status "Recommended Full Read" no Notion: **367** (todos extraídos).
- Candidatos aderentes listados: **44** — por eixo (com sobreposição): (a) 20, (b) 15, (c) 15, (d) 3, Tema A **0**, Tema B 7.
- Prioridade: 13 alta, 27 média, 5 baixa (contagem por linha da tabela).
- Lacunas críticas sem candidato: **Tema A (closed-loop ID)** e **eixo (d) (grSim/rSoccer — o baseline do artigo)**; Tema B parcial; FOPDT clássico e cinemática canônica opcionais.
