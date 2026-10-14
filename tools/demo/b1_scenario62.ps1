# b1_scenario62.ps1 - B1 (scenario 6.2): twin + GUI + DualSense on Windows, the team's strategy in WSL2.
# Multicast does not cross the WSL2 NAT, so vision goes by unicast to the WSL IP and the strategy sends
# RobotControl to the Windows IP seen from WSL (the default gateway). Both IPs change at every boot:
# run `prepare` again after a reboot. With networkingMode=mirrored in %USERPROFILE%\.wslconfig both sides
# share 127.0.0.1 and the script falls back to the loopback set-up of scenario 6.1.
#
# Usage (PowerShell, any directory; the script finds the repo from its own location):
#   powershell -ExecutionPolicy Bypass -File tools\demo\b1_scenario62.ps1 prepare    # IPs, _to_delete\b1\bridge_wsl.json, firewall check, WSL commands
#   powershell -ExecutionPolicy Bypass -File tools\demo\b1_scenario62.ps1 firewall   # as administrator: inbound UDP 10300-10302
#   powershell -ExecutionPolicy Bypass -File tools\demo\b1_scenario62.ps1 gui        # GUI Debug + publish (joystick on id 5, strategy on 0..4)
#   powershell -ExecutionPolicy Bypass -File tools\demo\b1_scenario62.ps1 wsl        # print the two WSL commands with today's IPs
# Options: -Team blue|yellow (default yellow), -JoyId N (robot driven by the joystick, default 5; the strategy
# gets ids 0..JoyId-1 through --n-robots JoyId), -Python <exe> (default py -3).
# Nothing here deletes anything; the only file written is _to_delete\b1\bridge_wsl.json.
param(
    [ValidateSet("prepare", "firewall", "gui", "wsl")][string]$Step = "prepare",
    [ValidateSet("blue", "yellow")][string]$Team = "yellow",
    [int]$JoyId = 5,
    [string]$Python = "py -3"
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$cfgDir = Join-Path $repo "_to_delete\b1"
$cfgWsl = Join-Path $cfgDir "bridge_wsl.json"
$ruleName = "dtssl ssl-sim-protocol"
$repoWsl = "/mnt/c/Users/victo/Documents/digitaltwin"

function Info($msg) { Write-Host "[B1] $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[B1] $msg" -ForegroundColor Yellow }

function Get-Mirrored {
    $p = Join-Path $env:USERPROFILE ".wslconfig"
    if (-not (Test-Path $p)) { return $false }
    return [bool]((Get-Content $p -Raw) -match "networkingMode\s*=\s*mirrored")
}

function Get-WslIps {
    $ip = (& wsl.exe -e hostname -I 2>$null | Out-String).Trim().Split(" ")[0]
    $route = (& wsl.exe -e sh -c "ip -4 route show default" 2>$null | Out-String)
    $gw = if ($route -match "via\s+(\S+)") { $Matches[1] } else { "" }
    if (-not $ip -or -not $gw) { throw "could not read the WSL IPs (is the distro installed and running? try: wsl.exe -e hostname -I)" }
    return @{ wsl = $ip; windows = $gw }
}

function Get-RuleState {
    $r = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($null -eq $r) { return "missing" }
    if ($r.Enabled -eq "True") { return "present" } else { return "disabled" }
}

function Write-BridgeWsl($wslIp) {
    $cfg = Get-Content (Join-Path $repo "config\bridge.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $cfg.vision.unicast_targets = @("${wslIp}:10006")
    $cfg.vision.multicast_if = "127.0.0.1"
    New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
    $json = $cfg | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($cfgWsl, $json, (New-Object System.Text.UTF8Encoding($false)))
    Info "wrote $cfgWsl (vision.unicast_targets = [$wslIp`:10006]; multicast stays on loopback)"
}

function Show-WslCommands($mirrored, $ips) {
    $n = $JoyId
    Write-Host ""
    Write-Host "--- WSL terminal (Ubuntu), in this order ---" -ForegroundColor Green
    Write-Host "cd $repoWsl && source ~/.venvs/dtssl/bin/activate"
    if ($mirrored) {
        Write-Host "python3 tools/ssl_unification/make_local_config.py --ssl-unification ~/ssl-unification --team $Team --sim-ip 127.0.0.1 --inet lo --n-robots $n"
    } else {
        Write-Host "python3 tools/ssl_unification/make_local_config.py --ssl-unification ~/ssl-unification --team $Team --sim-ip $($ips.windows) --inet eth0 --n-robots $n"
    }
    Write-Host "bash tools/ssl_unification/run_against_twin.sh --ssl-unification ~/ssl-unification --team $Team --no-serve"
    Write-Host "--- (the strategy drives ids 0..$($n-1); id $n is yours on the joystick) ---" -ForegroundColor Green
    Write-Host ""
}

switch ($Step) {
    "prepare" {
        $mirrored = Get-Mirrored
        if ($mirrored) {
            Info "networkingMode=mirrored found in .wslconfig: loopback set-up (no unicast, no firewall rule needed)"
            Info "GUI config: config\bridge.json as it is"
            Show-WslCommands $true $null
            break
        }
        $ips = Get-WslIps
        Info "WSL IP $($ips.wsl); Windows IP seen from WSL $($ips.windows) (NAT; both change at every boot)"
        Write-BridgeWsl $ips.wsl
        $state = Get-RuleState
        switch ($state) {
            "present" { Info "firewall rule '$ruleName' present and enabled" }
            "disabled" { Warn "firewall rule '$ruleName' exists but is disabled: Enable-NetFirewallRule -DisplayName '$ruleName' (as administrator)" }
            default { Warn "firewall rule missing: run as administrator  powershell -ExecutionPolicy Bypass -File tools\demo\b1_scenario62.ps1 firewall" }
        }
        Show-WslCommands $false $ips
        Info "then, here:  powershell -ExecutionPolicy Bypass -File tools\demo\b1_scenario62.ps1 gui"
    }
    "firewall" {
        $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if (-not $admin) { throw "run this step from a PowerShell opened as administrator" }
        if ((Get-RuleState) -eq "missing") {
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol UDP -LocalPort 10300-10302 -Action Allow | Out-Null
            Info "rule '$ruleName' created (inbound UDP 10300-10302)"
        } else {
            Enable-NetFirewallRule -DisplayName $ruleName
            Info "rule '$ruleName' already existed; enabled"
        }
    }
    "gui" {
        $mirrored = Get-Mirrored
        $cfgArg = if ($mirrored) { "config\bridge.json" } elseif (Test-Path $cfgWsl) { $cfgWsl } else { throw "run `prepare` first ($cfgWsl missing)" }
        $cmd = "$Python -m dtssl.gui --mode debug --team $Team --config `"$cfgArg`" --publish"
        Info "select robot $Team $JoyId in the GUI (combo of the Robot tab or , and . keys) and drive it with the DualSense"
        Info "running: $cmd"
        Invoke-Expression $cmd
    }
    "wsl" {
        $mirrored = Get-Mirrored
        if ($mirrored) { Show-WslCommands $true $null } else { Show-WslCommands $false (Get-WslIps) }
    }
}
