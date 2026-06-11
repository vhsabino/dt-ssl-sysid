function link_sldd_to_model(model_name, sldd_path)
% LINK_SLDD_TO_MODEL  Vincula sldd ao .slx — só roda uma vez.

    % --- (1) Garante que a pasta do SLDD está no path ---
    [sldd_dir, sldd_base, ext] = fileparts(sldd_path);
    if ~isempty(sldd_dir) && ~contains(path, sldd_dir)
        addpath(sldd_dir);
        fprintf('addpath: %s\n', sldd_dir);
    end
    sldd_filename = [sldd_base, ext];   % "ssl_robot.sldd" (só o nome)

    load_system(model_name);

    cur = get_param(model_name, 'DataDictionary');
    if ~isempty(cur)
        warning('Modelo já vinculado a "%s". Sobrescrevendo.', cur);
    end

    % --- (2) Passa só o NOME do arquivo, não o path ---
    set_param(model_name, 'DataDictionary', sldd_filename);

    % --- (3) Limpa Model Workspace dos params do SLDD ---
    mws  = get_param(model_name, 'ModelWorkspace');
    vars = mws.whos;
    targets = {'K_vx','tau_vx','Td_vx','K_vy','tau_vy','Td_vy', ...
               'K_w','tau_w','Td_w','sat_v','sat_w','Ts'};
    for k = 1:numel(vars)
        if ismember(vars(k).name, targets)
            mws.evalin(sprintf('clear %s', vars(k).name));
            fprintf('Removido do MW: %s\n', vars(k).name);
        end
    end

    save_system(model_name);
    fprintf('Modelo vinculado a "%s".\n', sldd_filename);
end