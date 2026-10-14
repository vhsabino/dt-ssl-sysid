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
| CLI | `src/dtssl/physics/cli.py` | `register(subparsers)` descoberto por `dtssl.cli`: `dtssl mjcf [--route a|b|both] [--out DIR] [--field divB|divA|FILE] [--n-blue N] [--n-yellow N] [--n-rollers N] [--no-boundary]` escreve `ssl_route_<r>.xml` + `ssl_route_<r>.md` (`--field divA`, desde 07/10/2026: campo da Divisão A de `config/field_divA.json` via `dtssl.config.load_field_preset`, 11 robôs por time na rota a sem `--n-blue/--n-yellow`, arquivos `ssl_route_<r>_divA.*`; também no `--view`); `dtssl mjcf --route a --view [--demo] [--seconds S]` abre o *viewer* passivo num `MuJoCoWorld` em tempo real. Também `python -m dtssl.physics.cli ...`. |
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
- Malhas do CAD só como **visual** (`visual="cad"`, ver seção abaixo): a colisão continua nas primitivas (prisma em D,
  cilindros, elipsoides); a física é bit-a-bit igual com e sem as malhas (teste).
- O viewer (`mujoco.viewer.launch_passive`) precisa de display/GL; não é testado no CI.

## Malhas do CAD (C5, 08/09/2026; refeito em 07/10/2026)

