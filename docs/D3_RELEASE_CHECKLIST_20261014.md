# D3 / WP5: pacote de reprodução, dry-run de 14/10/2026 e o que falta decidir

*Escrito em 14/10/2026 depois de rodar `tools/make_release.py` em dry-run (saída em
`_to_delete\release_dryrun\dtssl-release`, fora do git). Nada foi publicado. Complementa
`docs/GUIA_ANONIMIZACAO_REPO.md` (checklist de julho) e o WP5 de `claude/plano-artigo-journal-2026-09-23.md`.*

## 1. O que o dry-run produziu

- Pacote de 8,5 MB: `src/dtssl` (157 arquivos, com as malhas CAD), `config/` (11), `tests/` (52), `matlab/dtssl`
  (21), `docs/` (os 8 pré-registros), `results/` (56 arquivos: os artefatos do SBR, os de setembro e outubro e o
  `CHANGELOG.md`), `figures/` (as 5 do SBR), `README.md`, `requirements.txt`, `LICENSE` (MIT), `pyproject.toml`.
- Varredura final limpa (nenhum token proibido em nenhum arquivo, texto ou binário). Conferência extra à mão com
  `findstr` por `ufpe`, `victo`, `WIN-DU3`, `robocin`, `sabino` e `vhssa`, sem acerto.

## 2. O que mudou no repo para o pacote fechar

1. As oito malhas OBJ de `src/dtssl/physics/assets/` traziam na linha 2 do cabeçalho o caminho privado do
   Inventor (`C:\Users\...\robot_v2025_v3.iam`); o pacote falhava na varredura. O cabeçalho passou a trazer só o
   nome do arquivo, o `meshes.json` foi re-registrado (`tools/register_cad_meshes.py`, md5 novos, geometria
   intocada) e o exportador (`tools/inventor_export_cad.m`) passou a escrever só o nome. Testes de CAD e GUI
   passam.
2. `tools/make_release.py`: manifesto com os artefatos de setembro e outubro (C2a, C1, C1b v1 e v2, B3, C4, C2b,
   C2b2 sessões 1 e 2, MIMO e controles) e com os pré-registros; `results/CHANGELOG.md` entra inteiro (é a
   proveniência de cada número; o scrub troca os hashes de commit por `withheld`); título do README igual ao do
   artigo aceito; tabela "Extension: one command per claim".
3. Scrub e lista de proibidos ampliados depois do dry-run: o primeiro nome sozinho, o nome de usuário dentro de
   caminhos (inclusive com barras duplicadas de JSON), `RoboCIn` com I maiúsculo, `ufpe` minúsculo e o nome do PC.
   Sem isso vazavam em `closed_loop_stats_*.json`, `session_report_*.json`, no CHANGELOG, em dois pré-registros e
   em cinco módulos.

## 3. Limites do pacote como está

- Ele é anonimizado por construção (double-blind do SBR). Para a extensão no periódico, se a revisão não for
  cega, o pacote deve sair identificado: autor, instituição, equipe, URL real do repositório e o DOI. O
  `make_release.py` ainda não tem um modo identificado; é um flag a acrescentar quando a decisão vier.
- Os dados não vão no pacote: `data/extracted` (818 arquivos, 78,8 MB, agora com os splits de rotação) e
  `results/sessao_01` estão no DVC com remoto local (`C:\Users\victo\dvc-store-digitaltwin`). Um pacote público
  precisa de um depósito dos dados (Zenodo aceita até 50 GB) ou de uma declaração de disponibilidade sob pedido.
  Os logs de competição são da equipe: a autorização para publicá-los é uma decisão com a orientadora e a equipe.
- O pacote copia do disco: os três artefatos de 18/09 (`protocol_holdout_20260918_*`) e as três entradas de
  23/09 do CHANGELOG continuam fora do git; num clone limpo o pacote ficaria sem eles até o commit pendente.
- Figuras: só as cinco do SBR. As do periódico (`latex_journal/figures/*.pdf`) entram quando o manuscrito fechar
  (uma linha no manifesto).
- `pyproject.toml` ainda aponta para o URL anônimo de placeholder quando anonimizado; o URL real é o do GitHub.
- O `README` do pacote descreve o artigo do SBR e lista a extensão como "in preparation"; o texto final depende do
  título e das contribuições do periódico (decisão com a orientadora).

## 4. Decisões para fechar o D3 (ninguém além de você e da orientadora)

| Decisão | Opções | Minha recomendação |
|---|---|---|
| Anonimizado ou identificado | double-blind (como hoje) / identificado (autor, instituição, DOI) | identificado para o periódico, se a revisão não for cega; manter o modo anônimo como flag |
| Licença | MIT (a atual) / outra | manter MIT |
| Dados | Zenodo (dataset com DOI próprio) / sob pedido / só os artefatos | Zenodo para `data/extracted` e `results/sessao_01`, se a equipe autorizar |
| DOI do código | Zenodo ligado ao GitHub (release `v1.0.0` já existe como tag) / sem DOI | Zenodo pela tag `v1.0.0` ou por uma tag do artigo |
| Autoria e CRediT | você + orientadora + quem fez coleta e CAD | com a orientadora (§7 do plano do periódico) |

Quando as decisões vierem: `python tools/make_release.py --zip` (ou com o flag identificado), conferir o
`README`, depositar no Zenodo, colocar o DOI no manuscrito (Data and code availability) e no `pyproject.toml`.
