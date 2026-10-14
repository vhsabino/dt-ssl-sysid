function repo_root = bootstrap_paths(varargin)
% BOOTSTRAP_PATHS  Adiciona as pastas MATLAB do dtssl ao path (sem cd()).
%
%   repo_root = bootstrap_paths()             % raiz = pasta acima deste arquivo
%   repo_root = bootstrap_paths('legacy')     % + matlab/legacy (scripts arquivados)
%   repo_root = bootstrap_paths(root)         % raiz explicita (compatibilidade)
%   repo_root = bootstrap_paths(root,'legacy')
%
% A raiz do repositorio e derivada da localizacao deste arquivo
% (<repo>/matlab/bootstrap_paths.m) -- nao depende de pwd nem de caminhos
% Windows hard-coded. Diferente da versao antiga (scripts/bootstrap_paths.m,
% ate 2026-09-02), esta funcao NAO muda o diretorio corrente: caminhos
% relativos nos scripts vivos (matlab/dtssl) sao resolvidos contra repo_root.
% Scripts em matlab/legacy ainda assumem pwd == raiz (ver matlab/legacy/README.md).
%
% Pastas adicionadas (se existirem): matlab, matlab/dtssl, matlab/sldd,
% matlab/simulink_io, config, simulink, results. Com 'legacy': tambem
% genpath(matlab/legacy).

    here = fileparts(mfilename('fullpath'));          % <repo>/matlab
    repo_root = fileparts(here);                       % <repo>
    add_legacy = false;

    for k = 1:numel(varargin)
        a = varargin{k};
        if (ischar(a) || isstring(a)) && strcmpi(strtrim(char(a)), 'legacy')
            add_legacy = true;
        elseif (ischar(a) || isstring(a)) && ~isempty(char(a))
            if ~isfolder(char(a))
                error('bootstrap_paths: pasta inexistente: %s', char(a));
            end
            repo_root = char(a);
        elseif ~isempty(a)
            error('bootstrap_paths: argumento nao reconhecido (use ''legacy'' ou um caminho).');
        end
    end

    if ~isfolder(fullfile(repo_root, 'matlab')) || ~isfolder(fullfile(repo_root, 'config'))
        error(['bootstrap_paths: %s nao parece ser a raiz do repo ' ...
               '(esperado matlab/ e config/).'], repo_root);
    end

    folders = {'matlab', fullfile('matlab','dtssl'), fullfile('matlab','sldd'), ...
               fullfile('matlab','simulink_io'), 'config', 'simulink', 'results'};
    for k = 1:numel(folders)
        p = fullfile(repo_root, folders{k});
        if isfolder(p), addpath(p); end
    end

    if add_legacy
        p = fullfile(repo_root, 'matlab', 'legacy');
        if isfolder(p), addpath(genpath(p)); end
    end

    if nargout == 0
        fprintf('bootstrap_paths: raiz do repo = %s (pwd inalterado)\n', repo_root);
    end
end