Histórico: a primeira versão exportava só o chassi e a roda de `usd/` (`tools/usd_to_mjcf_meshes.py`, `fast_simplification`),
em cinza único, e o chute e o dribbler entraram em 06/10 como malhas fixas tesseladas do Inventor
(`tools/inventor_export_mechanisms.m`). Em 07/10 as quatro malhas passaram a sair de uma única ferramenta, com as
cores do CAD, e as duas anteriores foram retiradas (cópias em `_to_delete\superseded_20261007\tools\`; `usd/` segue no
repositório só como arquivo de origem antigo).

### Exportação (Inventor, COM) e registro

`tools/inventor_export_cad.m` (MATLAB controlando o Inventor 2026 pela API COM, Windows) abre a montagem principal
`ssl-mechanics\v2025\inventor\robot_v2025_v3.iam` (ou reutiliza a instância aberta), percorre a árvore de ocorrências
uma vez, tessela cada corpo folha visível com `SurfaceBodies(i).CalculateFacets` (tolerância de corda 0,1 mm; os
*proxies* já vêm no frame da montagem principal) e escreve quatro malhas no frame de corpo do MJCF
(p' = R_z(+90°)·(p − [0 0 24,15 mm]) / 1000: x' = −y, y' = x, origem z no plano dos eixos das rodas, logo os geoms
ficam em `pos = (0, 0, wheel.r)`), cada uma com o par `_lod` para a GUI, escrito por `tools/cad_lod.m` (só as peças
vistas de fora, decimação `reducepatch` **por peça** com o orçamento de faces repartido pela área visível, para as
cores sobreviverem; ver "LOD para as vistas 3D" abaixo):

| Malha | O que entra | Peças | Faces (cheia / LOD) | Cores |
|---|---|---|---|---|
| `ssl_chassis.obj` | tudo o que não é mecanismo, roda, fixador (DIN/ISO), decalque ou peça SMD menor que 4 mm (`SkipPattern`, `MinPartMm`) | 218 (554 omitidas); 209 na LOD | 60 188 / 11 855 | 13 |
| `ssl_wheel.obj` | uma roda, `Direct_Transmission_new:1/Wheel_v2025_new:1` (`WheelPath`), no frame da roda: eixo em +x (saída), plano médio dos roletes em x = 0; as outras três ficam fora do chassi | 82; 75 na LOD | 8 088 / 4 968 | 5 |
| `ssl_kicker.obj` | `kicker_assembly_5mm:1` (chute reto + chip), frame do chassi | 12; 12 na LOD | 4 990 / 1 490 | 3 |
| `ssl_dribbler.obj` | `Dribbler_Robocup2025v3:1` (barra, motor, engrenagens, placas laterais, suporte do chip, PCBs IR) | 32; 30 na LOD | 14 862 / 3 486 | 9 |

Cores: cada folha recebe a cor base (difusa) da sua própria aparência, `ComponentOccurrence.Appearance` (aparência da
peça ou *override* da ocorrência), lida do *asset* pelas chaves do esquema (`generic_diffuse`, `plasticvinyl_color`,
`metal_color`, `wallpaint_color`, ...; cinza 191 quando não há). É o que o viewport sombreado do Inventor mostra:
um *override* numa submontagem não se propaga (a submontagem da tampa tem *override* "green" e é desenhada preta),
texturas são ignoradas e decalques são imagens sobre faces, não aparências. Por isso a tampa (`Capa_2025_V3`), que
no CAD é envolvida por um decalque preto com os patrocinadores, recebe preto por nome (`ColourOverrides`); a barra
`Dribblerschnecke` ("Gummi - schwarz", textura) fica no cinza claro base, igual ao viewport. As PCBs (quatro placas de
motor, placa principal e placa do processador) têm a aparência `BoardColor`, um creme claro (247, 249, 209) que nas
vistas 3D parecia um verde desbotado; `AppearanceOverrides` (por nome de aparência, 09/10/2026) as pinta de verde musgo
(31, 77, 46), material `m_1f4d2e` "BoardColor (override)", mais escuro que o verde do campo (`FLOOR_RGBA`
0,13/0,47/0,20), como as placas de circuito costumam ser (aplicado nos arquivos sem reexportar: `usemtl`, linhas
`# part` e bloco do `.mtl` renomeados). Conferido contra o
render do viewport (`Camera.SaveAsBitmap`): tampa e chassi pretos, módulo do dribbler cinza/branco, cubos das rodas
pretos, roletes cinza, capacitor branco. As faces saem agrupadas por peça (`g <caminho>`) e por cor (`usemtl m_rrggbb`;
materiais em `ssl_<tag>.mtl`, `Kd` 0 a 1, compartilhado pelo `_lod`). O cabeçalho de cada OBJ guarda a proveniência
(montagem, alvo, tolerância), o plano do decalque do padrão de id (`# id plate z`, peças `Papier*`, omitidas),
os dados do eixo da roda (ângulo no CAD 60,000°, centro (39,8; 68,9) mm, raio externo 30,38 mm) e uma linha
`# part <caminho> | lo | hi | mtl | aparência` por peça (mm, frame MJCF). A exportação completa leva ~41 s com a
montagem aberta.

### LOD para as vistas 3D (`tools/cad_lod.m`, 09/10/2026)

Até 08/10 o exportador decimava cada peça da LOD pela mesma razão (`reducepatch` por peça, ~20 % das faces). Como
`reducepatch` mantém os vértices sobre a superfície, as cordas da tampa curva (`Capa_2025_V3`, 662 faces) e da placa
sob ela (`Gehäuse_Unterplatte`, quase branca, "Clear - Light") afundavam ~1 mm uma pela outra e pelas peças de baixo,
e a placa clara e as peças de alumínio apareciam como manchas brancas sobre os robôs pretos da vista 3D do campo (a
malha cheia, usada no modo HQ, não tem o defeito; renders de antes e depois em `_to_delete\gl_probe_closeup_shaded_lod.png`
e `_to_delete\gl_after_closeup_lod.png`). `tools/cad_lod.m` substitui essa etapa: lê o `ssl_<tag>.obj` cheio, renderiza
cada peça com uma cor chapada (sem iluminação, ortográfico, figura invisível, `print -RGBImage`) de 5 elevações × 12
azimutes (de cima, como a vista do campo, e de baixo, como a aba Robô), conta os pixels que cada peça mostra, descarta
as que ninguém vê (`MinPixels` 6) e reparte o orçamento de faces (`FaceTargets`, os mesmos do exportador) em proporção
à área visível, com piso de 24 faces por peça e 4 passadas de redistribuição. O cabeçalho do `_lod` mantém as
convenções do exportador (linhas `# part` das peças mantidas, na ordem dos grupos) e ganha uma linha `# interior`
com as peças deixadas de fora; `register_cad_meshes.py` a ignora na proveniência e grava `generator` com
"LOD by tools/cad_lod.m". Resultado: chassi 209 de 218 peças, 60 188 → 11 855 faces; roda 75 de 82, 8 088 → 4 968
(orçamento `wheel_lod` 5 000 desde 09/10 à tarde: com 1 200 faces os 20 roletes caíam no piso de 24 faces e viravam
cristais pontiagudos, a partir de ~3 000 ficam redondos; a roda é a malha mais repetida, 4 por robô, mas é desenhada de
um item só, ver `gui.md` "Polígonos das rodas"); chute 12 de 12, 4 990 → 1 490; dribbler 30 de 32, 14 862 → 3 486 (~12 s
por malha). Os pixels em que a peça da LOD
difere da peça da malha cheia caem de 1,89 M para 93 k nas 24 vistas de conferência (`_to_delete\lod_artefacts.m`),
e os que restam são peças pretas sobre peças pretas. `inventor_export_cad.m` chama `cad_lod` para o par `_lod` de
cada alvo; para refazer só a LOD: `addpath tools; cad_lod(); python tools/register_cad_meshes.py`. O teste
`test_assets_present_and_meta_consistent` passou a exigir `n_parts` da LOD ≤ da malha cheia, materiais contidos nos
da malha cheia e faces da LOD abaixo de 40 % das da malha cheia (70 % na roda).

`python tools/register_cad_meshes.py` (só numpy) lê os OBJ/MTL e grava `src/dtssl/physics/assets/meshes.json`:
por malha `file`, `mtl`, `n_parts`, `n_skipped`, `faces_source`, `faces`, `vertices`, `bbox`, `md5`, `source`,
`materials` (`m_rrggbb` → rgb 0 a 1 + nome da aparência); no chassi `z_top_above_axle` (bbox, 125,0 mm),
`z_cover_above_axle` (plano superior da tampa, 120,2 mm: maior plano horizontal voltado para cima ≥ 50 cm²) e
`z_id_plate_above_axle` (decalque do padrão, 119,25 mm); na roda `outer_radius`, `axle`, `cad_angle_deg`,
`cad_centre`; no chute e no dribbler as *features* derivadas das caixas das peças (barra do dribbler: eixo y,
centro (72,9; −0,25; 13,75) mm, raio 6,47 mm, 72 mm; placa do chip como caixa orientada por PCA, face frontal
inclinada 16° para trás; boca: faces internas das placas laterais y = −27,75 e +28,75 mm, fundo x = 59,1 mm, borda
frontal x = 79,9 mm; êmbolos e cabeças do chute; PCBs IR). `mjcf.cad_meta()` é o único leitor.

### No builder e na GUI

Um `<mesh>` do MuJoCo tem uma só cor, então `mjcf.split_obj` parte cada OBJ em memória em um sub-mesh por material
(`cad_submeshes()`, nomes de arquivo virtuais `ssl_<chave>__<material>.obj`; a barra do dribbler sai separada, rótulo
`bar`, para poder girar): 30 *assets* (13 + 5 + 3 + 9) e 45 geoms visuais por robô (13 do chassi, 4 × 5 das rodas,
3 do chute, 9 do dribbler), `contype=conaffinity=0`, `mass=0`, `group=1`, `rgba` do material; as primitivas vão para o
`group=3`. `mjcf.load_model(xml)` anexa os bytes (`MjModel.from_xml_string(xml, assets)`); `dtssl mjcf --out DIR
--visual cad` escreve os 30 OBJ e o `meshes.json` ao lado do XML. A física é a mesma nos dois modos (teste bit a
bit mantido: tamanhos compilados `ngeom + 45` por robô, `nmesh + 30`, massas e inércias iguais, trajetórias iguais).
Na GUI, `scene3d.parse_obj` recebe os materiais e devolve `colors` por face; `cad_meshes`/`mechanism_meshes` vêm
coloridas e `view3d`/`robot_view3d` desenham com `faceColors` (na aba Robot as rodas continuam tingidas pela
velocidade, agora sobre a cor do CAD, `wheel_face_colors`, re-upload da malha só quando o nível de tinta muda).

Placa de identificação: ela ficava em `wheel.r + z_top_above_axle` (154,5 mm acima do piso), o topo da bbox, que é
uma peça saliente sobre a tampa; as bolinhas pareciam flutuar 4 a 6 mm. Agora `mjcf.cad_plate_z()` usa o plano do
decalque do padrão no CAD (`z_id_plate_above_axle`, 148,7 mm acima do piso, dentro dos 150 mm da regra), com
recuo para a tampa e para a bbox quando a chave não existe; builder (`_robot_visuals`) e GUI (`RobotMeshes.build`)
usam o mesmo valor.

## Dribbler físico (`dribbler="bar"`, 07/10/2026)

`MuJoCoWorld(..., dribbler="bar")` / `build_world_xml(..., dribbler="bar")` / `dtssl mjcf --dribbler bar` constroem o
mecanismo do CAD em vez da mola virtual (`"spring"`, default, inalterado): a barra de borracha como cápsula
(r 6,47 mm, 72 mm) num corpo `<robô>_dribbler_bar` com dobradiça `<robô>_dribbler` (eixo y do corpo) acionada por um
`velocity` (laço de velocidade do BLDC; `ctrl` = rad/s da barra, 0 a `dribbler_rpm_max` do `robot_limits.json`,
6000 rpm, trem 18:26:18 = 1:1; torque limitado a `torque_max`), montado num corpo `<robô>_dribbler_module` com uma
junta prismática `<robô>_dribbler_slide` ao longo da direção barra → bola (45°), com mola e amortecedor (os
`AmortecedorCad` do CAD), dentro de uma **boca**: fundo da casca em D cortado na placa do chip, duas bochechas até a
borda frontal das placas laterais (x = 79,9 mm, 5 mm além da face em D) e a placa do chip como caixa orientada
(`mouth_fragment`, classe `mouth`, sem massa). Bits de contato: `BIT_MOUTH = 32`; a bola passa a colidir com
piso, paredes e boca (`BALL_CONAFF_MOUTH`) e deixa de tocar a casca em D (`ROBOT_CONAFF_MOUTH`), que segue colidindo
com robôs e paredes; a barra e a boca têm prioridade 2 (a bola mantém seus parâmetros identificados no piso).
Por robô: +2 corpos, +2 juntas, +5 geoms, +1 atuador, +3 malhas compartilhadas (fundo e bochechas); o módulo e a
barra tiram sua massa do inercial do chassi (massa total = `spec.mass`). `MuJoCoWorld.dribbler_state(team, id)`
devolve (velocidade da barra, posição do slide, barra tocando a bola); `_ball_actions` manda `ctrl` = rpm do
comando → rad/s; `has_ball` continua a regra geométrica do IR. Visual `cad`: a malha da barra é desenhada no corpo
que gira; as outras peças do módulo ficam fixas.

Princípio e números. Na pose do CAD a barra fica 2,96 mm longe de uma bola encostada na placa do chip (e a placa
impede a bola de chegar mais perto: uma barra fixa nessa pose nunca tocaria a bola no piso). O módulo descansa
então num batente `engage` = 8 mm além do contato (slide 0, mola relaxada; uma bola na placa empurra o módulo 8 mm
para trás, 0,3 N com `stiffness` = 37,5 N/m; a barra segue a bola até 8 mm à frente da placa). A barra gira a bola
para trás (taxa positiva em +y arrasta o topo da bola para o robô); o retro-giro faz o atrito do piso puxar a bola
para a boca e a barra a pressiona no piso. Como a barra está 45° atrás e acima da bola, sua normal empurra a bola
para a frente e só os atritos (barra e piso, `mu_slide` = 0,186 identificado) a seguram: em repouso a bola flutua
~6 mm à frente da placa, pressionada com ~0,25 N, girando a −92 rad/s (velocidade periférica da barra a 3000 rpm);
nada além de atrito a segura, então ela é perdida quando o robô freia, recua ou gira mais forte do que o atrito
permite (como nos robôs reais). Dois detalhes que fizeram diferença: a barra real é uma rosca
(`Dribblerschnecke`, duas hélices opostas que se encontram no centro) e centraliza a bola; um cilindro no MuJoCo
não faz isso, então o mundo aplica a força lateral `−helix·N·clip(y/helix_width)` na bola enquanto a barra a toca
(`helix` = 0,3 da normal, saturada a 5 mm de desvio); sem isso a bola escapa de lado em qualquer curva. E o
contato bola-placa precisa ser inelástico (`mouth_solref` (0,01; 1,0), atrito 0,2) e o da barra macio e
sobreamortecido (`solref` (0,02; 2,0)), senão a bola quica para fora na captura.

Envelope medido (`_to_delete\sweep_bar.py`, rota a, cenário com rampas: captura a v, frenagem a a, recuo a 0,3 m/s,
curva a 1,5 rad/s com 3a rad/s², passo lateral a 0,3 m/s, dribbler a 3000 rpm): a bola fica na boca em todas as
fases para capturas até 0,8 m/s com rampas de 1 m/s² e até 0,5 m/s com rampas de 3 m/s²; perde-se ao frear a
≥ 2 m/s² depois de capturas a ≥ 0,8 m/s e nas capturas a 1,2 m/s. Recepção de passe (robô parado): 1,0 m/s é
segurada; 1,5 e 2,0 m/s quicam 2 a 8 mm além do alcance da barra (o robô real avança); 3 m/s volta 7 cm. Degraus
de comando (sem rampa) de −0,5 m/s perdem a bola, como esperado. Rotas a e b e `visual="cad"` dão o mesmo
resultado (física idêntica).

Parâmetros sem fonte no repositório (`DribblerOptions`, marcados no docstring): `engage`, `travel_back`,
`stiffness`, `damping`, `module_mass`, `bar_mass`, `armature`, `torque_max`, `friction`, `mouth_*`, `helix`,
`helix_width`. O que depende da mecânica: a posição real de repouso do módulo em relação ao CAD (a folga de 3 mm
sugere que a montagem não está na pose de operação), curso e pré-carga dos amortecedores, dados do motor do
dribbler. Testes: `tests/test_physics_dribbler.py` (14: geometria da boca, XML nas duas rotas e nos dois visuais,
tamanhos compilados, captura + frenagem + recuo + curva + passo lateral segurando a bola com retro-giro, perda num
degrau forte, curva sem `helix` perde a bola, estado do mundo e default `spring` intacto).

## Como abrir o viewer

```bash
pip install -e ".[mujoco]"            # ou pip install mujoco
dtssl mjcf --route a --view --demo    # 6x6, robôs em círculos com dribbler ligado/desligado
dtssl mjcf --route b --n-blue 1 --n-yellow 0 --view --demo --seconds 20
dtssl mjcf --route b --view --demo --visual cad   # malhas do CAD (RobôCIn v2025) em vez das primitivas
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

## Backends no harness do artigo (07/09/2026)

`dtssl.sim.world_plant.WorldPlant` embrulha um `World` de um robô na interface `Plant` do harness
(`reset` → `set_robot_state` com pose + velocidade de corpo; `prime_delay` → `prime_robot_delay`; `step` →
`set_command` + `World.step`; bola estacionada a 40 m, paredes desligadas, watchdog em relógio de simulação).
`MuJoCoWorld.set_robot_state` na rota b também impõe as velocidades das rodas pela cinemática inversa (sem
escorregamento inicial). `dtssl replay --plant mujoco-velocity|mujoco-rollers|mujoco-rollers-delay` e
`dtssl analysis run backends_holdout` (10 eventos de hold-out, 265 janelas; 35 s no PC, Windows/Python 3.14, commit `fea0150`):

| h_ref = 0,4 s, bin translacional, mediana das janelas | e_pos (m) |
|---|---|
| `fopdt` (gêmeo do artigo) | 0,0388 |
| `mujoco-velocity` (rota a) | 0,0388 — \|Δ\| máx. 1,6 mm vs a planta analítica em 265 janelas |
| `mujoco-rollers` (rota b, sem sintonia, sem atraso) | 0,0729 |
| `mujoco-rollers-delay` (rota b + Td do θ oficial) | 0,0477 |
| `ideal` | 0,1005 |

Por evento (n = 10): o gêmeo vence a rota b em 10/10 (Wilcoxon p = 0,001, rank-biserial +1,00), a rota b com atraso
em 9/10 (p = 0,010, +0,82) e a ideal em 10/10; contra a rota a a diferença é ruído numérico (|Δ| mediano 0,0000 m).
Leitura: (i) o gêmeo embutido no MuJoCo é o gêmeo — contatos passam a existir sem custo de fidelidade; (ii) a
física "como sai da caixa" fica entre a ideal e o gêmeo (melhor que o rSim de 0,129 m do artigo, pior que o
gêmeo por 1,9×); (iii) só o atraso identificado fecha a maior parte desse gap (0,073 → 0,048 m), coerente com a
ablação do artigo (Td 43 % do ganho). Artefato: `results/backends_holdout_20260907_1515.md/.csv`.

## Atrito do piso como opção (14/10/2026, preparação do C3)

- `mjcf.world_root` / `build_world_xml` ganharam `floor_friction` (default 0,9, inalterado) e `MuJoCoWorld`
  o parâmetro de mesmo nome, guardado em `self.floor_friction` e passado em `build_xml`. Geoms de mesma
  prioridade combinam atrito pelo máximo: o contato roleta-piso da rota b vê
  `max(floor_friction, RouteBOptions.roller_friction)`; a bola (prioridade 1) mantém o seu. Com os defaults
  nada muda (teste `test_world_floor_friction_option_defaults_to_0_9`; o ponto untuned do
  `tuned_physics_baseline` reproduz `mujoco-rollers-delay` a 1e-9 m em
  `test_default_point_reproduces_the_untuned_route_b_with_delay`).
- Uso: a sintonia da rota b (C3) põe piso e roletes no mesmo `mu`, de modo que o atrito efetivo seja
  exatamente o parâmetro otimizado, sem mexer em prioridades (que alterariam a mistura de `solref`/`solimp`).
