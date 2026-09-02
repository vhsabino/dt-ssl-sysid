function params = identify_per_dof(dataByDOF, opts)
% identify_per_dof - Identifica K, tau, Td por DOF a partir dos iddata montados.
%
% Estrutura alvo (contínua):
%       G_i(s) = K_i / (tau_i * s + 1) * exp(-Td_i * s),   i in {x, y, theta}
%
% Saída:
%   params.x.K, params.x.tau, params.x.Td   (idem para y, theta)
%   params.x.sys  -> idtf identificado
%   params.x.fit  -> FitPercent reportado pela toolbox
%
% Requer: System Identification Toolbox (tfest / procest).
%
% Notas:
%   - usei `procest` com estrutura 'P1D' (1 polo + atraso). É a estrutura
%     correta dado que tau_e fica abaixo de Nyquist a 60 Hz.
%   - Se você preferir tfest, basta trocar (comentário abaixo).

    arguments
        dataByDOF (1,1) struct
        opts.searchOptions struct = struct()
        opts.maxIter (1,1) double = 50
    end

    params = struct();
    dofs   = {'x','y','theta'};

    for k = 1:numel(dofs)
        dof = dofs{k};
        if ~isfield(dataByDOF, dof) || isempty(dataByDOF.(dof))
            warning('Sem dados para DOF %s — pulando.', dof);
            continue;
        end
        d = dataByDOF.(dof);

        % Mantém só SISO pra identificação (square é MIMO; usamos só na validação)
        if size(d, 'Nu') > 1
            warning('DOF %s tem entrada MIMO; ignorando para identificação isolada.', dof);
            continue;
        end

        fprintf('\n=== Identificando DOF %s ===\n', dof);

        % --- modelo de processo 1ª ordem + atraso (procest, recomendado) ---
        opt = procestOptions('SearchMethod','auto','Display','off');
        opt.SearchOptions.MaxIterations = opts.maxIter;
        sys = procest(d, 'P1D', opt);

        % Métrica reportada pela toolbox (comparação 1-passo); usa simulação:
        [~, fit, ~] = compare(d, sys);
        if iscell(fit), fit = mean(cell2mat(fit)); end

        % Extrai params
        K    = sys.Kp;
        tau  = sys.Tp1;
        Td   = sys.Td;

        params.(dof).sys = sys;
        params.(dof).K   = K;
        params.(dof).tau = tau;
        params.(dof).Td  = Td;
        params.(dof).fit = fit;

        fprintf('K = %.4f | tau = %.4f s | Td = %.4f s | fit = %.1f%%\n', ...
                K, tau, Td, fit);

        % --- alternativa: tfest (1 polo, 0 zeros, com InputDelay livre) ---
        % np = 1; nz = 0;
        % sys = tfest(d, np, nz, 'InputDelay', NaN);  % NaN -> estima o atraso

        % --- alternativa: ARX/OE pra modelo discreto direto ---
        % sys = oe(d, [2 1 1]);
    end

    % imprime resumo
    fprintf('\n========== RESUMO ==========\n');
    fprintf('%-8s | %-10s | %-10s | %-10s | %-8s\n','DOF','K','tau [s]','Td [s]','fit [%]');
    for k = 1:numel(dofs)
        dof = dofs{k};
        if isfield(params,dof)
            p = params.(dof);
            fprintf('%-8s | %-10.4f | %-10.4f | %-10.4f | %-8.1f\n', ...
                    dof, p.K, p.tau, p.Td, p.fit);
        end
    end
end
