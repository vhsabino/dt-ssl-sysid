# Demo para a orientadora: o gêmeo digital `dtssl` em 30 minutos

*Roteiro escrito em 11/09/2026. Tudo roda no PC (Windows + WSL2); nada aqui depende de rede. Tempo alvo:
25 min de demonstração + 5 min de perguntas. Complementa o resumo de 2 páginas
(`docs/RESUMO_ORIENTACAO_20260909.pdf`), que serve de "slide" de abertura e de fechamento.*

## Regra de ouro

Cada bloco tem um comando, uma frase para dizer e um plano B. Se algo falhar, não depure na frente dela:
passe para o plano B do bloco (sempre um arquivo já pronto em `results/` ou `docs/img/`). A ordem dos
blocos é a ordem de importância; se o tempo apertar, corte o bloco 4 (viewer MuJoCo) e encurte o bloco 3.

## Véspera: checklist (20 min, rode cada comando uma vez)

```powershell
cd C:\Users\victo\Documents\digitaltwin
git status --short | Select-String -NotMatch '^\?\?'        # vazio = árvore limpa (os PDFs da SLR são untracked, ok)
git log --oneline -14                                          # a linha do tempo que você vai mostrar
py -3 -m dtssl.cli info
py -3 -m dtssl.cli replay shoot_to_goal shoot_to_goal_12_01 --out _to_delete\demo
py -3 -m dtssl.gui --mode debug --team yellow                  # pad ligado ANTES; feche Steam/DS4Windows
py -3 -m dtssl.gui --mode replay --label shoot_to_goal --event shoot_to_goal_12_01   # só entra na demo se abrir bem aqui
py -3 -m dtssl.cli mjcf --route b --view --demo --visual cad   # viewer MuJoCo; se não abrir, o plano B é docs\img\mjcf_cad_preview.png
```

```bash
# WSL (Ubuntu): a estratégia contra o gêmeo, 30 s, e o grSim de pé
cd /mnt/c/Users/victo/Documents/digitaltwin && source ~/.venvs/dtssl/bin/activate
bash tools/ssl_unification/run_against_twin.sh --ssl-unification ~/ssl-unification --team yellow   # feche a janela Qt depois de ver os robôs andando
tools/external_sims/run_grsim.sh start && tools/external_sims/run_grsim.sh probe && tools/external_sims/run_grsim.sh stop
```

Deixe abertos antes da reunião: um PowerShell na raiz do repo (fonte 16 pt ou mais), um terminal WSL já com o
venv ativo, o PDF do resumo, e no VS Code os arquivos `results/backends_holdout_20260907_1515.md`,
`results/identifiability_insilico_mujoco-rollers-delay_v2_20260907_2044.md`,
`results/closed_loop_stats_20260907_2137.md` e `results/protocol_holdout_20260910_0211.md` (um por aba).
Tudo que a demo escreve vai para `_to_delete\demo` (ignorado pelo git): o repositório fica limpo.

## Bloco 0 (2 min): a tese em uma frase, com o PDF aberto na página 1

Dizer: "A tese é um gêmeo digital de fidelidade comportamental do robô SSL: uma planta de primeira ordem com
atraso por grau de liberdade, identificada dos logs de competição. Desde o artigo, transformei isso em um
pacote reproduzível, em um simulador que fala o protocolo da liga, e usei o gêmeo como instrumento para
testar as próprias hipóteses do artigo. Vou mostrar as três coisas nessa ordem."

## Bloco 1 (3 min): tudo reproduz com um comando

```powershell
py -3 -m dtssl.cli info                    # versão, raiz, dataset, backends disponíveis, extras instalados
git log --oneline -14                      # a sequência: refatoração, C2a, C1, C1b, B3, C4, C5, C6, D2, C2b
py -3 -m dtssl.cli analysis list           # um módulo por número do artigo (registro; requires = o que cada um precisa)
py -3 -m dtssl.cli replay shoot_to_goal shoot_to_goal_12_01 --out _to_delete\demo
```

Abra o PNG gerado em `_to_delete\demo` (trajetória real x gêmeo e `e_pos` por horizonte).

