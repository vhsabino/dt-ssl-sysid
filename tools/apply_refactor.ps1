<#
.SYNOPSIS
  Parte GIT da aplicação da refatoração dtssl (rodar no Windows, no PowerShell, dentro do repositório).
  A parte de arquivos (overlay + moves para _to_delete/) já foi aplicada pelo Claude pelo Cowork.

.USO
  cd C:\Users\victo\Documents\digitaltwin
  powershell -ExecutionPolicy Bypass -File tools\apply_refactor.ps1            # cria branch refactor/dtssl, add, commit
  powershell -ExecutionPolicy Bypass -File tools\apply_refactor.ps1 -DryRun    # só mostra o que faria

.NOTAS
  - Requer git for Windows com git-lfs (os .slx/.usd/.stp continuam como ponteiros LFS).
  - Nunca faz push. Nunca apaga _to_delete/ (revise e apague manualmente depois).
  - Se já estiver na branch refactor/dtssl, apenas adiciona e commita.
  - Remove pastas vazias deixadas pelos moves (a VM do Cowork não pode apagar diretórios).
#>
param(
  [switch]$DryRun,
  [string]$Branch = "refactor/dtssl",
  [string]$Message = "refactor: dtssl package, twin server (ssl-simulation-protocol), GUI+DualSense, MuJoCo backends, MATLAB live/legacy split, docs (ADR-001) - applied from Cowork session 2026-09-02"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path ".git")) { throw "Rode este script na raiz do repositório digitaltwin (pasta com .git)." }
if (-not (Test-Path "src/dtssl/__init__.py")) { throw "Overlay não aplicado: src/dtssl não existe." }
git lfs version | Out-Null

# 1) pastas vazias deixadas pelos moves
$skip = @(".git", "_to_delete", "data", "scripts\local", ".dvc", "slr", "cad", "usd", "models", "tests")
Get-ChildItem -Directory -Recurse -Force | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object {
  $rel = Resolve-Path -Relative $_.FullName
  $rel = $rel -replace '^\.\\', ''
  if ($skip | Where-Object { $rel -like "$_*" }) { return }
  if (-not (Get-ChildItem -Force $_.FullName | Select-Object -First 1)) {
    Write-Host "rmdir $rel"
    if (-not $DryRun) { Remove-Item -Force $_.FullName }
  }
}

# 2) branch
$current = (git rev-parse --abbrev-ref HEAD).Trim()
Write-Host "Branch atual: $current"
if ($current -ne $Branch) {
  $exists = (git branch --list $Branch | Out-String).Trim()
  if ($exists) {
    Write-Host "Branch $Branch já existe -> checkout"
    if (-not $DryRun) { git checkout $Branch }
  } else {
    Write-Host "Criando branch $Branch a partir de $current"
    if (-not $DryRun) { git checkout -b $Branch }
  }
}

# 3) add + commit
Write-Host "git add -A (renames/deletes/novos; .gitattributes normaliza CRLF->LF; LFS mantém ponteiros)"
if (-not $DryRun) {
  git add -A
  $n = (git status --short | Measure-Object -Line).Lines
  Write-Host "Entradas no índice: $n"
  git commit -m $Message
  Write-Host "Commit criado:"; git log --oneline -1
  Write-Host "LFS check (esperado: pid_v3 + legacy/archive/rl/rl_model{,_with_ros} + legacy/simulink/simulink_tests):"
  git lfs ls-files | Select-String "slx"
  Write-Host "Objetos soltos (considere 'git gc' depois):"; git count-objects -vH | Select-String "count|size-pack"
} else {
  git status --short | Select-Object -First 40
}
Write-Host "Pronto. Próximos passos: pip install -e .[gui,mujoco,dev] ; python -m pytest ; dtssl info ; dtssl gui"
