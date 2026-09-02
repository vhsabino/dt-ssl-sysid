function run_td_quantization_case(caseIdx)
%RUN_TD_QUANTIZATION_CASE Roda 1 caso de sensibilidade de quantizacao de Td
% (PARTE C da reidentificacao 2026-07-24) em processo MATLAB isolado
% (evita contaminacao de estado do SLDD/Simulink entre casos observada ao
% rodar os 6 casos num loop dentro da mesma sessao).
REPO = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));  % raiz do repo (<repo>/matlab/legacy/batch_20260724/<este>.m); era C:\Users\victo\Documents\digitaltwin
cd(REPO);
addpath(fullfile(REPO,'matlab'));
bootstrap_paths('legacy');   % matlab/dtssl + matlab/legacy (ex-automation/)
cd(REPO);
clear Ts

TsGrid = 1/60;
CASES = struct('dof',{},'label',{},'field',{},'steps',{});
CASES(1) = struct('dof','vx','label','front_to_back','field','Td_vx','steps',4);
CASES(2) = struct('dof','vx','label','front_to_back','field','Td_vx','steps',5);
CASES(3) = struct('dof','vy','label','side_to_side', 'field','Td_vy','steps',3);
CASES(4) = struct('dof','vy','label','side_to_side', 'field','Td_vy','steps',4);
CASES(5) = struct('dof','w', 'label','shoot_to_goal','field','Td_w', 'steps',5);
CASES(6) = struct('dof','w', 'label','shoot_to_goal','field','Td_w', 'steps',6);
c = CASES(caseIdx);
Td = c.steps * TsGrid;

DONE = fullfile(REPO, 'build', sprintf('td_quant_case%d_DONE.txt', caseIdx));
try
    base_vxvy = load(fullfile(REPO,'models','sysid_vxvy_v2.mat'), 'theta0');
    base_w    = load(fullfile(REPO,'models','sysid_omega_rotate_v1.mat'), 'theta0');
    theta0 = base_vxvy.theta0;
    theta0.K_w = base_w.theta0.K_w; theta0.tau_w = base_w.theta0.tau_w; theta0.Td_w = base_w.theta0.Td_w;
    theta0.(c.field) = Td;

    tag = sprintf('tdquant_%s_%dsteps', c.dof, c.steps);
    candp = fullfile(REPO,'build', sprintf('%s_tmp.mat', tag));
    save(candp, 'theta0');

    Simulink.data.dictionary.closeAll('-discard');
    bdclose('all');
    [W, T, traj_file] = eval_theta_se2_vs_placeholder(candp, c.label, 'Tag', tag); %#ok<ASGLU>

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
end
