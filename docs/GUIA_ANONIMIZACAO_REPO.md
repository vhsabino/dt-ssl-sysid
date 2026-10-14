# Guia de anonimização do repositório público (double-blind SBR/LARS 2026)

Este guia é específico: cada item foi **verificado por varredura** em
`open-source/` (63 arquivos) em 2026-08-10, não é checklist genérico. Onde diz
"encontrado", eu achei de fato; onde diz "limpo", eu procurei e não achei.

O CFP exige ocultar nomes, contato, agradecimentos e qualquer referência ao
local da pesquisa. O risco real em repositório de código não são os nomes — é o
**rastro**: caminhos, hashes de commit, nomes internos e histórico do git.

---

## 1. O que já está limpo (verificado)

| Verificação | Resultado |
|---|---|
| Nomes próprios, instituição, cidade, e-mail | **nenhuma ocorrência** |
| `LICENSE`, `CITATION.cff`, `.git/` dentro de `open-source/` | **ausentes** |
| Nome de equipe no código | **nenhuma ocorrência** |

---

## 2. O que vaza hoje e precisa de ação

### 2.1 Caminhos absolutos do ambiente — **14 arquivos**

Todos os scripts de análise têm a raiz do projeto embutida:

```python
R = Path('/sessions/happy-modest-euler/mnt/digitaltwin')
```

Isso revela o ambiente e, pior, quebra a reprodução para qualquer outra pessoa.
Substituir em todos os `scripts/*.py` por uma raiz relativa ao próprio arquivo:

```python
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]     # raiz do repositório
```

Um comando resolve:

```bash
cd open-source
grep -rl "sessions/happy-modest-euler" scripts/ | while read f; do
  python3 - "$f" <<'PY'
import re,sys
p=sys.argv[1]; s=open(p,encoding='utf-8').read()
s=re.sub(r"Path\(\s*['\"]/sessions/[^'\"]+['\"]\s*\)",
         "Path(__file__).resolve().parents[1]", s)
open(p,'w',encoding='utf-8').write(s)
PY
done
grep -rc "sessions/happy" scripts/ | grep -v ':0' || echo "limpo"
```

Depois **rode um script** para confirmar que ainda funciona com a raiz relativa.

### 2.2 Hashes de commit e nome do repositório de firmware

Encontrados em `config/robot_geometry.json`, `matlab/identify_trans_dof.m`,
`matlab/identify_omega_rotate.m` e `scripts/build_rotate_qc.py`:

- `commit c283f47`, `commit eb57531`, `commit eb97620`
- `ssl-embedded`, `kinematics.h`

O hash é o vazamento mais sério da lista: se o repositório de firmware for
público, ou vier a ser, qualquer pessoa localiza a equipe em segundos. O nome
`ssl-embedded` já é um forte indicativo.

Ação: substituir por descrições neutras.

| Onde | De | Para |
|---|---|---|
| `robot_geometry.json` | `identico a kinematics.h (ssl-embedded, commit eb57531)` | `identical to the firmware kinematics header (version withheld for review)` |
| `identify_*.m` | `evalc('!git rev-parse --short HEAD')` | `'anonymised'` |
| `build_rotate_qc.py` | menções a commit | remover |

O `git rev-parse` nos scripts MATLAB também grava o hash do **seu** repositório
em cada artefato gerado — desative antes de gerar qualquer coisa nova.

### 2.3 `phase0_replay/meeting_overlay.py`

O nome e o cabeçalho ("figura de overlay para reunião") denunciam uso interno de
equipe e o arquivo não sustenta nenhum resultado do artigo.
**Remova-o do pacote público.** É a única exclusão que eu recomendaria.

### 2.4 Comentários em português — **8 arquivos**

`docs/PREREGISTRO_OMEGA_20260724.md`, `results/identificacao_omega_20260724.md`,
`scripts/analyze_omega_excitation.py`, `scripts/build_rotate_qc.py`,
`scripts/eval_rsim_delay_ablation.py`, `scripts/fig_omega_stepresponse_en.py`,
`scripts/fig_spec_main_result.py`, `phase0_replay/meeting_overlay.py`.