Dizer: "Cada número do artigo é `dtssl analysis run <nome>`; o artefato sai com carimbo de tempo, commit,
θ, dataset e seed no cabeçalho, e cada execução tem uma linha no `results/CHANGELOG.md` (50 entradas até hoje).
Este replay é o harness do artigo em um evento do hold-out: o gêmeo erra cerca de 4 cm em 0,4 s onde a
cinemática ideal erra 10."

Plano B: se o replay falhar, mostre `results/backends_holdout_20260907_1515.md` (a coluna `fopdt`).

## Bloco 2 (5 min): o gêmeo ao vivo, com o DualSense

```powershell
py -3 -m dtssl.gui --mode debug --team yellow
```

1. Dirija um robô (stick esquerdo translação, stick direito rotação, R2 turbo). Aponte nos gráficos à direita
   o comando (linha) e a resposta (linha atrasada e suavizada): "isto é o τ e o Td identificados, em tempo real".
2. Painel de θ: mude `Td_vx` para 0,20 e `Apply`; dirija de novo e mostre o atraso maior. Volte ao preset
   `oficial`. Dizer: "o mesmo θ do artigo, editável ao vivo; nada disso grava no `config/`".
3. Aba **3D (CAD)**: `Follow` ligado, dirija; mostre as rodas girando pela cinemática inversa. Dizer: "as
   malhas são o CAD do RobôCIn v2025 exportado do USD; é só apresentação, a física é a mesma bit a bit."
4. Se abriu bem na véspera, feche e abra o modo Replay:
   `py -3 -m dtssl.gui --mode replay --label shoot_to_goal --event shoot_to_goal_12_01` (Espaço = play).
   Dizer: "o harness visual: o gêmeo dirigido pelos comandos gravados, contra a verdade da visão."

Plano B: sem pad, teclado (`W/S A/D` translação, `Q/E` rotação, `,`/`.` troca de robô). Se a GUI não abrir,
mostre `docs/img/gui_3d_tab.png`.

## Bloco 3 (4 min): o gêmeo como grSim para a estratégia do time (WSL)

```bash
bash tools/ssl_unification/run_against_twin.sh --ssl-unification ~/ssl-unification --team yellow
```

Deixe a janela Qt do ssl-unification aparecer (WSLg) com os robôs amarelos jogando por 30 a 60 s. Num segundo
terminal WSL: `tail -3 /tmp/dtssl_serve.log` (mostre `hz=60.0`, `watchdog=0`, `kicks` crescendo). Feche a
estratégia; o script derruba o gêmeo.

Dizer: "O `dtssl serve` implementa o ssl-simulation-protocol: visão multicast a 60 Hz, controle nas portas do
grSim, teleporte. A estratégia do RobôCIn roda sem uma linha de C++ alterada, só com um `config/local`
gerado. Na validação de 03/09 foram 185 s a 60 Hz, sem nenhum estouro de watchdog e 45 chutes. Foi assim que
gravei a primeira sessão do gêmeo (B3) e a comparei com os logs de competição (C4)."

Plano B: `py -3 -m dtssl.cli serve --duration 5` no Windows + `py -3 -m dtssl.cli fake-strategy --team yellow --target 1 0.5 --duration 3`
em outro PowerShell (cliente de fumaça que emula a estratégia).

## Bloco 4 (3 min, cortável): a camada física (MuJoCo) com o CAD

```powershell
py -3 -m dtssl.cli mjcf --route b --view --demo --visual cad
```

Dizer: "Duas rotas no MuJoCo: na rota (a) a planta comportamental dirige o chassi dentro do engine, que só
cuida de contato com bola, robôs e paredes; o embedding reproduz o gêmeo (diferença máxima 1,6 mm no
hold-out). Na rota (b) são rodas omnidirecionais com roletes livres, sem sintonia: 7,3 cm em 0,4 s contra
3,9 cm do gêmeo; só o atraso identificado já fecha metade desse gap (4,8 cm)."

Plano B: `docs\img\mjcf_cad_preview.png` e a tabela de `results/backends_holdout_20260907_1515.md`.

## Bloco 5 (6 min): a ciência que a infraestrutura habilitou (abas do VS Code)

