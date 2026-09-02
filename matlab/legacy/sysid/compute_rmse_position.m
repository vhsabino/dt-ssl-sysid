function J = compute_rmse_position(theta, dataByDOF, opts)
% compute_rmse_position - Função objetivo da BO em posição (mm), com janelas
% deslizantes rebaseadas para mitigar drift de integração.
%
% theta: vetor de 9 params [Kx tau_x Td_x  Ky tau_y Td_y  Kt tau_t Td_t]
% dataByDOF: estrutura saindo do build_idData_per_dof
% J: RMSE total em mm (escalar) — soma quadrática ponderada de x,y,θ
%
% Esquema:
%   1) constrói G_i(s) = K_i / (tau_i s + 1) * exp(-Td_i s) para cada DOF
%   2) simula em laço aberto sobre cada segmento do iddata
%   3) integra v_modelo -> pos_modelo
%   4) janela deslizante: rebaseia pos a zero a cada `window_sec`
%   5) RMSE em mm dentro de cada janela; média entre janelas e segmentos
%
% Justificativa: posição é o que importa, mas integração livre acumula viés.
% Janelas curtas (2-3s) capturam dinâmica sem deixar drift dominar.

    arguments
        theta     (1,:) double
        dataByDOF (1,1) struct
        opts.window_sec (1,1) double = 2.5
        opts.overlap    (1,1) double = 0.5    % 50% overlap
        opts.weight_x   (1,1) double = 1.0
        opts.weight_y   (1,1) double = 1.0
        opts.weight_th  (1,1) double = 0.5   % θ entra mais leve por ter menos dados
        opts.use_val_out (1,1) logical = false  % se true, avalia em val_out
    end

    if numel(theta) ~= 9
        error('theta deve ter 9 elementos: [Kx tau_x Td_x Ky tau_y Td_y Kt tau_t Td_t]');
    end

    % substitui NaN por valores "neutros" (modelo de θ vira ganho 1, sem dinâmica)
    nan_mask = isnan(theta);
    if any(nan_mask)
        warning('compute_rmse_position: %d params são NaN, usando placeholders.', sum(nan_mask));
        placeholders = [1 0.1 0  1 0.1 0  1 0.1 0];  % K=1, tau=0.1, Td=0
        theta(nan_mask) = placeholders(nan_mask);
    end

    Kx=theta(1); tx=theta(2); dx=theta(3);
    Ky=theta(4); ty=theta(5); dy=theta(6);
    Kt=theta(7); tt=theta(8); dt=theta(9);

    % --- guards: parâmetros fisicamente inválidos retornam Inf ---
    if any(theta(2:3:end) <= 0) || any(theta(3:3:end) < 0) || any(abs(theta(1:3:end)) < 1e-6)
        J = 1e6; return;
    end

    Gx = tf(Kx, [tx 1], 'InputDelay', dx);
    Gy = tf(Ky, [ty 1], 'InputDelay', dy);
    Gt = tf(Kt, [tt 1], 'InputDelay', dt);

    if opts.use_val_out && isfield(dataByDOF,'val_out')
        src = dataByDOF.val_out;
    else
        src = dataByDOF;
    end

    rmse_x = compute_for_dof(Gx, src, 'x',     opts);
    rmse_y = compute_for_dof(Gy, src, 'y',     opts);
    rmse_t = compute_for_dof(Gt, src, 'theta', opts);

    % se θ veio NaN no input original, descarta sua contribuição
    if any(nan_mask(7:9))
        opts.weight_th = 0;
    end

    % combina (todos em mm e mrad já, ver compute_for_dof)
    J = sqrt( opts.weight_x  * rmse_x^2 + ...
              opts.weight_y  * rmse_y^2 + ...
              opts.weight_th * rmse_t^2 );
end

function rmse_mm = compute_for_dof(G, src, dof, opts)
    if ~isfield(src,dof) || isempty(src.(dof))
        rmse_mm = 0; return;
    end
    d = src.(dof);
    % Para 'square' (MIMO) usaríamos só uma coluna, mas aqui DOFs são SISO.
    if size(d, 'Nu') > 1, rmse_mm = 0; return; end

    Ts = d.Ts;
    if iscell(Ts), Ts = Ts{1}; end
    Ts = double(Ts);
    win = round(opts.window_sec / Ts);
    step = max(1, round(win * (1 - opts.overlap)));

    % iddata pode ser merged (multi-experimento) — itera por experimento
    nExp = size(d, 'Ne');   % Ne = número de experimentos no iddata
    experiments = cell(nExp,1);
    for e = 1:nExp, experiments{e} = getexp(d, e); end

    rmses = []; weights = [];
    for e = 1:numel(experiments)
        de = experiments{e};
        if size(de.y,1) < win, continue; end

        % simula em laço aberto: y_sim = G * u
        try
            ysim = lsim(G, de.u, (0:size(de.u,1)-1)'*Ts);
        catch
            rmse_mm = 1e6; return;  % G instável → penaliza
        end

        ymeas = de.y;

        % converte vel -> pos (cumtrapz em mm; vel está em m/s e rad/s)
        if strcmp(dof,'theta')
            pmeas = cumtrapz(ymeas)*Ts*1000;  % rad -> mrad (escala comparável a mm)
            psim  = cumtrapz(ysim) *Ts*1000;
        else
            pmeas = cumtrapz(ymeas)*Ts*1000;  % m -> mm
            psim  = cumtrapz(ysim) *Ts*1000;
        end

        % janelas deslizantes com rebase
        for s = 1:step:(numel(pmeas) - win + 1)
            idx = s:(s+win-1);
            pm = pmeas(idx) - pmeas(idx(1));
            ps = psim(idx)  - psim(idx(1));
            rmses(end+1) = sqrt(mean((pm - ps).^2));  %#ok<AGROW>
            weights(end+1) = numel(idx);              %#ok<AGROW>
        end
    end

    if isempty(rmses)
        rmse_mm = 0;
    else
        rmse_mm = sqrt(sum(weights .* rmses.^2) / sum(weights));
    end
end