Isto é **risco baixo** — o SBR é brasileiro e boa parte das submissões vem de
grupos que escrevem em português. Não traduza tudo; o custo é alto e o ganho
pequeno. Duas ressalvas:

- `docs/PREREGISTRO_OMEGA_20260724.md` é citado no artigo como evidência do
  pré-registro. Vale traduzir **só este**, porque o revisor vai abri-lo.
- `scripts/fig_spec_main_result.py` gera um diagrama com texto em português.
  Ele não é usado pelo artigo; pode sair do pacote.

### 2.5 Nome do dataset e rótulo de time

`config/holdout_events.json` e `config/twin_params.json` contêm
`2026-05-18_19-2-15` e `"team": "allies"`.

Risco **muito baixo**: é um timestamp de log e um rótulo genérico. Não mexeria.
Mas se a sua equipe publica logs com esse padrão de nome em algum lugar,
renomeie o diretório do dataset para `session_A`.

---

## 3. Onde hospedar

Três opções, em ordem de recomendação:

**Anonymous GitHub** (`anonymous.4open.science`) — espelha um repo real e
substitui nomes automaticamente. Melhor opção: dá URL estável, permite navegar
o código no browser (o revisor não precisa clonar) e expira depois da revisão.
Cuidado: ele anonimiza *conteúdo*, **não o histórico** — veja §4.

**OSF anonymous view** — bom se você quiser depositar dados junto e ter DOI
depois. Dá timestamp verificável, o que reforça o argumento de pré-registro.

**Conta GitHub descartável** — funciona, mas exige disciplina manual (§4) e não
tem timestamp independente. Só use se as outras duas não servirem.

---

## 4. O histórico do git é o vazamento que as pessoas esquecem

Anonimizar arquivos não adianta se o histórico carrega `user.name` e
`user.email` em cada commit. **Não faça `git push` de um clone do repositório
de trabalho.** Crie um repositório novo, sem histórico:

```bash
cd open-source
rm -rf .git
git init
git config user.name  "Anonymous"
git config user.email "anonymous@example.com"
git add -A
git commit -m "Reproduction package for SBR/LARS 2026 submission"
```

Confirme antes de publicar:

```bash
git log --format='%an <%ae>' | sort -u     # deve mostrar só Anonymous
```

Se o pacote for um ZIP em vez de repositório, apague `.git/` de qualquer forma —
ele viaja junto sem que você perceba.

---

## 5. Verificação final, um comando

```bash
cd open-source
echo "--- identificadores ---"
grep -rIniE "robocin|ufpe|recife|pernambuco|natalnet|<seu sobrenome>|<seu usuário github>" . || echo ok
echo "--- caminhos e hashes ---"
grep -rIniE "sessions/happy|C:\\\\Users|/home/|rev-parse|commit [0-9a-f]{7}" . || echo ok
echo "--- metadados em imagens ---"
command -v exiftool >/dev/null && exiftool -Author -Creator -Software figures/*.png || echo "instale exiftool"
echo "--- autoria no git ---"
git log --format='%an <%ae>' | sort -u
```

Os PNGs merecem atenção: matplotlib grava `Software: Matplotlib` (inofensivo),
mas se alguma figura tiver passado por editor gráfico pode carregar seu nome.

---

## 6. No artigo

O `07_conclusion.tex` tem hoje um **placeholder que retorna 404**:
`https://github.com/anon-ssl-dt/behavioral-twin-ssl`. Um revisor da última
rodada verificou e registrou isso como objeção — enquanto der 404, o
pré-registro, o determinismo e a reconciliação com o Simulink ficam sem
verificação, e são justamente os argumentos de rigor do artigo. Troque pelo URL
real assim que existir.

---

## 7. Ordem de execução

1. Remover `phase0_replay/meeting_overlay.py` e `scripts/fig_spec_main_result.py`
2. Corrigir os caminhos absolutos (§2.1) e **rodar um script** para confirmar
3. Limpar hashes e `ssl-embedded` (§2.2)
4. Traduzir `docs/PREREGISTRO_OMEGA_20260724.md`
5. `rm -rf .git` e reinicializar com autor anônimo (§4)
6. Rodar a verificação final (§5)
7. Publicar e **abrir o URL numa janela anônima** para confirmar que responde
8. Colar o URL em `07_conclusion.tex` e recompilar
