# run_lote2_apply_and_test.ps1 - aplica o patch da aba Robot (lote 2, 19/09) no repo, confere md5 e roda ruff + pytest.
# Uso (PowerShell, raiz do repo):  powershell -ExecutionPolicy Bypass -File _to_delete\_apply\run_lote2_apply_and_test.ps1
# Nao faz commit. Saida ASCII. Pre-requisito: os patches do lote 1 aplicados e commitados (docs/README.md e o runbook ja no repo).
$ErrorActionPreference = "Stop"
$repo = "C:\Users\victo\Documents\digitaltwin"
$apply = Join-Path $repo "_to_delete\_apply"
Set-Location $repo
function Md5($path) { (Get-FileHash -Algorithm MD5 -Path $path).Hash.ToLower() }
function ApplyPatch($name) {
    $tar = Join-Path $apply "$name.tar.gz"
    $lines = Get-Content (Join-Path $apply "${name}_md5.txt")
    $expectedTar = ($lines[0] -split '\s+')[0]
    $gotTar = Md5 $tar
    if ($gotTar -ne $expectedTar) { throw "$name : md5 do tarball difere (esperado $expectedTar, obtido $gotTar)" }
    Write-Host "[lote2] $name : tarball ok ($gotTar)"
    tar -xzf $tar -C $repo
    if ($LASTEXITCODE -ne 0) { throw "tar falhou em $name" }
    $bad = 0
    foreach ($l in $lines[1..($lines.Count - 1)]) {
        $parts = $l -split '\s+', 2
        $got = Md5 (Join-Path $repo $parts[1])
        if ($got -ne $parts[0]) { Write-Host "[lote2] MD5 DIFERE: $($parts[1])"; $bad++ } else { Write-Host "[lote2] ok  $($parts[1])" }
    }
    if ($bad -gt 0) { throw "$name : $bad arquivo(s) com md5 diferente" }
}
ApplyPatch "patch_robot_tab"

Write-Host "[lote2] ruff nos arquivos Python tocados"
py -3 -m ruff check src/dtssl/bridge/telemetry.py src/dtssl/bridge/proto/__init__.py src/dtssl/gui/robot_tab.py src/dtssl/gui/app.py src/dtssl/gui/cli.py tests/test_telemetry.py tests/test_gui_robot_tab.py tests/test_bridge_proto.py tests/test_gui_view3d.py
if ($LASTEXITCODE -ne 0) { throw "ruff acusou problemas" }

Write-Host "[lote2] pytest do bloco (telemetria, protos, aba Robot offscreen, janela 3D; ~30 s)"
$env:QT_QPA_PLATFORM = "offscreen"
py -3 -m pytest tests/test_telemetry.py tests/test_bridge_proto.py tests/test_gui_robot_tab.py tests/test_gui_view3d.py tests/test_gui_window.py -q
if ($LASTEXITCODE -ne 0) { throw "pytest do bloco falhou" }
Remove-Item Env:QT_QPA_PLATFORM

Write-Host "[lote2] pytest -m 'not requires_data' (suite curta, ~2 min)"
py -3 -m pytest -m "not requires_data" -q
if ($LASTEXITCODE -ne 0) { throw "suite curta falhou" }

Write-Host "[lote2] git status:"
git status --short
Write-Host "[lote2] pronto. Ver a aba:  py -3 -m dtssl.gui --mode debug --team yellow   (aba Robot; W/A/S/D move o robo selecionado)"
Write-Host "[lote2] commit sugerido:  git add -A src/dtssl config/telemetry.json tests docs README.md CLAUDE.md ; git commit -F _to_delete\_apply\commit_robot_tab.txt"
