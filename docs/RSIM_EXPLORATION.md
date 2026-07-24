# Exploração de viabilidade — RSimReplay (rSoccer / rSim)

*Fase de exploração do Prompt 8. NÃO implementado. Itens 1 e 4 são bloqueantes ⇒ PARE para decisão conjunta. Ambiente NÃO foi alterado (só dry-run, builds em pasta temp e download de wheel — nada instalado). Data: 2026-06-16.*

## Veredito da exploração: **BLOQUEADO** (itens 1 e 4)

| # | Item | Resultado |
|---|---|---|
| 1 | Instalar rsoccer-gym + rSim | ❌ **BLOQUEIO** — `rc-robosim` (o rSim) não compila em cp314-win; depende de **ODE** (lib de sistema) ausente |
| 2 | Frame da ação / leitura de pose | ✅ ação = `(v_x,v_y,v_theta)` de **corpo**; pose lida via `get_state()` (x,y em m; θ em **graus**) |
| 3 | dt interno | ⚠️ **inteiro em ms** (`int(time_step*1000)`); 1/60 s→16 ms (62,5 Hz) ≠ 1/60 → **reamostrar** |
| 4 | Setar velocidade IC (velb0) | ❌ **BLOQUEIO** — `reset` posiciona robô só com `[x,y,θ]`; sem setter de velocidade → começa do REPOUSO |
| 5 | Comando direto (sem controle) | ✅ `Robot(v_x,v_y,v_theta, wheel_speed=False)` vai DIRETO ao `robosim.SSL.step` |

## 1. Instalação — BLOQUEIO (Python 3.14 / Windows)
- `rsoccer-gym==1.4` é wheel pura (`py3-none-any`), instala ok. Depende de **`rc-robosim>=1.2.0`**.
- `rc-robosim==1.2` é **sdist (24 kB, sem wheel)** = extensão C++ via scikit-build + CMake + pybind11, que **embrulha ODE (Open Dynamics Engine)**.
- Tentativa de build (`pip wheel rc-robosim`), cadeia de falhas em cp314-win (MSVC 2022, CMake 4.3, Ninja presentes):
  1. pybind11 antigo (buscado por FetchContent) exige `cmake_minimum_required < 3.5`, removido no CMake moderno. **Contornável** com `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` (passei desse ponto — não é reimplementação, é flag de build).
  2. Próximo erro, **fatal**: `Could NOT find ODE (missing: ODE_INCLUDE_DIRS ODE_LIBRARIES)` em `FindODE.cmake` / `CMakeLists.txt:34`. O ODE **não é vendorizado nem pip-instalável**; precisaria ser instalado no sistema (vcpkg/compilação) e apontado ao CMake.
  3. Mesmo achando o ODE, o pybind11 buscado é antigo (era CMake<3.5 ⇒ pybind11 ~2.5) e **antecede o suporte a Python 3.14** → a compilação provavelmente falharia em cp314 de qualquer modo.
- **Conclusão:** sem wheel para cp314; build de fonte exige ODE + patch de pybind11/CMake + compatibilidade cp314. Não trivial. Conforme sua diretriz, **NÃO reimplementei grSim**. Decisão conjunta necessária.

## 2. Interface de ação e leitura de pose (lido da fonte, não executado)
- `rsoccer_gym/Simulators/rsim.py::RSimSSL.send_commands`: com `cmd.wheel_speed=False`, monta `[0, v_x, v_y, v_theta, 0, kick_x, kick_z, dribbler]` e chama `self.simulator.step(sim_cmds)`. Ou seja, a ação é **velocidade de corpo (v_x, v_y, v_theta)** — casa com o comando de CORPO do nosso log (sem rotacionar). *(corpo-vs-mundo a confirmar em runtime quando o engine existir.)*
- Pose: `get_frame()` → `simulator.get_state()` → `FrameSSL.parse`: por robô `x, y` (m), `theta` (**graus**, convenção rSoccer → converter p/ rad no harness), e velocidades reportadas `v_x, v_y, v_theta`.

## 3. dt — reamostragem necessária
`SSLBaseEnv.__init__`: `time_step_ms = int(self.time_step*1000)`. Inteiro em ms ⇒ 1/60 s vira 16 ms (62,5 Hz), não 1/60. Tratamento: rodar o sim em passo pequeno (ex. 1 ms) e **substep acumulando ~16,67 ms por passo 1/60 do harness**, lendo a pose nos limites da grade (interp linear / θ via unwrap), igual ao loader. Não é bloqueio, mas é fiação extra.

## 4. Justiça da condição inicial — BLOQUEIO (velb0 não-setável)
`RSim.reset` / `robosim.reset(ball_pos, blue_pos, yellow_pos)` recebem por robô **apenas `[x, y, theta]`** (a bola recebe velocidade; o robô **não**). O engine **lê** velocidade mas não a **seta**. ⇒ o rSim **começaria cada janela do repouso**, enquanto o twin começa de `velb0` (velocidade de corpo real em t0). **Assimetria injusta.** Tratamentos propostos (sua escolha):
- **(A, recomendado) Warm-up por janela:** reposicionar em `pose(t0 − Lw)` e dirigir o rSim com os comandos reais `cmd[t0−Lw : t0]` até t0, de modo que o estado em t0 reflita o histórico real (acelera até ~velb0). Espelha o que o twin faz via `velb0`+`prime_delay`. Mais simétrico.
- **(B) Excluir as primeiras K amostras** da métrica em AMBOS os plants igualmente (descarta o transitório de IC). Simples e simétrico, mas perde resolução em horizonte curto (onde o arranque-do-repouso mais penaliza).
- **(C) velb0=(0,0,0) para ambos** (twin incluído): IC idênticas, mas muda a avaliação do twin da convenção promovida. Menos fiel.
Recomendo **A** como principal, com **B** como verificação de robustez.

## 5. Comando direto — OK
Confirmado: `Robot(yellow=False, id=0, v_x=vx, v_y=vy, v_theta=w, wheel_speed=False)` → `send_commands` → `robosim.SSL.step` aplica a velocidade **direto, sem controle de movimento**. Isola a dinâmica de planta. Frame de corpo (= nosso log).

## Caminhos para a decisão conjunta
1. **Ambiente Linux ou Python 3.11/3.12 + ODE** (apt/vcpkg) para compilar `rc-robosim`; rodar a comparação rSim lá e trocar resultados por arquivo (exportar as janelas do harness → rodar rSim → reimportar pose_sim p/ a métrica). O harness já produz `WindowRollout` serializável.
2. **Adiar o rSim nesta rodada:** manter `IdealKinematicPlant` como default (o bin de translação já dá **GO** twin-vs-ideal). Revisitar rSim quando houver ambiente buildável.
3. **Forçar o build neste Windows/cp314:** instalar ODE + fixar pybind11 moderno + flags CMake — yak-shave grande, incerto em cp314 (pybind11 antigo). Não recomendado.

**Aguardo sua decisão (itens 1 e 4).** Quando definir caminho + tratamento de justiça, implemento `RSimReplay(Plant)` reusando `metrics.py` (mesmas janelas, mesmos gates; `prime_delay`=NO-OP, documentando que a ausência de atraso de transporte no rSim é justamente onde o twin deve vencer).
