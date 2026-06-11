function [theta, meta] = load_theta_mat(mat_path)
% LOAD_THETA_MAT  Carrega θ e (opcional) metadados de identificação.
%
% Saída:
%   theta - struct com os 9 params nomeados
%   meta  - struct com report, params0, dataByDOF (se existirem)

    NAMES = {'K_vx','tau_vx','Td_vx', ...
             'K_vy','tau_vy','Td_vy', ...
             'K_w', 'tau_w', 'Td_w'};

    S = load(mat_path);
    candidates = {'theta0','theta_opt','theta'};

    raw = [];
    for k = 1:numel(candidates)
        if isfield(S, candidates{k})
            raw = S.(candidates{k});
            fprintf('  → usando variável "%s" de %s\n', candidates{k}, mat_path);
            break;
        end
    end
    if isempty(raw)
        error('Nenhum θ em %s. Esperado: theta0/theta_opt/theta.', mat_path);
    end

    % Normaliza pra struct
    if isstruct(raw)
        missing = setdiff(NAMES, fieldnames(raw));
        if ~isempty(missing)
            error('Struct θ sem campos: %s', strjoin(missing, ', '));
        end
        theta = raw;
    elseif isnumeric(raw)
        raw = raw(:).';
        if numel(raw) ~= 9
            error('Vetor θ tem %d elementos, esperado 9.', numel(raw));
        end
        theta = cell2struct(num2cell(raw), NAMES, 2);
    else
        error('Formato de θ não suportado: %s', class(raw));
    end

    % --- NOVO: empacota metadados ---
    if nargout >= 2
        meta = struct();
        for f = {'report','params0','dataByDOF'}
            if isfield(S, f{1}), meta.(f{1}) = S.(f{1}); end
        end
        meta.source_file = mat_path;
        meta.loaded_at   = datetime('now');
    end
end