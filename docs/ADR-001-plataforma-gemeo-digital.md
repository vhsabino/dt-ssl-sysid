# ADR-001 — Plataforma do gêmeo digital do robô SSL: Python + MuJoCo (rota (a) agora, rota (b) experimental); Isaac Sim adiado; Gazebo descartado; MATLAB restrito à identificação

*Architecture Decision Record. Status: **ACEITO** (Victor, 02/09/2026). Substitui a discussão de `docs/REUNIAO_MODELO_E_LITERATURA.md` §3 e o item F6 do `ROADMAP.md`. Documento em PT-BR; citações no idioma original com página.*

## 1. Contexto

A tese entrega um gêmeo digital **comportamental** do robô SSL omnidirecional de 4 rodas (RobôCIn v2025): por grau de liberdade i ∈ {vx, vy, ω}, `G_i(s) = K_i·e^(−Td_i·s)/(τ_i·s+1)`, identificado de logs de competição (vx, vy) e de coleta dedicada em malha aberta (ω), com validação free-run em janelas re-ancoradas SE(2) (`config/metrics.json`). Os números publicados (SBR/LARS 2026): e_pos mediano em h_ref = 0,4 s de **0,039 m** (modelo) vs 0,101 m (cinemática ideal) vs 0,129 m (rSim); 10/10 eventos hold-out a favor do modelo; Shapley τ 55 % / Td 43 % / K 2 %.

Precisa-se agora de um **gêmeo executável completo**: (i) drop-in do simulador para o `ssl-unification` (software de estratégia da equipe), (ii) interface com modo Debug teleoperado (DualSense), (iii) preservação do harness científico, (iv) camada física opcional (bola, contato, roletes) e (v) caminho para a vertente RL (RQ3 da SLR; F6 do roadmap). Candidatos: NVIDIA Isaac Sim, MATLAB/Simulink+Simscape, MuJoCo, Gazebo, "outro".

Restrições de contexto: o `ssl-unification` fala o **ssl-simulation-protocol** da liga (o mesmo do grSim e do simulador da ER-Force) e só compila em Ubuntu (Qt6/GCC 11); o Victor tem Windows 11 com WSL2 Ubuntu, MATLAB R2026a, GPU NVIDIA e um DualSense; a SLR está no sprint crítico de skim (31/08–02/10), logo o custo de manutenção tem de ser baixo.

## 2. Critérios de decisão

| # | Critério | Peso | Por quê |
|---|---|---|---|
| C1 | Executa a planta FOPDT publicada como dinâmica do ego (rota (a)) sem reabrir a calibração | alto | é a contribuição científica; `REUNIAO_MODELO_E_LITERATURA` §3 já rejeitou reconstruir a física como modelo primário |
| C2 | Drop-in do `ssl-unification` (UDP + protobuf do ssl-simulation-protocol; visão 60 Hz + geometria; feedback) | alto | sem alteração no C++ da equipe; benchmark "gêmeo × grSim/ER-Force" vira troca de endpoint |
| C3 | Joystick PS5 em velocidade de corpo (modo Debug/excitação) | médio | teleoperação e coleta de excitação dedicada (ω) |
| C4 | Reprodutibilidade/CI: instalação por `pip`, headless, Windows + Linux, sem licença | alto | cada número do artigo é um comando |
| C5 | Caminho para RL em escala (RQ3; F6) | médio | MJX/MuJoCo-Warp ou Isaac Lab |
| C6 | Aproveita ativos existentes (Simulink pid_v3, USD/CAD, harness Python) | médio | — |
| C7 | Custo de hardware/operacional | médio | GPU mínima, RAM, disco, tempo de iteração |

## 3. Evidência da literatura (20 PDFs da SLR + 3 adicionados em 02/09/2026)

**Modelo por velocidade × modelo físico da roda.** Schoenbach et al. (CASE 2025) modelam o TIAGo++ Omni (mecanum) no Isaac Sim de duas formas e medem contra o robô real: o modelo físico (15 roletes × 6 esferas por rolete, 360 passos/s) e um "lightweight velocity-based model" que "directly sets the robot's base velocity to the desired Twist command" com 60 passos/s (p.1460). Erro relativo de distância em 4 s (Tab. I, p.1461): físico vs leve — x 8,24 % vs 7,36 %; y 4,61 % vs 3,89 %; xy 5,68 % vs 5,16 %; rotação 4,30 % vs 2,97 %. Conclusão dos autores: "The lightweight model is well-suited for high-throughput tasks such as reinforcement learning, while the physically accurate model can be used for fine-tuning and validation when precise behavior is required" (p.1461); e "mecanum and similar wheels are typically not simulated with full physical accuracy" (p.1458). Isso é exatamente a rota (a): a dinâmica do ego é o modelo identificado; o engine impõe contato.

