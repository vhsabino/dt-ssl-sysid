function report = cross_log_validation(theta, dataByDOF, opts)
% cross_log_validation - Reporta degradação do modelo em log out-of-distribution.
%
% Saída: tabela com RMSE_pos (mm) por DOF em (a) treino, (b) val_out, e razão.
% Critério qualitativo:
%   razão < 1.3   -> generaliza bem
%   1.3 - 2.0     -> degradação aceitável
%   > 2.0         -> overfitting OU os logs têm distribuição muito diferente

    arguments
        theta     (1,:) double
        dataByDOF (1,1) struct
        opts.window_sec (1,1) double = 2.5
        opts.overlap    (1,1) double = 0.5
    end

    has_val = isfield(dataByDOF,'val_out');
    if ~has_val
        warning('Sem val_out — passa um struct com .train e .val_out em build_idData_per_dof');
    end

    fprintf('\n========= CROSS-LOG VALIDATION =========\n');

    % Auxiliar: roda compute_rmse_position só pra um DOF, num conjunto específico
    function r = rmse_dof(set, dof)
        if ~isfield(set,dof) || isempty(set.(dof)), r = NaN; return; end
        % constrói G só desse DOF e zera os outros pesos
        switch dof
            case 'x',     w = [1 0 0];
            case 'y',     w = [0 1 0];
            case 'theta', w = [0 0 1];
        end
        % faz a busca chamando compute_rmse_position com pesos isolados
        J = compute_rmse_position(theta, set, ...
            'window_sec', opts.window_sec, 'overlap', opts.overlap, ...
            'weight_x', w(1), 'weight_y', w(2), 'weight_th', w(3), ...
            'use_val_out', false);  % set já é o que quero
        r = J;  % com peso unitário em só um DOF, J = RMSE daquele DOF
    end

    dofs = {'x','y','theta'};
    rows = cell(numel(dofs),1);
    for i = 1:numel(dofs)
        d = dofs{i};
        r_train = rmse_dof(dataByDOF, d);
        if has_val
            % chama com val_out empacotado como "raiz" do struct
            tmp = struct(d, dataByDOF.val_out.(d));
            r_val = rmse_dof(tmp, d);
        else
            r_val = NaN;
        end
        ratio = r_val / max(r_train, 1e-6);
        verdict = '—';
        if ~isnan(ratio)
            if ratio < 1.3,        verdict = 'OK';
            elseif ratio < 2.0,    verdict = 'aceitável';
            else,                  verdict = '⚠ overfit/dist-shift'; end
        end
        rows{i} = struct('DOF',d,'rmse_train_mm',r_train,'rmse_val_mm',r_val, ...
                         'ratio',ratio,'verdict',verdict);
        fprintf('%-6s | train=%.2f mm | val=%.2f mm | ratio=%.2f | %s\n', ...
                d, r_train, r_val, ratio, verdict);
    end

    report = struct2table(vertcat(rows{:}));
end
