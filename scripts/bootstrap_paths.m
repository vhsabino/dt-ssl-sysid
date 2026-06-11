function repo_root = bootstrap_paths(repo_root)
% BOOTSTRAP_PATHS  Adiciona pastas do repo ao path, autodetectando a raiz.
%   bootstrap_paths()             % autodetecta a partir de pwd
%   bootstrap_paths('C:\...\digitaltwin')

    if nargin < 1 || isempty(repo_root)
        repo_root = find_repo_root(pwd);
    end

    if isempty(repo_root)
        error(['Não consegui localizar a raiz do repo a partir de %s.\n' ...
               'Roda: cd C:\\Users\\victo\\Documents\\digitaltwin'], pwd);
    end

    folders = { ...
        'matlab', 'matlab/sldd', 'matlab/sysid', 'matlab/simulink_io', ...
        'matlab/analytical', 'matlab/train', 'matlab/viewer', ...
        'config', 'scripts', 'simulink', 'results'};

    for k = 1:numel(folders)
        p = fullfile(repo_root, folders{k});
        if isfolder(p), addpath(genpath(p)); end
    end

    % --- Muda pwd pra raiz pra que caminhos relativos funcionem ---
    cd(repo_root);
    fprintf('Raiz do repo: %s\n', repo_root);
    fprintf('pwd ajustado para a raiz.\n');
end

% =========================================================================
function root = find_repo_root(start_dir)
% Sobe na árvore até achar uma pasta que contenha 'matlab' E 'config' (ou data)
    root = '';
    cur  = start_dir;
    for k = 1:6   % no máx 6 níveis acima, evita loop infinito
        if isfolder(fullfile(cur, 'matlab')) && ...
           (isfolder(fullfile(cur, 'config')) || isfolder(fullfile(cur, 'data')))
            root = cur; return;
        end
        parent = fileparts(cur);
        if isequal(parent, cur), return; end   % chegou na raiz do disco
        cur = parent;
    end
end