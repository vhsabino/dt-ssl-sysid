# reorganize.ps1
# ------------------------------------------------------------------------------
# Migração da estrutura atual de digitaltwin/ para a nova organização.
#
# USO:
#   # 1) backup ZIP da pasta inteira ANTES de qualquer coisa!
#
#   # 2) dry-run (não move nada, só imprime o que faria):
#   .\reorganize.ps1
#
#   # 3) revise o output. Quando estiver confiante:
#   .\reorganize.ps1 -Execute
#
# Por segurança, o script usa Move-Item (não Copy) — uma vez executado,
# os arquivos saem do lugar original. SEMPRE faça o ZIP de backup antes.
# ------------------------------------------------------------------------------

param(
    [string]$RepoRoot = ".",
    [switch]$Execute   # default: dry-run; passe -Execute para mover de verdade
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path $RepoRoot).Path
Set-Location $RepoRoot

$DryRun = -not $Execute
$mode = if ($DryRun) { "[DRY-RUN]" } else { "[EXECUTANDO]" }
Write-Host "`n========================================" -F Cyan
Write-Host "  REORGANIZAÇÃO digitaltwin/ $mode" -F Cyan
Write-Host "  Root: $RepoRoot" -F Cyan
Write-Host "========================================`n" -F Cyan

if (-not $DryRun) {
    $confirm = Read-Host "Você fez o ZIP de backup da pasta inteira? (yes/no)"
    if ($confirm -ne 'yes') {
        Write-Host "ABORTADO. Faça o backup primeiro." -F Red
        exit 1
    }
}

# ---------- helpers ----------
function Ensure-Dir($path) {
    if (-not (Test-Path $path)) {
        if ($DryRun) { Write-Host "  [mkdir] $path" -F DarkGray }
        else { New-Item -ItemType Directory -Path $path -Force | Out-Null }
    }
}

function Move-Safe($source, $targetDir, $newName = $null) {
    if (-not (Test-Path $source)) {
        Write-Host "  [skip] $source (não existe)" -F DarkYellow
        return
    }
    Ensure-Dir $targetDir
    $target = if ($newName) { Join-Path $targetDir $newName } else { $targetDir }
    if ($DryRun) {
        Write-Host "  $source" -F Gray
        Write-Host "    -> $target" -F Green
    } else {
        Move-Item -Path $source -Destination $target -Force
        Write-Host "  MOVED: $source -> $target" -F Green
    }
}

# ============================================================
# 1. CRIAR ESTRUTURA NOVA
# ============================================================
Write-Host "`n[1/9] Criando estrutura de diretórios..." -F Cyan
$dirs = @(
    "notebooks",
    "python",
    "matlab\viewer",
    "matlab\sysid",
    "matlab\optimization",
    "matlab\simulink_io",
    "matlab\analytical",
    "matlab\train",
    "matlab\ros_bridge",
    "simulink",
    "docs",
    "data\extracted",
    "data\recorded",
    "data\bench",
    "results\checkpoints_TD3",
    "build",
    "archive\rl",
    "archive\old_viewers",
    "archive\old_evaluators",
    "archive\tests"
)
foreach ($d in $dirs) { Ensure-Dir $d }

# ============================================================
# 2. NOTEBOOKS PYTHON (ETL pipeline)
# ============================================================
Write-Host "`n[2/9] Movendo notebooks Python..." -F Cyan
Move-Safe "scripts\local\logExtractor.ipynb"   "notebooks" "01_logExtractor.ipynb"
Move-Safe "scripts\local\splitByLabels.ipynb"  "notebooks" "02_splitByLabels.ipynb"

# ============================================================
# 3. LIBS PYTHON (legacy + atuais)
# ============================================================
Write-Host "`n[3/9] Movendo libs Python..." -F Cyan
Move-Safe "scripts\local\data_select"   "python\data_select"
Move-Safe "scripts\local\proto"         "python\proto"
Move-Safe "scripts\local\pyrecordio"    "python\pyrecordio"
Move-Safe "scripts\local\utils"         "python\utils"
Move-Safe "scripts\kinematics.py"       "python" "kinematics.py"
Move-Safe "scripts\local\test_env.py"   "archive\tests" "test_env.py"

# ============================================================
# 4. MATLAB ATIVO
# ============================================================
Write-Host "`n[4/9] Movendo MATLAB (código ativo)..." -F Cyan

