function root = dtssl_root()
%DTSSL_ROOT Raiz do repositorio, derivada da localizacao deste arquivo
% (<repo>/matlab/dtssl/private/dtssl_root.m). Usado pelos scripts vivos para
% resolver caminhos relativos (config/, models/, build/, results/, tests/)
% sem depender de pwd -- bootstrap_paths nao muda mais o diretorio corrente.
root = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));
end
