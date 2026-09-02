function varargout = bootstrap_paths(varargin)
% Forwarder p/ matlab/bootstrap_paths.m (implementacao real, sem cd). Mantido so p/ chamadores antigos.
old = cd(fullfile(fileparts(fileparts(mfilename('fullpath'))), 'matlab')); c = onCleanup(@() cd(old)); %#ok<NASGU>
f = str2func('bootstrap_paths');   % resolvido na pasta matlab/ (precedencia da pasta corrente), nao neste arquivo
[varargout{1:nargout}] = f(varargin{:});
end
