# Outline do Artigo (IMRaD) — alvo: JINT ou MDPI Robotics/Sensors

Título (rascunho): "Behavioral Digital Twin of an Omnidirectional
RoboCup SSL Robot via Per-DOF Grey-Box Identification from
Closed-Loop Competition Logs"

1. Introduction — reality gap em SSL; por que logs de competição;
   contribuições C1-C3 (de docs/01_definicao_pesquisa.md).
2. Related Work — saída da SLR/mapping: DT de robôs móveis;
   identificação em malha fechada; simuladores SSL (benchmark grSim).
3. Methodology — G_i(s)=K/(τs+1)e^(-Td·s) por DOF; pipeline de dados
   (protobuf→splits→Savitzky-Golay); procest baseline; bayesopt com
   custo RMSE multi-horizonte.
4. Experimental Setup — robô 2025, logs, métricas, protocolo de
   validação (hold-out de splits), critérios de aceite.
5. Results — FIGURA CENTRAL (RMSE×horizonte×modelo); tabela mestra;
   análise por DOF; identificabilidade de Td; whiteness (Ljung-Box).
6. Discussion — limitações (excitação em malha fechada); ameaças à
   validade; comparação com grSim.
7. Conclusion + future work (coleta dedicada de rotação; vertente RL).

Checklist de submissão: declaração de uso de IA • dados/código
(DVC + repo público se permitido) • ORCID • carta de apresentação.
