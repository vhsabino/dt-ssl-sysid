# Protocolo SLR — versão "light" Kitchenham (§9, pesquisador único)

> Base: Kitchenham & Charters (2007), EBSE-2007-01. Adaptações de pesquisador único: triagem assistida por IA com revisão humana de amostra (test-retest) + arbitragem do orientador nos casos DÚVIDA.

## 1. Questões da revisão (alinhadas às QPs da tese)
- **QR1:** Quais abordagens de modelagem/identificação são usadas para construir gêmeos digitais ou simuladores de alta fidelidade de robôs móveis omnidirecionais?
- **QR2:** Como "fidelidade" é definida e medida (métricas, horizontes, validação)?
- **QR3:** Quais trabalhos identificam dinâmica a partir de dados em malha fechada / logs operacionais, e como tratam excitação e atraso de transporte?

## 2. PICOC
| | |
|---|---|
| **P**opulação | Robôs móveis com rodas (foco: omnidirecionais; RoboCup SSL incluído) |
| **I**ntervenção | Identificação grey-box / calibração de simulador / construção de digital twin |
| **C**omparação | Modelos físicos white-box, black-box (NN), cinemática ideal |
| **O**utcome | Fidelidade comportamental: RMSE de trajetória, fit%, reality gap |
| **C**ontexto | Dados de operação/competição (malha fechada), robótica móvel |

## 3. Estratégia de busca
**Bases:** Scopus, IEEE Xplore, ACM DL, Web of Science. **Literatura cinzenta (sinalizada):** TDPs/ETDPs RoboCup (TIGERs, Twente etc.) por busca manual + snowballing dos incluídos (frente e trás, 1 nível).

**String mestra (adaptar por base):**
```
("digital twin" OR "system identification" OR "grey-box" OR "gray-box"
  OR "simulator calibration" OR "model calibration")
AND ("omnidirectional" OR "omni-directional" OR "mobile robot"
  OR "wheeled robot" OR "RoboCup")
AND ("fidelity" OR "sim-to-real" OR "reality gap" OR "validation"
  OR "transfer")
```
Período: 2010–2026. Idiomas: EN, PT. Documentar por base: data, string exata, nº de retornos (Tabela 2 de Kitchenham).

## 4. Critérios de seleção
**Inclusão:** (I1) identifica/calibra modelo dinâmico de robô móvel com dados reais; (I2) reporta métrica de fidelidade ou validação experimental; (I3) peer-reviewed (TDPs entram como cinzenta, marcados).
**Exclusão:** (E1) manipuladores/humanoides sem base móvel; (E2) DT de manufatura/processo sem robô; (E3) só simulação, sem dado real; (E4) sem acesso ao texto completo; (E5) duplicata (manter versão mais completa).

## 5. Processo de seleção (2 fases)
- **Fase 1 (título+resumo):** Claude Cowork aplica I/E e preenche `triagem.csv` com decisão+motivo; casos ambíguos → `DUVIDA`. **Você** revisa: todos os `DUVIDA` + amostra aleatória de 15% (test-retest; reporte a concordância). Divergências → orientador.
- **Fase 2 (texto completo):** leitura **sua** dos candidatos; Claude extrai dados para você conferir.

## 6. Avaliação de qualidade (por primário, escala Y=1/P=0.5/N=0)
Q1 objetivo claro? Q2 plataforma e dados descritos? Q3 método de identificação reprodutível? Q4 validação com dado independente (hold-out)? Q5 limitações discutidas?

## 7. Formulário de extração
ID; ref; ano; plataforma (tipo de robô); estrutura do modelo (ordem, delay?); método de identificação; tipo de dado (malha aberta/fechada, dedicado/operacional); métrica de fidelidade; horizonte de validação; trata excitação? trata delay?; resultado principal; score de qualidade; notas.

## 8. Síntese
Narrativa + tabelas por QR; mapa "estrutura de modelo × tipo de dado × métrica" para evidenciar a lacuna (logs de malha fechada + delay). Sem meta-análise (heterogeneidade esperada).

## 9. Cronograma e declaração
Busca+dedup: S2 • Fase 1: S3 • Fase 2+extração: S4–5 • Síntese: S5. Uso de IA na triagem declarado na seção de método da revisão.
