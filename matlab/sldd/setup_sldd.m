function setup_sldd(sldd_path, theta0_mat)
% SETUP_SLDD  Cria/recria ssl_robot.sldd com os 9 params + Ts + saturações.

    if nargin < 2, theta0_mat = ''; end

    % --- Garante que a pasta-mãe existe ---
    [sldd_dir,~,~] = fileparts(sldd_path);
    if ~isempty(sldd_dir) && ~isfolder(sldd_dir)
        mkdir(sldd_dir);
        fprintf('Pasta criada: %s\n', sldd_dir);
    end

    % --- Valores iniciais (default neutro) ---
    p = struct( ...
        'K_vx',  1.00, 'tau_vx', 0.10, 'Td_vx', 0.05, ...
        'K_vy',  1.00, 'tau_vy', 0.10, 'Td_vy', 0.05, ...
        'K_w',   1.00, 'tau_w',  0.08, 'Td_w',  0.04);

    % --- NOVO: carrega e normaliza θ do .mat (aceita struct OU vetor) ---
    if ~isempty(theta0_mat) && isfile(theta0_mat)
        p_loaded = load_theta_mat(theta0_mat);    % helper abaixo
        % merge: campos do .mat sobrescrevem o default
        fn_loaded = fieldnames(p_loaded);
        for k = 1:numel(fn_loaded)
            p.(fn_loaded{k}) = p_loaded.(fn_loaded{k});
        end
        fprintf('SLDD populado com θ de %s\n', theta0_mat);
    end

    % --- Limites (bayesopt usa estes Min/Max como bounds) ---
    bounds = struct( ...
        'K_vx',  [0.5 2.0], 'tau_vx', [0.01 0.5], 'Td_vx', [0 0.20], ...
        'K_vy',  [0.5 2.0], 'tau_vy', [0.01 0.5], 'Td_vy', [0 0.20], ...
        'K_w',   [0.5 2.0], 'tau_w',  [0.01 0.5], 'Td_w',  [0 0.20]);

    % --- Fixos (saturações + Ts) ---
    fixed = struct('sat_v', 3.0, 'sat_w', 10.0, 'Ts', 1/60);

    % --- Cria dicionário do zero ---
    if isfile(sldd_path)
        delete(sldd_path);
        fprintf('SLDD antigo removido: %s\n', sldd_path);
    end
    dd  = Simulink.data.dictionary.create(sldd_path);
    sec = getSection(dd, 'Design Data');

    % --- Tunáveis ---
    fn = fieldnames(p);
    for k = 1:numel(fn)
        name = fn{k};
        sp = Simulink.Parameter(p.(name));
        sp.CoderInfo.StorageClass = 'SimulinkGlobal';
        sp.DataType = 'double';
        if isfield(bounds, name)
            sp.Min = bounds.(name)(1);
            sp.Max = bounds.(name)(2);
        end
        addEntry(sec, name, sp);
    end

    % --- Fixos ---
    fn = fieldnames(fixed);
    for k = 1:numel(fn)
        name = fn{k};
        sp = Simulink.Parameter(fixed.(name));
        sp.CoderInfo.StorageClass = 'Auto';
        sp.DataType = 'double';
        addEntry(sec, name, sp);
    end

    saveChanges(dd); close(dd);
    fprintf('SLDD criado: %s (%d entradas)\n', sldd_path, ...
            numel(fieldnames(p)) + numel(fieldnames(fixed)));
end