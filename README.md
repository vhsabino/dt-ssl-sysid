# Overlay de Refatoração — Doutorado DT-SSL

Este kit é um OVERLAY: copie o conteúdo para a RAIZ do seu repositório
existente sem apagar nada (src/, data/, models/ permanecem).

    rsync -av --ignore-existing dt-ssl-phd-overlay/ ~/seu-repo/

Depois:
1. Revise e personalize CLAUDE.md (5-10 min) — é o cérebro da automação.
2. Leia ROADMAP.md e bloqueie os gates no calendário.
3. No Claude Code, os comandos /triagem, /experimento e /secao-artigo
   já estarão disponíveis.

Estrutura: docs/ (definições formais) • slr/ (protocolo + pipeline) •
paper/ (outline + seções) • automation/ (orquestrador MATLAB) •
.claude/commands/ (workflows de 1 comando).