# viewer/
Move-Safe "scripts\VisualizadorSimulink.m"    "matlab\viewer"
Move-Safe "scripts\local\VisualizadorLogPlayer.m"  "matlab\viewer"
Move-Safe "scripts\visualizadorOutputs.m"     "matlab\viewer"

# sysid/ (nosso trabalho)
Move-Safe "scripts\local\build_idData_per_dof.m"   "matlab\sysid"
Move-Safe "scripts\local\identify_per_dof.m"       "matlab\sysid"
Move-Safe "scripts\local\compute_rmse_position.m"  "matlab\sysid"
Move-Safe "scripts\local\cross_log_validation.m"   "matlab\sysid"
Move-Safe "scripts\local\run_sysid.m"              "matlab\sysid"
Move-Safe "scripts\local\run_bayesopt.m"           "matlab\sysid"
# validate_on_square pode estar na raiz local ou foi gerada por nós:
Move-Safe "scripts\local\validate_on_square.m"     "matlab\sysid"

# optimization/ (BO + PSO juntos, para comparação no paper)
Move-Safe "scripts\run_pso_optimization.m"         "matlab\optimization"
Move-Safe "scripts\run_pso_optimization_stage_1.m" "matlab\optimization"
Move-Safe "scripts\train_parameter_estimation.m"   "matlab\optimization"

# simulink_io/
Move-Safe "scripts\local\load_log_to_timeseries.m"     "matlab\simulink_io"
Move-Safe "scripts\local\load_log_to_timeseries_v2.m"  "matlab\simulink_io"
Move-Safe "scripts\local\load_commands_to_timeseries.m" "matlab\simulink_io"
Move-Safe "scripts\kinematics.m"                       "matlab\simulink_io"

# analytical/
Move-Safe "scripts\analyticalModel\inverse_kinematics_solver.m" "matlab\analytical"
Move-Safe "scripts\analyticalModel\kinematicSolver.m"           "matlab\analytical"
Move-Safe "scripts\analyticalModel\local2global.m"              "matlab\analytical"

# train/
Move-Safe "scripts\control_parameters.m"           "matlab\train"
Move-Safe "scripts\avaliar_gemeo_digital.m"        "matlab\train"
Move-Safe "scripts\local\train\time_sync.m"        "matlab\train"
Move-Safe "scripts\local\train\time_raw.m"         "matlab\train"

# ros_bridge/ (mantém estrutura de package MATLAB com +)
Move-Safe "scripts\+bus_conv_fcns"  "matlab\ros_bridge\+bus_conv_fcns"

# ============================================================
# 5. SIMULINK MODELS
# ============================================================
Write-Host "`n[5/9] Movendo modelos Simulink..." -F Cyan
$slxFiles = @(
    "parameter_estimation_model_pid.slx",
    "parameter_estimation_model_pid_v2.slx",
    "parameter_estimation_model_pid_v3.slx",
    "parameter_estimation_model_with_ros.slx",
    "parameter_estimation_model_with_ros_v2.slx",
    "simulink_tests.slx"
)
foreach ($f in $slxFiles) { Move-Safe "scripts\$f" "simulink" }

# ============================================================
# 6. DADOS (-> data/)
# ============================================================
Write-Host "`n[6/9] Movendo dados..." -F Cyan
# Dataset principal extraído
Move-Safe "scripts\local\extracted"  "data\extracted_tmp"
if (-not $DryRun -and (Test-Path "data\extracted_tmp")) {
    # achatar: tinha 2026-05-18 dentro de extracted; agora extracted/2026-05-18
    Get-ChildItem "data\extracted_tmp" | ForEach-Object {
        Move-Item $_.FullName "data\extracted\" -Force
    }
    Remove-Item "data\extracted_tmp" -Force
}

# Logs gravados de outros robôs (treino legado)
Move-Safe "scripts\local\train\robocin_robodragons_id1.mat" "data\recorded"
Move-Safe "scripts\local\train\robocin_robodragons_id7.mat" "data\recorded"
Move-Safe "scripts\local\train\robocin_tests_id5.mat"       "data\recorded"
Move-Safe "scripts\local\train\robocin_tigers_id6.mat"      "data\recorded"

Move-Safe "scripts\log_robo_ssl.csv" "data\recorded"

# Dados de bancada (se já estiver no repo; senão coloque manualmente)
# Move-Safe "data_old_motor.mat" "data\bench"

