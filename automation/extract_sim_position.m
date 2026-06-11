function [t, px, py] = extract_sim_position(out)
%EXTRACT_SIM_POSITION Localiza posicao simulada (m) no SimulationOutput.
% Prefere a posicao ALINHADA por SE(2) (pos_*_aligned, anexada por
% run_one_mat); cai para os sinais brutos do modelo. Nomes reais
% observados em parameter_estimation_model_pid_v3 via out.who
% (inspecao 2026-06-11): pos_x_out, pos_y_out (timeseries top-level).
candX = ["pos_x_aligned","pos_x_out","pos_x_sim","pos_x"];
candY = ["pos_y_aligned","pos_y_out","pos_y_sim","pos_y"];
avail = string(out.who);
nx = candX(find(ismember(candX, avail), 1));
ny = candY(find(ismember(candY, avail), 1));
if isempty(nx) || isempty(ny)
    error(['Nao achei posicao simulada (esperado: %s / %s). ' ...
        'Disponivel no SimulationOutput: %s'], strjoin(candX,','), ...
        strjoin(candY,','), strjoin(avail, ', '));
end
vx = out.get(char(nx));  vy = out.get(char(ny));
t = vx.Time;  px = squeeze(vx.Data);  py = squeeze(vy.Data);
end