**Custo do físico de roletes no Isaac Sim.** Wiedemann et al. (ICRA 2024) comparam nove colisores de rolete para o O3dyn: deriva em 4 m de 1,4–8 mm com esferas/cilindros manuais contra **33–116 mm** com convex hull/decomposition automáticos (Tab. I, p.16925); fator de tempo real **0,60–0,83** (< 1) para um único robô (Tab. II, p.16925); passos de física de 360 → 720/s para movimento lateral (p.16927–16928); e "a separate set of parameters was required for each trajectory" (p.16928). Wiedemann et al. (CASE 2025) automatizam a calibração (GA/DTW, 14 parâmetros) e concluem que "targeting a few high-impact parameters often ensures better results than tuning many less consequential ones" (p.2442) e que "instead of using Isaac Sim's default base controller, one could integrate the actual robot controller" (p.2442) — de novo a rota (a). Han et al. (Wheeled Lab, 2025) mostram a escala do Isaac Lab (1024–2000 ambientes numa RTX 3080), mas em carros Ackermann com rodas simples e admitindo que "these advances can rely on proprietary simulators, expensive hardware, and a daunting range of tools and skills" (p.1).

**Roletes discretos em MuJoCo.** Wan et al. (asRoBallet, arXiv 2604.24916, 2026) são o único caso localizado de omni-wheel tipo ETH com roletes discretos em MuJoCo: "Each wheel is constructed as a ring of 12 free-spinning rollers … attached to the main hub via hinge joints" (p.3), com receita de solver (Newton, cone elíptico, `impratio=10`, `noslip_iterations=1`, dt = 2 ms) e treino PPO em **CPU** (8 ambientes, 4×10⁶ passos, ~2,5 h). Advertem que, em regime dominado por contato, "training fails when a motor-type actuator is replaced with a velocity-type actuator" (p.4) e que "the primary bottleneck for sim2real ballbot RL is not the learning algorithm itself, but the fidelity of the contact model" (p.9) — limite de validade da rota (a), que justifica manter a rota (b) como backend experimental comparável.

**Baseline SSL em Simscape.** Araújo & Barros (LARS 2025) constroem um gêmeo Simscape Multibody do robô SSL da mesma equipe sem calibração empírica: RMSE de trajetória **149–231 mm** (Tab. II, p.5), atribuindo o resíduo a "unmodeled wheel slip and actuator latency" (p.5) — justamente o que a FOPDT captura (Td, τ). O artigo não descreve como a liberdade lateral dos roletes foi representada e tem inconsistências na Tab. I (r = 0,0051 m; Iz = 1,25 kg·m²), o que enfraquece Simscape como plataforma de referência.

**Ecossistema da liga.** grSim (Monajjemi et al., 2012) usa "a simplified dynamic model of the omni wheels" sobre ODE; rSoccer/rSim (Martins et al., 2021) herdou essa engine; o simulador da ER-Force usa Bullet. Todos falam o ssl-simulation-protocol — o gêmeo que falar o mesmo protocolo é comparável a eles por construção.

## 4. Análise das opções

| Opção | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Veredito |
|---|---|---|---|---|---|---|---|---|
| **Python + MuJoCo** | sim (atuadores de velocidade dead-beat: erro 0,14 mm/3 s vs planta) | nativo (UDP/protobuf em Python) | pygame/SDL2 | `pip`, Win/Linux, headless, determinístico | MJX / MuJoCo Warp | harness Python + CAD/USD → MJCF | CPU; 1065 passos/s c/ 12 robôs | **ADOTADA** |
| Isaac Sim 5.1 | sim (rota (a) em Schoenbach) | extensão Python dentro do Kit | via omni.appwindow | não (RTX 4080 16 GB, 32 GB RAM, 50 GB; sem CI) | Isaac Lab (forte) | USD existente, mas quebrado (rigid bodies deletados, 80 juntas inativas, campo ausente) | alto; RTF < 1 com roletes | adiada; MJCF/URDF importável depois |
| MATLAB Simulink/Simscape | sim (pid_v3 já é isso, 9,5 s/sim) | UDP+protobuf em Simulink: penoso | `vrjoystick` limitado | licença; sem CI | RL Toolbox lento | Simulink pid_v3 | licença | mantido só como identificação (`procest`) e oráculo |
| Gazebo | via ROS 2 | bridge ROS 2 | ROS `joy` | Ubuntu apenas | fraco | nada | médio | descartado |
| grSim / ER-Force como plataforma | não (engine própria; não aceita a planta identificada como ego sem fork) | nativo | não | build C++ | não | — | — | usados como **benchmarks**, não como plataforma |

