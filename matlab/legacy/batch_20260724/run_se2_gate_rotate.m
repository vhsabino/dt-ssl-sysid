% Wrapper de execucao em lote (batch, fora do MCP sincrono -- 18 simulacoes
% Simulink excedem o timeout da chamada interativa) para o gate (iii) do
% candidato omega desta sessao (dataset rotate, malha aberta).
% Grava um marcador ao final (sucesso ou erro) p/ polling externo.
% Caminhos ABSOLUTOS no wrapper (independe de cwd/comportamento do run()).
REPO = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));  % raiz do repo (<repo>/matlab/legacy/batch_20260724/<este>.m); era C:\Users\victo\Documents\digitaltwin
DONE = fullfile(REPO, 'build', 'se2_gate_rotate_DONE.txt');
cd(REPO);
try
    addpath(fullfile(REPO,'matlab'));
    bootstrap_paths('legacy');   % matlab/dtssl + matlab/legacy (ex-automation/)
    cd(REPO);
    [W, T, traj_file] = eval_omega_v3_se2('CandMat', fullfile(REPO,'build','sysid_omega_rotate_v1_tmp.mat'));
    save(fullfile(REPO,'build','se2_gate_rotate_result.mat'), 'W', 'T', 'traj_file');
    fid = fopen(DONE, 'w');
    fprintf(fid, 'OK\n%s\n', traj_file);
    fclose(fid);
catch ME
    fid = fopen(DONE, 'w');
    if fid > 0
        fprintf(fid, 'ERRO\n%s\n', getReport(ME, 'extended'));
        fclose(fid);
    end
    rethrow(ME);
end
