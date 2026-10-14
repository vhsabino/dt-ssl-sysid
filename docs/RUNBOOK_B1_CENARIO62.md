# Runbook B1: cenário 6.2, gêmeo + GUI + DualSense no Windows, estratégia no WSL2

*Escrito em 14/10/2026 para o Victor rodar sozinho (30 a 60 min, com o DualSense ligado). Fecha o item B1 do
backlog: o modo "Debug totalmente controlável", em que o joystick pilota um robô e a estratégia do
ssl-unification comanda os outros, tudo passando pelo mesmo servidor ssl-simulation-protocol do gêmeo.
Script: `tools/demo/b1_scenario62.ps1`. Complementa o §6.2 de `claude/roteiro-proximos-passos.md` e o
`docs/RUNBOOK_VIDEOS_D5_20260916.md`.*

## 0. Por que o cenário precisa de rede

O multicast da visão (224.5.23.2:10006) não atravessa o NAT do WSL2. Então a GUI, no modo Debug com
`--publish`, manda a visão também por unicast ao IP do WSL, e a estratégia manda os `RobotControl` para o IP do
Windows visto do WSL (o gateway), porta 10302 (yellow). Os dois IPs mudam a cada boot do Windows: o `prepare`
lê os dois e regrava a config. Alternativa sem IPs: `networkingMode=mirrored` em `%USERPROFILE%\.wslconfig`
(Windows 11 22H2+); o script detecta e cai no loopback do cenário 6.1.

## 1. Uma vez só (PowerShell como administrador)

```powershell
cd C:\Users\victo\Documents\digitaltwin
powershell -ExecutionPolicy Bypass -File tools\demo\b1_scenario62.ps1 firewall
```

Cria a regra de entrada UDP 10300 a 10302 ("dtssl ssl-sim-protocol"). Sem ela a estratégia não alcança o
servidor de controle do gêmeo e os robôs da estratégia ficam parados.

## 2. A cada sessão

Terminal 1, PowerShell comum, raiz do repo:

```powershell
powershell -ExecutionPolicy Bypass -File tools\demo\b1_scenario62.ps1 prepare
```

Imprime os IPs de hoje, escreve `_to_delete\b1\bridge_wsl.json` (cópia de `config/bridge.json` com
`vision.unicast_targets = ["<IP do WSL>:10006"]`), confere a regra do firewall e imprime os dois comandos do
WSL já com os IPs certos. Em 14/10 eram WSL 172.28.58.53 e Windows 172.28.48.1.

Terminal 2, WSL (Ubuntu), copiando o que o `prepare` imprimiu:

```bash
cd /mnt/c/Users/victo/Documents/digitaltwin && source ~/.venvs/dtssl/bin/activate
python3 tools/ssl_unification/make_local_config.py --ssl-unification ~/ssl-unification --team yellow \
    --sim-ip <IP do Windows> --inet eth0 --n-robots 5
bash tools/ssl_unification/run_against_twin.sh --ssl-unification ~/ssl-unification --team yellow --no-serve
```

`--n-robots 5` deixa a estratégia com os ids 0 a 4 e o id 5 livre para o joystick; sem isso os dois mandam
comando para o mesmo robô. O `--no-serve` não sobe gêmeo no WSL: ele está no Windows. Deixe este terminal
aberto; a janela Qt do ssl-unification abre pelo WSLg.

Terminal 1 de novo, o gêmeo com a GUI:

```powershell
powershell -ExecutionPolicy Bypass -File tools\demo\b1_scenario62.ps1 gui
```

Equivale a `py -3 -m dtssl.gui --mode debug --team yellow --config _to_delete\b1\bridge_wsl.json --publish`.
Na GUI, selecione o robô yellow 5 (combo da aba Robot, ou as teclas `,` e `.`) e pilote com o DualSense.

Ordem que funciona: `prepare`, depois a estratégia no WSL, depois a GUI. Se a GUI subir antes, não faz mal:
a estratégia se conecta quando chegar (a GUI publica visão desde o início; o watchdog de 0,3 s só reseta o
comando de quem parou de mandar).

## 3. O que observar (e o que me mandar)

1. Na janela do ssl-unification: o campo aparece em até 1 s (pacote de geometria) e os robôs yellow 0 a 4
   com comportamento `Player` andam.
2. Na GUI do gêmeo: os mesmos robôs 0 a 4 se movendo na vista do campo (2D ou 3D) sem você tocar no controle;
   o id 5 obedece ao DualSense; a aba Robot mostra, no id 5, a telemetria do gêmeo reagindo ao comando.
3. Aba Log da GUI: sem exceções e sem resets de watchdog em série para os ids 0 a 4 (um reset isolado ao
   fechar a estratégia é normal).
4. Chutes e dribbler da estratégia aparecem (a bola sai do robô na vista do campo).

Me mande três linhas: robôs 0 a 4 andaram (sim/não); id 5 obedeceu ao joystick (sim/não); Log limpo
(sim/não, e a mensagem se houver). Se quiser gravar a sessão para o harness, rode em vez da GUI o servidor
puro com gravação (`py -3 -m dtssl.cli serve --config _to_delete\b1\bridge_wsl.json --record results/sessao_02
--record-team yellow`) e a estratégia no WSL; a GUI não grava.

## 4. Falhas comuns

- Robôs da estratégia parados e a janela do ssl-unification com o campo: falta a regra do firewall (§1) ou o
  `--sim-ip` está com o IP de um boot anterior; rode `prepare` de novo e regenere a config do WSL.
- Janela do ssl-unification sem campo: a visão não está chegando no WSL; confira o IP do WSL em
  `_to_delete\b1\bridge_wsl.json` contra `wsl.exe -e hostname -I`.
- Dois comandos no mesmo robô (o id 5 "briga" com você): a config do WSL foi gerada sem `--n-robots 5`.
- `make_local_config.py` avisando que `config/local` já existe para outro time: passe `--team` igual ao da GUI
  ou regenere.
- Sem DualSense reconhecido: `--joy-map dualsense-raw-windows` na linha do `gui` (edite o `$cmd` do script ou
  rode o comando equivalente à mão); teclado continua funcionando.
