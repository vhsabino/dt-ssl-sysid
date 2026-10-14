# Runbook D5: os dois vídeos que faltaram na demo de 11/09

*Escrito em 16/09/2026. Um único passo a passo, na ordem em que eu digito, para gravar os dois vídeos que a
orientadora pediu: (1) a estratégia do RobôCIn jogando contra o gêmeo como se ele fosse o grSim e (2) o
ER-Force rodando e avaliado pelo gêmeo. O que faltou no dia não foi o software: foi eu não ter o passo a passo
à mão. Cada vídeo agora é um script com subcomandos em `tools/demo/`, que confere os pré-requisitos antes de
subir qualquer coisa. Números citados: `results/CHANGELOG.md` (cenário 6.1 de 03/09; C2b de 10/09).*

## 0. Véspera (15 min, uma vez)

Terminal WSL (Ubuntu), sempre a partir da raiz do repo vista do Linux:

```bash
cd /mnt/c/Users/victo/Documents/digitaltwin
tools/demo/video1_dropin.sh check         # venv, binário da estratégia, config do time yellow, WSLg, portas
tools/demo/video2_erforce.sh check        # venv, simulator-cli, endpoint erforce, portas
```

Os dois têm de terminar em "tudo pronto"/"ok". Se um `check` falhar, a mensagem diz o comando que resolve.
Depois ensaie uma vez cada vídeo inteiro (seções 2 e 3), sem gravar, e só então grave. Gravação: OBS Studio,
captura de tela inteira (a janela Qt do WSLg aparece como janela normal do Windows); sem o OBS, `Win+G`
(Xbox Game Bar) grava a janela em foco, então grave o terminal e a janela Qt lado a lado numa tela só.
Confira o vídeo antes de ir.

## 1. Layout da tela para os dois vídeos

Dois terminais WSL lado a lado (Windows Terminal, `wsl` em cada aba, ou duas janelas) e espaço para a janela
Qt da estratégia. No terminal da esquerda rodam os comandos; no da direita, o `watch` do log. Fonte grande
(Ctrl e + no Windows Terminal) para o log ser legível no vídeo.

## 2. Vídeo 1 (3 min): drop-in do ssl-unification

Terminal esquerdo:

```bash
cd /mnt/c/Users/victo/Documents/digitaltwin
tools/demo/video1_dropin.sh run
```

O script confere tudo de novo, sobe o `dtssl serve` (FOPDT com o θ oficial, `config/bridge.json`)
em background e abre o `ssl-unification -running`. A janela Qt aparece em até 2 s; o campo aparece assim que
chega o pacote de geometria (menos de 1 s) e os seis robôs yellow com comportamento `Player` começam a andar.

Terminal direito, assim que a janela abrir:

```bash
tools/demo/video1_dropin.sh watch
```

É o `tail -f /tmp/dtssl_serve.log`. A cada 5 s aparece uma linha `[stats]`; o que eu mostro e digo:

- `hz=60.0/60 late=0`: o gêmeo mantém 60 Hz de tempo real sem tick atrasado;
- `yellow=` crescendo cerca de 4 pacotes por quadro: a estratégia está comandando os seis robôs;
- `watchdog=0`: nenhum robô ficou sem comando;
- `kicks=` crescendo: a estratégia chuta a bola no gêmeo.

Fala: "O ssl-unification não sabe que não está no grSim: mesma visão, mesmas portas, mesmo protocolo. Nenhuma
linha de C++ foi tocada; só o `config/local`." Referência de 03/09: 185 s a 60 Hz, watchdog 0, 45 chutes.
Deixe jogar uns 60 s, mostre a janela e o log juntos, feche a janela da estratégia (o script encerra o gêmeo e
imprime a linha final de `[stats]`).

### 2.1 Variante com o gêmeo numa janela (18/09)

O `run` sobe o gêmeo como `dtssl serve`, que não tem janela: o que se vê do gêmeo são os robôs na janela Qt da
estratégia e o log. Para o gêmeo aparecer numa janela própria, mostrando o que a estratégia faz nele (campo 2D com
os 12 robôs e a bola, plots de comando e estado do robô selecionado, aba 3D com o CAD, barra de status com Hz e
pacotes), o gêmeo tem de ser a GUI no modo `bridge`, que roda o mesmo servidor por dentro:

```bash
tools/demo/video1_dropin.sh gui        # no lugar do run: abre dtssl gui --mode bridge (janela via WSLg) e depois a estratégia
```

Uma vez, antes: o venv do WSL precisa do extra `[gui]` (`~/.venvs/dtssl/bin/pip install -e "/mnt/c/Users/victo/Documents/digitaltwin[gui]"`,
2 a 5 min); se a janela não abrir por falta de libs do Qt no Ubuntu, `sudo apt install -y libxcb-cursor0 libxkbcommon-x11-0 libxcb-xinerama0 libgl1 libegl1 libdbus-1-3`.
O próprio `gui` diz isso quando falta algo. Ficam duas janelas Qt lado a lado: a da estratégia (o que ela decide) e a do
gêmeo (o que acontece com os robôs). A aba 3D no WSLg usa renderização por software; se pesar, fique na aba 2D. Sem o
terminal da direita nesse modo: a barra de status da GUI mostra Hz e pacotes.

Aba **Robot** (19/09, pedido da orientadora): o robô selecionado em destaque com as rodas pela cinemática inversa,
comando × resultante, watchdog, sensor de bola e o bloco de hardware (bateria e capacitor de um modelo ilustrativo, rotulado;
valores reais quando `GUI_ARGS=--telemetry` e há robôs reais reportando pelo rádio). Desde 24/09 o robô aparece em **3D**
(CAD, rodas girando e coloridas pela velocidade, bola no dribbler, setas de comando e resultante): arraste com o botão
esquerdo para girar em qualquer eixo, como uma peça no CAD; roda do mouse aproxima; duplo clique ou `R` reinicia;
`Auto` põe o robô a girar sozinho (bom para o vídeo); `frente`/`topo`/`baixo` são os presets. Escolha o robô no combo da
própria aba (os dois times) ou com `<`/`>`, além de `,`/`.` e do clique no campo 2D. A troca `3D`/`2D` no cabeçalho volta à
vista de cima; sem GL (ou com `GUI_ARGS=--no-3d`) a aba fica no 2D sozinha. Se o 3D pesar no WSLg, desligue `HQ`.

Aba 3D no WSLg (visto em 18/09): o log encheu de `OpenGL.error.Error: Attempt to retrieve context when no valid context`
a cada repintura da aba 3D, e a aba ficou vazia (o resto da GUI e o servidor seguem, o pyqtgraph engole a exceção). Causa:
o Qt criou o contexto GL por um caminho (EGL ou GLX) e o PyOpenGL, que desenha as malhas, procurou o contexto pelo outro
(no Linux ele assume GLX). Os dois precisam falar com o mesmo GL. O `gui` agora testa os dois pares antes de abrir a
janela (`tools/demo/video1_dropin.sh gl-check` mostra o diagnóstico) e exporta o que funciona (`QT_XCB_GL_INTEGRATION=xcb_egl`
com `PYOPENGL_PLATFORM=egl`, ou `xcb_glx` sem `PYOPENGL_PLATFORM`); se nenhum funcionar, abre sem a aba 3D. Para forçar:
`GL_PAIR=glx tools/demo/video1_dropin.sh gui`; para desligar a aba 3D no vídeo: `GUI_ARGS=--no-3d tools/demo/video1_dropin.sh gui`.

Plano B (se a janela Qt não aparecer): `echo $DISPLAY` vazio significa WSLg fora do ar; no PowerShell
`wsl --shutdown`, abra o Ubuntu de novo e repita. Se não voltar, o log do gêmeo continua provando a
integração (`yellow=` crescendo, `kicks=` crescendo) e o vídeo passa a ser só o terminal, com o log de 03/09
(`claude/backlog-decisao-2026-09.md` §0) como número de referência.

## 3. Vídeo 2 (3 min): ER-Force rodando e avaliado pelo gêmeo

O `simulator-cli` do ER-Force não tem janela: o que aparece é o terminal, a figura do replay e, se eu quiser
o uso da liga, a estratégia jogando dentro dele. Terminal esquerdo, um subcomando por vez:

```bash
cd /mnt/c/Users/victo/Documents/digitaltwin
tools/demo/video2_erforce.sh start      # sobe o simulator-cli -g 2020B --realism None; status com as portas 10020/10300-10302
tools/demo/video2_erforce.sh probe      # teleporte + 1 janela de 1 s: "window_ok": true, latência, tau0, moved_m
tools/demo/video2_erforce.sh replay     # side_to_side_01_05 replayado no ER-Force pelo harness: tabela e_pos por horizonte + PNG
tools/demo/video2_erforce.sh strategy   # opcional: o ssl-unification jogando DENTRO do ER-Force (janela Qt); feche para voltar
tools/demo/video2_erforce.sh stop       # derruba o simulador e restaura a config/local do gêmeo
```

O que eu mostro e digo em cada passo:

- `start`: "Este é o simulador do ER-Force, Bullet, como sai da caixa, sem sintonia ao nosso robô."
- `probe`: "O harness fala com ele pelo mesmo protocolo: teleporta, manda comandos a 60 Hz, lê a visão e
  alinha. `window_ok: true` é o instrumento válido."
- `replay`: "Um evento real de competição replayado dentro do ER-Force, janela a janela, com a mesma métrica
  do artigo." A tabela mostra `e_pos` mediano por horizonte; a figura abre no Windows. Para a comparação de
  bolso: no hold-out inteiro (C2b, 10/09) o ER-Force deu 0,088 m em 0,4 s, com o atraso identificado 0,056,
  o grSim 0,239, o gêmeo 0,039. O replay no ER-Force leva cerca de um minuto (é em tempo real).
- `strategy` (se der tempo): "E o uso da liga: a mesma estratégia, agora contra a física do ER-Force." A
  janela Qt mostra os robôs jogando; o `config/local` é regenerado para a visão do ER-Force (porta 10020 na
  interface da rota default do WSL) e restaurado no `stop`. Este passo não foi ensaiado antes de 16/09:
  ensaiar na véspera; se a estratégia não vir a visão, pular e dizer que o ponto do vídeo é o harness.
- `stop`: encerra e restaura.

Plano B: `results/protocol_holdout_20260910_0211.md` aberto no VS Code (tabela por evento e diagnóstico do
replay), com a fala acima. Se o `probe` falhar com "no vision", o simulador está mandando a visão por outra
interface: `tools/external_sims/simctl.sh erforce log` e `config/external_sims.json` (`multicast_if 0.0.0.0`).

## 4. Falhas comuns e o que fazer

- "porta 10300 em uso": outro simulador ou um `dtssl serve` antigo de pé. `tools/external_sims/simctl.sh grsim stop`,
  `simctl.sh erforce stop`, `pkill -f 'dtssl.cli serve'`.
- "dtssl não importa": o venv do WSL não está ativo. Os scripts ativam `~/.venvs/dtssl` sozinhos; se ele não
  existir, `python3 -m venv ~/.venvs/dtssl && ~/.venvs/dtssl/bin/pip install -e "/mnt/c/Users/victo/Documents/digitaltwin[dev]"`.
- config/local do time errado ou do ER-Force: o `check` do vídeo 1 compara com a config do gêmeo e regenera
  (guarda a anterior em `/tmp/video1_config_backup_*.json`).
- Log com `yellow=0` e `kicks=0` por vários `[stats]`: o gêmeo está de pé mas a estratégia não está mandando comando
  (janela aberta pausada, ou config/local de outro time); fechar e rodar de novo resolve (foi o que aconteceu em 18/09:
  na segunda subida, `yellow=1066 kicks=1` em 5 s). `tail: file truncated` no `watch` é só o log sendo reaberto pelo novo `run`.
- Janela Qt sem campo: pacote de geometria não chegou; conferir no log do gêmeo se `vision=` cresce e se a
  config aponta para `224.5.23.2:10006` em `lo`.
- Nada aqui grava sessão nem escreve em `results/` (o replay do vídeo 2 escreve em `/tmp/demo_erforce`).