## 5. Decisão

1. **Núcleo em Python (`dtssl`)**: a planta comportamental publicada é o backend padrão (`fopdt`), com bola de duas fases, colisões e chute/dribbler analíticos (`dtssl.sim.twin_world`), servidor ssl-simulation-protocol (`dtssl serve`) e GUI PySide6 com DualSense (`dtssl gui`). O harness científico (`dtssl.eval`, `dtssl.analysis`) permanece bit-idêntico ao que gerou o artigo.
2. **MuJoCo como camada física**, sob a mesma interface `World`: rota (a) `mujoco-velocity` (a FOPDT dirige o ego; MuJoCo impõe contato — Schoenbach 2025, Wiedemann 2025) é a entrega funcional; rota (b) `mujoco-rollers` (4 rodas × 12 roletes elipsoidais, receita de Wan 2026) é backend experimental para estudar o limite de validade da rota (a) e para RL dominado por contato.
3. **Isaac Sim adiado**: sem ganho científico agora (99,6 % das janelas do hold-out são translação-dominadas; contato não é necessário), custo de hardware acima do disponível e ativo USD quebrado. O MJCF gerado por `dtssl mjcf` (ou um URDF derivado) é o caminho de importação se a vertente RL exigir Isaac Lab em 2027.
4. **MATLAB** fica para identificação (`procest`, `matlab/dtssl/identify_*`) e para o oráculo Simulink `pid_v3` de reconciliação; **Simscape não** será usado como plataforma do gêmeo (o baseline LARS 2025 mostra 150–240 mm sem calibração).
5. **Gazebo descartado** (Linux-only, acoplado a ROS 2, sem uso na liga, sem vantagem em RL).
6. **Sistema operacional**: **não migrar** a máquina para Ubuntu. O `ssl-unification` compila no WSL2 já existente (WSLg para a GUI Qt); o gêmeo e o joystick rodam no Windows ou no WSL. Dual-boot Ubuntu só se esta máquina for operar robôs reais/base station (multicast em interface física, USB do nRF24) ou Isaac Lab.

## 6. Consequências

- Uma única API (`World`) para três níveis de fidelidade (comportamental, MuJoCo rota (a), MuJoCo rota (b)) e as mesmas métricas: a comparação "comportamental × físico × grSim/ER-Force" torna-se um experimento de troca de backend/endpoint — responde diretamente à cobrança da banca sobre o grSim.
- O gêmeo grava sessões no **mesmo contrato dos logs** (`SessionRecorder`), logo o harness de fidelidade avalia também o que o `ssl-unification` fez contra o gêmeo.
- Risco assumido: a rota (a) não representa escorregamento, acoplamento lateral por CoM nem "initial forward push" (Wiedemann 2024/2025); a rota (b) e a coleta dedicada de rotação são os instrumentos para medir esse limite.
- Dívida: goldens v2 com ω promovido devem ser gerados no MATLAB do Victor (`export_plant_golden(ev,'theta','promoted','tag','v2')`); ssl-unification ainda não foi compilado contra o gêmeo (scripts em `tools/ssl_unification/`).

## 7. Condições de revisão

Reabrir este ADR se: (i) a vertente RL exigir > 10³ ambientes paralelos com contato de roletes (avaliar MuJoCo Warp antes de Isaac Lab); (ii) a rota (b) mostrar ganho de fidelidade ≥ 20 % sobre a rota (a) em janelas rotação-dominadas de coleta dedicada; (iii) a equipe migrar o `ssl-unification` para outro protocolo.

## Referências (chaves de `latex/refs/references.bib` + 3 novas em `slr/pdfs/`)
`wiedemann2024simulation` (ICRA 2024, pp. 16923–16929); `wiedemann2025automated` (CASE 2025, pp. 2436–2443); Schoenbach et al. 2025 (CASE 2025, pp. 1456–1463, DOI 10.1109/CASE58245.2025.11163930 — `SLR-2025-V-1914`); Han et al. 2025 (arXiv 2502.07380 — `SLR-2025-Tyler-3364`); Wan et al. 2026 (arXiv 2604.24916 — `EXT-2026-Omniwheel-Mujoco`, `wan2026asroballet`); `araujo2025digital` (LARS 2025); `monajjemi2012grsim`; `martins2021rsoccer`; NVIDIA Isaac Sim 5.1 requirements (docs, consultado 02/09/2026); MuJoCo Warp/MJX (docs, 02/09/2026).
