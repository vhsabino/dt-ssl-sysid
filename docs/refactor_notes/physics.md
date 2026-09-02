# Notas de refatoração — backend físico MuJoCo (`dtssl.physics`), 02/09/2026

Agente: *physics* (`src/dtssl/physics/{__init__,mjcf,mujoco_world,cli}.py`, `models/mjcf/`, `tests/test_physics_*.py`, esta nota).
Escopo: `docs/SPEC_DTSSL.md` §3, §4.2, §4.6, §4.7. Nada em `sim/`, `models/`, `bridge/`, `gui/` foi tocado; `World`,
`RobotSpec`, `FieldGeometry`, `Scene`, `RobotCmd`/`RobotState`/`BallState`/`WorldState` são usados **como estão** e a
interface pública espelha a do `TwinWorld` (mesmos extras `robot_keys`, `has_ball`, `set_present`, `effective_command`,
contadores `kicks`/`contacts`/`watchdog_hits`, `watchdog_clock="wall"|"sim"|callable`). `mujoco` (3.12.0) é importado
**só** dentro de `MuJoCoWorld`/`describe_xml`/`--view`; `import dtssl.physics` e a geração do XML não precisam dele
(teste `test_import_physics_does_not_import_mujoco`).

## O que foi entregue

| Item | Arquivo(s) | Resumo |
|---|---|---|
| Gerador MJCF | `src/dtssl/physics/mjcf.py` | XML programático (`xml.etree`) a partir de `config/field_divB.json`, `config/robot_limits.json`, `config/robot_geometry.json` (via `dtssl.config.load_field/load_limits/load_geometry` quando existem, senão leitura local). `build_field_xml` (chão plano `condim=3` μ=0,9; linhas = caixas finas visuais `contype=0`; círculo central como polígono de 36 segmentos; áreas penais; gols com fundo e duas laterais; paredes de *boundary* a 300 mm), `build_ball_xml` (esfera `freejoint`, `condim=6`, `priority=1`, `solref=(0,01, 0,6)`), `build_robot_xml(team, rid, route, ...)` (rotas a/b), `build_world_xml(scene, route, ...)` (compõe fragmentos, deduplica *assets*/*defaults*), `describe_xml` (markdown de corpos/juntas/atuadores/sites + tamanhos compilados). Bitmasks de contato: chão 1, bola 2, chassi 4, parede 8, rolete 16 — o chassi **nunca** toca o chão, roletes só tocam o chão, bola toca chão/chassi/paredes. |
| Mundo | `src/dtssl/physics/mujoco_world.py` | `MuJoCoWorld(route="a"|"b", scene=..., n_blue, n_yellow, params, plant, field, spec, ball, wheel, solver, route_a, route_b, timestep, n_rollers, wheel_control, kv_*, force_max, torque_max, saturate, deadzone, watchdog_s, watchdog_clock, kick_cooldown_s, dribbler_*, boundary, chassis, **unknown→aviso)`. `step(dt)`: `n_sub = round(dt/timestep)` substeps com `model.opt.timestep = dt/n_sub` (tempo simulado **exato** para qualquer `dt`); watchdog; rota a → planta → alvo do servo; rota b → IK → alvo das rodas (ou PI por substep); chute; força do dribbler por substep (`xfrc_applied`); `state()` de `qpos/qvel` (θ em (−π, π], velocidade de corpo, `has_ball` pelo cone do dribbler de `sim.collisions.ball_in_front`, bola com `z` = base acima do chão e flag `rolling` = deslizamento < 10 % de |v|). `teleport_robot` (velocidade global opcional; `present=False` estaciona o robô fora do campo), `teleport_ball(rolling=)`, `set_present`, `set_plant_params` (θ trocado *in place*, buffers de atraso preservados), `viewer()` (`mujoco.viewer.launch_passive`, sincronizado a cada `step`), `close()`. Expõe `model`, `data`, `xml`, `robots`, `wheel_speeds(team, id)`, `plant_pose(team, id)`. |
| Registro | `dtssl.sim.backends` (inalterado) | `make_world("mujoco-velocity")` = rota a, `make_world("mujoco-rollers")` = rota b (teste `test_registry_state_teleport`). |
| CLI | `src/dtssl/physics/cli.py` | `register(subparsers)` descoberto por `dtssl.cli`: `dtssl mjcf [--route a|b|both] [--out DIR] [--n-blue N] [--n-yellow N] [--n-rollers N] [--no-boundary]` escreve `ssl_route_<r>.xml` + `ssl_route_<r>.md`; `dtssl mjcf --route a --view [--demo] [--seconds S]` abre o *viewer* passivo num `MuJoCoWorld` em tempo real. Também `python -m dtssl.physics.cli ...`. |
| Amostras | `models/mjcf/ssl_route_a.{xml,md}` (6×6, 35 kB), `models/mjcf/ssl_route_b.{xml,md}` (1×1, 52 kB) | Geradas pela CLI; cabeçalho avisa para regenerar em vez de editar. |
| Testes | `tests/test_physics_mjcf.py` (13 puros + 11 `requires_mujoco`), `tests/test_physics_world.py` (24, `requires_mujoco`) | **48 testes**, todos passando (3,4 s); suíte inteira: 265 passed, 1 skipped. |

## Modelo

### Comum (campo, bola)

- **Chão**: plano infinito, `condim=3`, μ=0,9 (o valor efetivo bola–chão e rolete–chão vem dos geoms com `priority`/max).
- **Bola**: r=0,0215 m, m=0,046 kg (`robot_limits.json:ball`), `condim=6` com atrito `(μ_desl, μ_tors, μ_rol) = (0,1857, 0,005, 0,00093)`.
  Os dois coeficientes são **derivados do modelo de duas fases do ssl-unification** (`Env.h`): `μ_desl = 1,82135/g` (fase deslizando)
  e, para esfera rolando sem escorregar, `a = μ_rol·g/(1,4·r)` ⇒ `μ_rol = 0,3025·1,4·0,0215/g`. A transição deslizar→rolar
  emerge da física (bola chutada sem spin perde ≈2/7 da velocidade deslizando). Medido: chute a 3 m/s → 2,96 m/s no 1º frame,
  2,16 m/s a 0,53 s (≈−1,6 m/s²), 1,96 → 1,67 m/s entre 1,0 e 2,0 s (≈−0,29 m/s² rolando; alvo 0,3025). `priority=1` faz a bola
  mandar nos parâmetros dos seus contatos. `solref=(0,01, 0,6)`: `dampratio<1` dá algum quique nos chips (não calibrado a e=0,5).
- **Gols/paredes**: caixas (`contype=8`), altura 0,12 m, espessura 0,02 m; gol com profundidade 0,18 m fora da linha; *boundary* a 0,3 m.
- **Chassi** (ambas as rotas): malha convexa inline (`<mesh vertex=...>`) = prisma em **D** (cilindro r=0,09 m cortado plano em x=0,075 m,
  a face do dribbler; corda de 99 mm), altura 0,15 m; `<inertial>` explícito de cilindro uniforme (m=2,4 kg, `I_z = ½mr² = 0,00972`,
  `I_x=I_y = m(3r²+H²)/12`) com CoM no eixo da junta — a malha em D colocaria o CoM 3,3 mm atrás do centro e acoplaria os
  *slides* ao *hinge* (ver "Pegadinhas"). `compiler inertiafromgeom="auto"` (com `"true"` o `<inertial>` é ignorado). Visual: placa
  na cor do time, 4 pontos do padrão SSL de id (tabela do rulebook, ordem FL/FR/BR/BL — só cosmético), barra do dribbler,
  sites `<nome>_dribbler` (0,075 m à frente, z=0,0215) e `<nome>_kicker`.
- **Contatos duros**: chassi e paredes com `solref=(0,004, 1)` (≥ 2·timestep, o mínimo "seguro" do MuJoCo) e `solimp=(0,95, 0,99, 0,001)`.
  Penetração medida empurrando a parede a 1 m/s (150 N): 0,2 mm (rota a) e 0,3 mm (rota b).

### Rota a — `mujoco-velocity` (entregue como funcional)

- Chassi em `slide x + slide y + hinge z` (corpo na origem do mundo **sem** pos/quat: os eixos dos *slides* são expressos no
  frame do corpo, logo `qpos = (x, y, θ)` é a pose absoluta) e três atuadores `velocity`.
- A **planta comportamental é a dinâmica do ego**: cada robô tem uma `AnalyticFOPDTPlant` (θ oficial) avançada com o comando
  de corpo; o alvo do servo é a **média** da velocidade da planta no mundo nos dois extremos do intervalo,
  `½[R(θ₀)v_b(k) + R(θ₁)v_b(k+1)]` com `θ₁ = θ₀ + dt·½(w_k + w_{k+1})`, exatamente o integrando trapezoidal de
  `deadreckoning_p1d`. `θ₀` é o heading **do MuJoCo** (não o da planta): um robô desviado por colisão continua a aplicar a
  velocidade de corpo no seu heading real; a pose interna da planta nunca é usada (`plant_pose()` só para depuração).
- **Servo dead-beat**: integrador `Euler` (explícito para o atuador) com `kv = m/h` nos *slides* (2,4/0,00208 = 1152 N·s/m) e
  `kv = I_z/h` no *hinge* (4,67 N·m·s/rad): `qvel` iguala o alvo após **um** substep, e a posição integra `dt·alvo` — o
  chassi reproduz a planta **exatamente** (teste `test_route_a_exact_when_unclamped`: < 1e-6 m/rad sem limites de força).
  `MuJoCoWorld._set_substep` reescala os ganhos se `dt` mudar o substep. Ganhos explícitos (`kv_slide`, `kv_hinge`) continuam
  possíveis.
- **Limites de força**: `forcerange = ±150 N` nos *slides* (≈62 m/s²) e `±3 N·m` no *hinge* (≈310 rad/s²), aplicados como
  `forcerange` do MJCF (corretos com Euler). Ficam acima do pico da planta `m·K·u/τ` para u ≤ 3 m/s (113 N) — mas o
  dead-beat pede o **salto por amostra** num único substep, então degraus grandes saturam por 1–2 substeps: erro máximo
  medido 5,7 mm num degrau de 3 m/s e 0,0068 rad num degrau de 10 rad/s (contra 0,135 mm e 0 rad em (1, 0,5, 1)).
  Empurrando a parede o robô aplica 150 N; robô–robô de frente: faces planas se tocam a 0,150 m (2×0,075), sobreposição < 0,5 mm.
- **Velocidade reportada**: o MuJoCo mantém a média ZOH do intervalo; `state()` gira-a para o corpo com o heading do
  **meio** do intervalo (`θ − ½dt·w`), o que a faz coincidir com a velocidade de corpo da planta (< 3 % a w = 3 rad/s).
- Chute: se a bola está no cone do dribbler e `kick_speed > 0` (com `kick_cooldown_s = 0,1` e consumo único, como no
  `TwinWorld`), `qvel` da bola = `v·(cos α cos θ, cos α sin θ, sin α)`, α = 45° para chip (`kick_angle_deg > 0`), spin zerado;
  clamps `kick_flat_max`/`kick_chip_max`. Chip a 3 m/s sobe 0,227 m (balística: 0,229).
- Dribbler: com `dribbler_rpm > 0` e bola a ≤ 0,16 m / ±0,6 rad, mola-amortecedor (k=40 N/m, c=1,5 N·s/m, força máx. 1 N ×
  (0,25 + 0,75·rpm/rpm_max)) para o "bolso" a 0,0965 m da frente, aplicada em `xfrc_applied` da bola a cada substep. Segura a
  bola a 0,097 m com o robô recuando a 0,3 m/s e girando a 0,5 rad/s (teste, ambas as rotas).

### Rota b — `mujoco-rollers` (experimental)

- Chassi com `freejoint` (parte com a base a z=0,5 mm) + 4 rodas em `R·(cos φ, sin φ)`, z = r, com **hinge no eixo radial
  para dentro** `−(cos φ, sin φ, 0)`: assim `ω_i > 0` move o centro da roda pela tangente **CCW** `(−sin φ, cos φ)`, e vale
  `ω_i·r = −sin φ_i·vx + cos φ_i·vy + R·ω` (verificado: `vx>0` → +x, `vy>0` → +y, `w>0` → θ cresce; teste dos eixos no XML).
  Roda: cubo visual (sem colisão), m=0,15 kg, `armature = N²·J_rotor = 16·9,25e-6 = 1,48e-4 kg·m²` (rotor do EC-45 flat
  refletido pela redução N=4 — N é desconhecido e ficou parâmetro).
- **Roletes**: `n_rollers=12` corpos por roda, no círculo de raio `ρ = r − r_rolete = 23,5 mm` no plano (tangente, z),
  hinge livre (damping 1e-6, armature 1e-7) com eixo tangente a esse círculo (⊥ ao eixo da roda e à direção radial local —
  roda omni de 0°). Forma **elipsoide** (barril) com semieixo `a` ao longo do eixo do rolete calculado para que o perfil
  `q(s)` coincida com o arco da roda em meia corda até o vizinho (`a = 13,6 mm`, `b = 6 mm`): o envelope fica circular a
  ~0,03 mm. Com cápsulas (`roller_shape="capsule"`, ℓ=4 mm) o envelope oscila ±0,3 mm e isso vira uma resistência ao
  rolamento visível (velocidade de regime −2,3 % a kv=0,5; −6 % a kv=0,02); com elipsoides −0,6 %. Roletes só colidem com o
  chão (μ=1,0, `condim=3`, `solimp=(0,95, 0,99, 0,001)`), massa 0,002 kg.
- **Solver** (receita Wan et al. 2026): `solver=Newton`, `cone=elliptic`, `impratio=10`, `noslip_iterations=1`,
  `timestep = 1/480 = 2,08 ms` (8 substeps por 1/60 s; ≈ 0,002 da receita) — os mesmos `<option>` da rota a.
- **Atuação**: `velocity` por roda com `kv_wheel = 0,1 N·m·s/rad` e `forcerange ±1,5 N·m` (≈ torque nominal 0,084 N·m ×
  N=4 × sobrecarga do driver; parâmetro). `h·kv/I_roda ≈ 0,9` ⇒ quase dead-beat quando a roda patina, estável com Euler.
  Alternativa `wheel_control="pi"`: atuadores `motor` (`ctrlrange ±1,5`) e PI em Python por substep com os ganhos do
  firmware (`Kp=0,3194`, `Ki=6,434`, limite do integrador 2527,1 em "unidades PWM", assumido = fundo de escala
  `pwm_max`): **a escala de unidades do firmware é desconhecida**; com esses números a malha fica dominada pelo integrador
  (ζ≈0,06 com a inércia refletida) e ultrapassa ~60 % — mantido como esqueleto experimental (`PIGains`), não como default.
- IK de `dtssl.kinematics.body_to_wheel_matrix` (import preguiçoso, validado contra a fórmula local `[−sin φ, cos φ, R]/r`),
  zona morta por roda opcional (`deadzone=True`, 1,567 rad/s de `robot_limits.json`; default desligada).
- Medido (vx = 0,5 m/s por 2 s): 0,976 m (**−2,4 %** do integral do comando, sendo ~2 % o transitório limitado por tração,
  t90 ≈ 0,1 s), deriva lateral 0,01 mm, heading 0,0000 rad, regime 0,497 m/s; w = ±1/−2/−3 rad/s: sentido correto, regime
  a −0,4 %, gira no lugar (< 0,2 mm). vy = 0,5 m/s: 0,967 m com deriva de heading −0,018 rad (assimetria 60°/135° com
  patinação); vx = vy = 0,5: −3,9 %, heading −0,08 rad.

## Erros e desempenho alcançados (testes/experimentos, MuJoCo 3.12.0, 2 vCPU x86-64)

| Medida | Valor |
|---|---|
| Rota a vs `AnalyticFOPDTPlant` standalone, 3 s, cmd (1, 0,5, 1) | **0,135 mm / 0,00000 rad** (limite do teste 2 mm / 0,01 rad) |
| idem, cmd (2, 1, 3) / (−1, 0,5, −2) / (0, 0, 5) | 1,54 mm / 0,27 mm / 0,00046 rad |
| idem, sem limites de força (`RouteAOptions(force_max=None, torque_max=None)`) | < 1e-6 m e rad (exato) |
| Rota b vx = 0,5 m/s por 2 s | −2,4 % da distância, deriva 0,01 mm (limites ±5 %, 5 cm) |
| Penetração na parede (1 m/s contra o *boundary*) | 0,2 mm (a), 0,3 mm (b) |
| Rota a, 12 robôs (6×6) | **1065 passos-mundo/s** (17,8× tempo real; 8520 `mj_step`/s) |
| Rota a, 1 robô | 6546 passos/s (109×) |
| Rota b, 1 robô | **1214 passos/s** (20×; 9710 `mj_step`/s; `nv=64`) |
| Rota b, 12 robôs | 110 passos/s (1,8×; `nv=702`, ~50 contatos) |
| `fopdt` (TwinWorld), 12 robôs, referência | 2954 passos/s |

## Pegadinhas encontradas (e por que o desenho é este)

1. **`forcerange` + integradores implícitos = servo lento.** Com `implicitfast`/`implicit` o MuJoCo aplica a derivada do
   atuador em relação à velocidade (−kv) mesmo quando a força está saturada; o substep saturado fica sobre-amortecido por
   `(m + h·kv)/m`. Medido: 60 N de clamp → 6 mm de erro (contra 1 mm sem clamp); 20 N·m no *hinge* com `kv=200` → heading
   diverge. Tentativa de limitar a força "moldando" o alvo por substep (`ctrl = qvel + clip(v* − qvel, ±F/kv)`) sofre do
   mesmo efeito. Solução: Euler explícito + ganho dead-beat `kv = m/h` (+ `forcerange` correto). Sem `forcerange` e com
   `implicitfast` o rastreamento era bom (0,1–0,6 mm) mas o robô empurrava paredes com 4800 N e quicava (jitter de 2 mm).
2. **Corpo da rota a com `pos`/`quat` de spawn.** Os eixos dos *slides* são do frame do corpo: com o corpo girado pelo θ
   inicial, `qpos` deixa de ser a pose absoluta (a física era consistente mas a parede "estava" noutro lugar). Corpo na
   origem, pose só em `qpos`.
3. **`inertiafromgeom="true"` ignora `<inertial>`** — o CoM da malha em D (−3,3 mm) acoplava translação e rotação e o heading
   derivava 0,0001 rad/passo com `w=0`. Agora `auto` + inercial explícito.
4. **Cápsulas como roletes** produzem envelope poligonal (a roda "sobe" nas pontas) → resistência ao rolamento espúria.
   Elipsoides com o semieixo derivado da geometria resolvem.
5. Rota a: erro pequeno mas não nulo em degraus grandes é o limite de força escolhido (150 N), não o integrador.

## Limitações conhecidas

- Rota a é um "empurrador cinemático" com força limitada a 150 N/3 N·m: colisões robô–robô são resolvidas pelo solver com
  esses limites (não pela tração das rodas); ambos param, sem *slip*. Massa 2,4 kg = só o chassi (rodas não somadas).
- A planta da rota a assume `dt` uniforme (o atraso `Td` é em amostras); `step(dt)` com `dt` variável desloca o atraso.
- Rota b: acima de ~1,5 m/s de degrau as rodas patinam forte (torque 1,5 N·m ≫ tração μN ≈ 7 N por roda) e o chassi pode
  saltar (z até 44 mm num degrau de 2 m/s); usar rampas. Comandos com `vy` deixam deriva de heading (−0,02 rad em 2 s a
  0,5 m/s). Modo PI sem escala de unidades do firmware (ver acima). 12 robôs com roletes rodam a 1,8× tempo real.
- Quique da bola (chip) não calibrado a e=0,5; a bola em contato é "dura" (`solimp` da bola 0,9–0,95).
- Sem malhas visuais dos USD (`usd/`): primitivas (prisma em D, cilindros, elipsoides). `physics/assets/` fica reservado.
- O viewer (`mujoco.viewer.launch_passive`) precisa de display/GL; não é testado no CI.

## Como abrir o viewer

```bash
pip install -e ".[mujoco]"            # ou pip install mujoco
dtssl mjcf --route a --view --demo    # 6x6, robôs em círculos com dribbler ligado/desligado
dtssl mjcf --route b --n-blue 1 --n-yellow 0 --view --demo --seconds 20
```

Em código:

```python
from dtssl.sim.backends import make_world
from dtssl.sim.entities import RobotCmd
w = make_world("mujoco-velocity", n_blue=2, n_yellow=2)
h = w.viewer()                       # janela passiva; w.step() sincroniza
while h.is_running():
    w.set_command("blue", 0, RobotCmd(vx=0.5, w=0.5))
    w.step()                         # 1/60 s
w.close()
```

`w.model` / `w.data` são o `MjModel`/`MjData` vivos (ex.: `mujoco.viewer.launch(w.model, w.data)` para o viewer interativo
com pausa). Os XML de `models/mjcf/` abrem direto em `python -m mujoco.viewer --mjcf models/mjcf/ssl_route_b.xml`
(sem controle: os robôs ficam parados).
