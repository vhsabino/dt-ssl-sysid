% Sensibilidade do gate SE(2) a quantizacao de Td (PARTE C da reidentificacao
% 2026-07-24). O simulador NAO quantiza Td (TransportDelay continuo,
% parametrizado direto por Td_vx/Td_vy/Td_w do SLDD -- confirmado via
% get_param, sem arredondamento). Este script e um teste de sensibilidade
% hipotetico: "se alguem quantizasse Td ao passo mais proximo (floor/ceil),
% o gate SE(2) ainda passaria?" -- NAO uma correcao de um mismatch real.
REPO = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));  % raiz do repo (<repo>/matlab/legacy/batch_20260724/<este>.m); era C:\Users\victo\Documents\digitaltwin
DONE = fullfile(REPO, 'build', 'td_quant_gate_DONE.txt');
cd(REPO);
try
    addpath(fullfile(REPO,'matlab'));
    bootstrap_paths('legacy');   % matlab/dtssl + matlab/legacy (ex-automation/)
    cd(REPO);
    clear Ts  % nunca deixar Ts solto no workspace base (achado desta sessao)

    base_vxvy = load(fullfile(REPO,'models','sysid_vxvy_v2.mat'), 'theta0');
    base_w    = load(fullfile(REPO,'models','sysid_omega_rotate_v1.mat'), 'theta0');
    theta_full = base_vxvy.theta0;
    theta_full.K_w  = base_w.theta0.K_w;
    theta_full.tau_w = base_w.theta0.tau_w;
    theta_full.Td_w  = base_w.theta0.Td_w;

    TsGrid = 1/60;
    cases = struct('dof',{},'label',{},'field',{},'steps',{},'Td',{});
    cases(end+1) = struct('dof','vx','label','front_to_back','field','Td_vx','steps',4,'Td',4*TsGrid);
    cases(end+1) = struct('dof','vx','label','front_to_back','field','Td_vx','steps',5,'Td',5*TsGrid);
    cases(end+1) = struct('dof','vy','label','side_to_side', 'field','Td_vy','steps',3,'Td',3*TsGrid);
    cases(end+1) = struct('dof','vy','label','side_to_side', 'field','Td_vy','steps',4,'Td',4*TsGrid);
    cases(end+1) = struct('dof','w', 'label','shoot_to_goal','field','Td_w', 'steps',5,'Td',5*TsGrid);
    cases(end+1) = struct('dof','w', 'label','shoot_to_goal','field','Td_w', 'steps',6,'Td',6*TsGrid);

    summary = {};
    for i = 1:numel(cases)
        c = cases(i);
        theta0 = theta_full; %#ok<NASGU>
        theta0.(c.field) = c.Td;
        tag = sprintf('tdquant_%s_%dsteps', c.dof, c.steps);
        candp = fullfile(REPO,'build', sprintf('%s_tmp.mat', tag));
        save(candp, 'theta0');
        [W, T, traj_file] = eval_theta_se2_vs_placeholder(candp, c.label, 'Tag', tag); %#ok<ASGLU>
        pool = W(isnan(W.horizonte_s), :);
        allh_pass = all(W.p_wilcoxon(~isnan(W.horizonte_s)) < 0.05 & W.median_delta_m(~isnan(W.horizonte_s)) < 0);
        summary(end+1,:) = {c.dof, c.label, c.steps, c.Td, pool.median_delta_m, pool.p_wilcoxon, allh_pass}; %#ok<AGROW>
        fprintf('>>> %s: %d passos (Td=%.4fs) | pool delta=%.4f p=%.3g | passa em TODOS os horizontes: %d\n', ...
            c.dof, c.steps, c.Td, pool.median_delta_m, pool.p_wilcoxon, allh_pass);
    end
    Tsum = cell2table(summary, 'VariableNames', ...
        {'dof','label','steps','Td_s','pool_delta_m','pool_p','passa_todos_horizontes'});
    disp(Tsum);
    save(fullfile(REPO,'build','td_quant_gate_result.mat'), 'Tsum');
    writetable(Tsum, fullfile(REPO,'build','td_quant_gate_result.csv'));

    fid = fopen(DONE, 'w');
    fprintf(fid, 'OK\n');
    fclose(fid);
catch ME
    fid = fopen(DONE, 'w');
    if fid > 0
        fprintf(fid, 'ERRO\n%s\n', getReport(ME, 'extended'));
        fclose(fid);
    end
    rethrow(ME);
end