Uma frase por artefato; não leia tabelas inteiras, aponte a linha de `h = 0,40 s`.

1. `results/backends_holdout_20260907_1515.md` (C2a). "Mesmas 265 janelas do artigo: gêmeo 0,039 m,
   embedding na rota (a) 0,039 m, rota (b) 0,073 m, rota (b) com o atraso identificado 0,048 m, ideal 0,101 m.
   O gêmeo vence a física sem sintonia em 10 de 10 eventos."
2. `results/identifiability_insilico_mujoco-rollers-delay_v2_20260907_2044.md` (C1 e C1b). "Identificabilidade
   in silico com θ conhecido. Com o gerador linear, todo DOF é recuperado sempre que há excitação, inclusive ω
   em malha fechada: a zona morta e o ruído não explicam o K de 1,3 do artigo. Com o gerador físico (rota b,
   que tem acoplamento translação-guinada), o K de ω em malha fechada sai 1,16 idealizado e 1,27 realista,
   contra 0,99 no controle sem translação e 0,996 na rotação pura. O viés é acoplamento sob realimentação,
   não mascaramento pela zona morta. Isso reescreve o parágrafo do mecanismo."
3. `results/closed_loop_stats_20260907_2137.md` e o PNG ao lado (C4). "A estratégia jogando sobre o gêmeo
   emite comandos com a mesma estatística dos logs de competição de jogo: 5 de 5 critérios contra
   `shoot_to_goal`; contra o pool inteiro falha 3, porque 28 dos 46 eventos são manobras roteirizadas a
   1 m/s constante. E o '94 % dos comandos sob a zona morta' do artigo é estatística de linhas cruas; na grade
   de 60 Hz é 90 % no pool e 74 % em jogo."
4. `results/protocol_holdout_20260910_0211.md` (C2b, rodado ontem à noite). "Os dois simuladores da liga,
   grSim e ER-Force, dentro do mesmo harness, via protocolo, como saem da caixa: em 0,4 s o ER-Force erra
   8,8 cm, com o atraso identificado 5,6 cm; o grSim erra 24 cm porque ignora a velocidade inicial no teleporte,
   todo trecho parte do repouso, e isso explica só um terço do gap, o resto é a atuação dele; o gêmeo, 3,9 cm.
   Pré-registrado: H1 corroborada nos dois, H3 corroborada (mesmo partindo do repouso o FOPDT vence a física
   do grSim), H2 parcial (o atraso identificado reduz o erro do ER-Force em 45 % e o do grSim em nada). A
   crítica 'compararam com simulador não sintonizado' está respondida com as duas físicas da liga."
   Opcional, se sobrar 1 min, ao vivo no WSL: `tools/external_sims/run_grsim.sh start && tools/external_sims/run_grsim.sh probe && tools/external_sims/run_grsim.sh stop`
   ("o harness teleporta o robô no grSim, manda 60 comandos e lê a visão de volta").

## Bloco 6 (2 min): rigor

Dizer: "Seis pré-registros em `docs/PREREGISTRO_*.md`, critérios fixados antes do resultado;
dois deles falharam pela referência escolhida e ficaram documentados como falharam (C1b v1 e C4 contra o
pool). 377 testes automatizados, goldens que comparam a planta Python com o MATLAB do artigo a 1e-15, e uma
correção de geometria já registrada. Nada do artigo mudou de número; mudou a leitura do mecanismo."

## Bloco 7 (5 min): próximos passos e o que decidir com ela

Abra a página 2 do PDF. Próximos passos, na ordem que proponho:

1. Fechar a branch: `_to_delete` revisada, merge de `refactor/dtssl` em `main`, tag `v1.0.0`, push, DVC dos
   dados de sessão (B2). Meio dia.
2. Texto do artigo (D1): parágrafo do mecanismo do viés de ω (acoplamento sob realimentação), correção do
   "94 %", tabela com ER-Force/grSim no harness no lugar ou ao lado do rSim. Depende da decisão 1 abaixo.
3. Pacote de reprodução com DOI (D3): `dtssl release` anonimizado + Zenodo. Meio dia, depende da decisão 4.
4. Calibrar a rota (b) como "gêmeo físico sintonizado" (C3), 1 a 2 semanas. Só se ela achar que C2b não basta.
5. SLR: sprint 2 (skim) em paralelo até 02/10; RQ3 (gêmeo + RL, transferência) entra depois, sobre o híbrido
   MuJoCo.

