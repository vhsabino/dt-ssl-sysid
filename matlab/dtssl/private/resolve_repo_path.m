function p = resolve_repo_path(p)
%RESOLVE_REPO_PATH Caminho relativo -> absoluto contra a raiz do repo.
% Caminhos ja absolutos (Windows 'C:\...', UNC '\\', ou POSIX '/') e vazios
% sao devolvidos inalterados.
p = char(p);
if isempty(p), return; end
is_abs = p(1) == '/' || p(1) == '\' || (numel(p) >= 2 && p(2) == ':');
if ~is_abs
    p = fullfile(dtssl_root(), p);
end
end