# ============================================================
# 7. RESULTADOS (-> results/)
# ============================================================
Write-Host "`n[7/9] Movendo resultados..." -F Cyan
Move-Safe "scripts\local\sysid_initial.mat"   "results"
Move-Safe "scripts\local\sysid_bayesopt.mat"  "results"
Move-Safe "scripts\local\cmd_timeseries.mat"  "results"
Move-Safe "scripts\local\log_timeseries.mat"  "results"
Move-Safe "scripts\Control_signals.mat"       "results"
Move-Safe "scripts\local\train\Control_signals.mat"     "results" "Control_signals_train.mat"

# Checkpoints TD3
Move-Safe "scripts\Checkpoints_Agente_TD3"    "results\checkpoints_TD3_tmp"
if (-not $DryRun -and (Test-Path "results\checkpoints_TD3_tmp")) {
    Get-ChildItem "results\checkpoints_TD3_tmp" | ForEach-Object {
        Move-Item $_.FullName "results\checkpoints_TD3\" -Force
    }
    Remove-Item "results\checkpoints_TD3_tmp" -Force
}

# Bus cache MATLAB
Move-Safe "scripts\local\train\+bus_conv_fcns\+ros2\+busToMsg\RefCachedMap.mat" "results" "RefCachedMap.mat"

# ============================================================
# 8. ARCHIVE
# ============================================================
Write-Host "`n[8/9] Arquivando..." -F Cyan

# RL pausado
Move-Safe "scripts\train_rl.m"             "archive\rl"
Move-Safe "scripts\play_rl.m"              "archive\rl"
Move-Safe "scripts\rl_model.slx"           "archive\rl"
Move-Safe "scripts\rl_model_with_ros.slx"  "archive\rl"

# Viewers antigos
Move-Safe "scripts\VisualizadorTempoReal.m"          "archive\old_viewers"
Move-Safe "scripts\VisualizadorTempoReal2.m"         "archive\old_viewers"
Move-Safe "scripts\VisualizadorTempoRealComErro.m"   "archive\old_viewers"

# Versões antigas dos avaliadores
Move-Safe "scripts\avaliar_gemeo_digital_v0.m"       "archive\old_evaluators"
Move-Safe "scripts\avaliar_gemeo_digital_stage_1.m"  "archive\old_evaluators"

# Tests / scratch
Move-Safe "scripts\test.m"                  "archive\tests"
Move-Safe "scripts\test2.m"                 "archive\tests"
Move-Safe "scripts\smoke_test_caminho2.m"   "archive\tests"
Move-Safe "scripts\local\temp.m"            "archive\tests"

# ============================================================
# 9. BUILD ARTIFACTS (-> build/) e LIMPEZA
# ============================================================
Write-Host "`n[9/9] Movendo build artifacts (entrarão no .gitignore)..." -F Cyan
Move-Safe "scripts\slprj"                                            "build"
Move-Safe "scripts\slprj_workers"                                    "build"
Move-Safe "scripts\parameter_estimation_model_with_ros_v2_grt_rtw"   "build"
Move-Safe "scripts\local\slprj"                                      "build" "slprj_local"
Move-Safe "scripts\local\.ipynb_checkpoints"                         "build" "ipynb_checkpoints_legacy"
Move-Safe "scripts\local\train\slprj"                                "build" "slprj_train"

# Bus conv legacy duplicado (já temos em matlab\ros_bridge agora)
Move-Safe "scripts\local\train\+bus_conv_fcns"                       "archive" "bus_conv_fcns_legacy"

# ============================================================
# RELATÓRIO FINAL
# ============================================================
Write-Host "`n========================================" -F Cyan
if ($DryRun) {
    Write-Host "  DRY-RUN concluído. Nada foi movido." -F Yellow
    Write-Host "  Para executar de verdade: .\reorganize.ps1 -Execute" -F Yellow
} else {
    Write-Host "  REORGANIZAÇÃO concluída!" -F Green
    Write-Host "" -F Green
    Write-Host "  Próximos passos:" -F Green
    Write-Host "  1. Verifique se a pasta 'scripts/' está vazia (ou só com arquivos esquecidos)" -F Green
    Write-Host "     >> Get-ChildItem scripts -Recurse" -F Green
    Write-Host "  2. Identifique qual .slx é a versão ativa:" -F Green
    Write-Host "     >> Get-ChildItem simulink\*.slx | Sort LastWriteTime -Desc | Select Name, LastWriteTime" -F Green
    Write-Host "  3. Coloque o data_old_motor.mat em data\bench\ manualmente" -F Green
    Write-Host "  4. git init && git add . && git commit -m 'Initial reorganized structure'" -F Green
}
Write-Host "========================================`n" -F Cyan