Perguntas para ela (anote as respostas):

1. Artigo SBR/LARS: o parágrafo "gêmeo como instrumento" e a reformulação do mecanismo do viés de ω entram
   na versão final, ou viram um artigo de ferramenta separado (RoboCup Symposium ou extensão JINT)? Qual
   venue e qual prazo?
2. Baselines: ER-Force e grSim no próprio harness substituem ou complementam o rSim no artigo? Vale investir
   1 a 2 semanas na calibração da rota (b) (C3), ou o C2b já responde à crítica do simulador não sintonizado?
3. Qualificação: escopo (instrumento + identificabilidade por regime + fidelidade comportamental versus
   física), data alvo e composição da banca.
4. RQ3: quando começar o gêmeo + RL, e em que plataforma (MuJoCo/MJX sobre o híbrido). A SLR deve ser
   fechada antes?
5. Robô real: uma coleta dedicada de excitação no laboratório é viável neste semestre? O dataset de rotação
   pura tem só 6 eventos, e o atraso identificado nunca foi validado no robô com comandos gravados.
6. Publicação do pacote: liberar o `dtssl` anonimizado com DOI junto com o artigo? Licença, autoria e
   agradecimentos ao RobôCIn.
7. Ela quer acesso ao repositório (`vhsabino/dt-ssl-sysid`, branch `refactor/dtssl`) e ao PDF de 2 páginas?

## Números de bolso (todos de `results/CHANGELOG.md`)

| O quê | Número | Fonte |
|---|---|---|
| Headline do artigo, `e_pos` em 0,4 s, 10/10 eventos | gêmeo 0,039 m; ideal 0,101; rSim 0,129 | artigo / CHANGELOG |
| Ablação (Shapley) | τ 55 %, Td 43 %, K 2 % | artigo |
| θ oficial | vx K 1,119 τ 0,072 Td 0,069; vy 1,052 / 0,127 / 0,057; ω 1,002 / 0,083 / 0,089 | `config/twin_params.json` |
| Backends no harness (C2a) | fopdt 0,0388 = rota (a) 0,0388; rota (b) 0,0729; (b)+atraso 0,0477; ideal 0,1005 | `backends_holdout_20260907_1515` |
| Identificabilidade (C1) | 72 células; todo DOF recuperado com excitação; ω em malha fechada K 0,996 (linear) | `identifiability_insilico_20260907_1552` |
| Mecanismo do viés (C1b) | K_ω malha fechada 1,16 (idealizado) / 1,27 (realista) vs 0,99 controle vs 0,996 rotação pura | `..._mujoco-rollers-delay_v2_20260907_2044` |
| Sessão gravada (B3) | 220 s, 6 robôs, 79 k linhas; round trip ao nível do mm | `session_report_sessao_01_20260907_2059` |
| Malha fechada x competição (C4) | 2/5 contra o pool; 5/5 contra `shoot_to_goal`; "94 %" = 90 % pool / 74 % jogo a 60 Hz | `closed_loop_stats_20260907_2137` |
| Simuladores da liga (C2b) | ER-Force 0,088 (+atraso 0,056); grSim 0,239 (+atraso 0,234); gêmeo 0,039; gêmeo parado 0,114 | `protocol_holdout_20260910_0211` |
| Drop-in (6.1) | 185 s a 60 Hz, watchdog 0, 45 chutes | log de 03/09 |
| GUI 3D | 12 robôs com CAD a 17 ms/quadro (Intel Iris Xe) | `docs/refactor_notes/gui.md` |
| Testes / pré-registros / CHANGELOG | 377 / 6 / 50 entradas | repo |

## O que não mostrar

Cenário 6.2 (GUI no Windows + estratégia no WSL: ainda não validado), `dtssl gate twin-vs-rsim` (precisa do
robosim), a pasta `_to_delete`, o `git status` sem filtro (dezenas de PDFs da SLR untracked), qualquer
artefato marcado "TESTE DE FUMACA".
