# Extração de citáveis — SBR/LARS 2026 (fase 2, Agente 1 Bibliografia)

**Data:** 2026-07-31. **Fonte:** leitura direta dos 20 PDFs em `slr/pdfs/` (pdftotext, abstract + intro + conclusão; clássicos EXT: folha de rosto/copyright + trechos que sustentam a afirmação mapeada). Metadados **somente** do que está impresso no PDF; campos ausentes estão marcados. `.bib` correspondente: `latex/refs/references.bib` (20 entradas).

**† = mesmo grupo (UFPE/RobôCIn) — double-blind: citar SEMPRE em 3ª pessoa.**

---

## 1. `wiedemann2024simulation` — SLR-2024-Marvin-250.pdf

- **Metadados verificados:** M. Wiedemann, O. Ahmed, A. Dieckhöfer, R. Gasoto, S. Kerner. "Simulation Modeling of Highly Dynamic Omnidirectional Mobile Robots Based on Real-World Data". 2024 IEEE ICRA, Yokohama, Japão, maio 2024. DOI 10.1109/ICRA57147.2024.10611459. (Páginas não visíveis no PDF.)
- **Contribuição:** guideline de modelagem em simulação de um robô logístico omnidirecional (Mecanum) altamente dinâmico, com pipeline de comparação real×simulado via Motion Capture.
- **Método:** modelagem de colliders dos rolos, análise de parâmetros físicos de maior impacto, ajuste **manual** do modelo guiado por conhecimento de especialista sobre dados reais.
- **Resultado:** modelo reproduz comportamentos complexos (deslizamento) em baixa e alta dinâmica; colliders manuais superam malhas autogeradas.
- **Limitação (conclusão):** foi necessário um conjunto de parâmetros **distinto por trajetória** — mesmo com ajuste manual persiste gap sim-to-real significativo quando todas as dinâmicas são consideradas.
- **Sustenta:** Intro §1–2 e RW (B): modelagem de simulação de omnidirecionais dinâmicos a partir de dados reais — trabalho mais próximo. ✅ CONFIRMA (a limitação "um θ por trajetória" reforça o argumento do artigo sobre regime de excitação).

## 2. `wiedemann2025automated` — SLR-2025-Marvin-1071.pdf

- **Metadados verificados:** M. Wiedemann, O. Ahmed, M. Hatwar, R. Gasoto, P. Detzner, S. Kerner. "Automated Tuning of Non-Differentiable Rigid Body Simulation Models for Wheeled Mobile Robots". 2025 IEEE 21st CASE, Los Angeles, EUA, ago. 2025. DOI 10.1109/CASE58245.2025.11163879. (Venue estava "n/i" no Notion — agora verificado.)
- **Contribuição:** pipeline de tuning automático (black-box) de modelos de simulação não-diferenciáveis para robôs com rodas, usando erro sim-to-real sobre trajetórias reais.
- **Método:** otimização black-box sobre parâmetros do modelo; 4 robôs (diferencial, Ackermann, omnidirecional), múltiplas trajetórias e algoritmos.
- **Resultado:** tuning automático bem-sucedido; **poucos parâmetros de alto impacto dão melhor resultado do que ajustar muitos parâmetros pouco sensíveis**.
- **Limitação:** nem todos os erros sistemáticos são capturados (drift inicial em x não replicado); estudos mais amplos necessários.
- **Sustenta:** Método/Discussão: calibração automática de parâmetros ↔ análogo ao bayesopt de 9 params; RW (D). ✅ CONFIRMA (o achado "poucos parâmetros de alto impacto" dialoga com a ARD do bayesopt v2).

## 3. `giro2023otbot` — SLR-2023-Pere-3366.pdf

- **Metadados verificados:** P. Giró, E. Celaya, L. Ros (IRI, CSIC-UPC). "The Otbot Project: Dynamic modelling, parameter identification and motion control of an omnidirectional tire-wheeled robot". arXiv:2311.10834 [cs.RO], 17 nov. 2023 (documento datado maio 2021). **Preprint arXiv — sem venue/DOI de publicação no PDF.**
- **Contribuição:** modelo dinâmico completo (Lagrange) de robô omnidirecional de rodas convencionais (powered-caster), metodologia de identificação de parâmetros e controle computed-torque.
- **Método:** identificação por minimização de erro de predição em **sequência dedicada de 3 passos** (parâmetros básicos → chassi → plataforma), com experimentos projetados para excitar cada grupo.
- **Resultado:** parâmetros recuperados com acurácia e trajetórias rastreadas de forma robusta.
- **Limitação (lida na §4.3):** o robô físico **não estava disponível** — a identificação é validada em simulação com saídas sintéticas + ruído gaussiano plausível.
- **Sustenta:** RW (B): "ID em omnidirecionais assume experimento dedicado" — ✅ CONFIRMA fortemente (3 experimentos dedicados projetados por grupo de parâmetros), com a ressalva de validação apenas simulada.

## 4. `brennan2025greybox` — SLR-2024-Robert-002.pdf

- **Metadados verificados:** R. W. Brennan, J. Lesage (Univ. of Calgary). "Evaluating the use of grey-box system identification for digital twins in manufacturing automation". *International Journal of Computer Integrated Manufacturing*, vol. 38, no. 7, pp. 893–914, **2025** (online 30 set. 2024). DOI 10.1080/0951192X.2024.2386980. ⚠️ Notion dizia 2024; a citação canônica do próprio PDF é 2025.
- **Contribuição:** avaliação de identificação grey-box como módulo gerador de modelos de DT (réplica digital), equilibrando fidelidade × custo computacional.
- **Método:** manipulador robótico de 3 elos; módulo de sysid do DT avaliado sob perturbações de entrada; modelo usado depois nos módulos de simulação e monitoramento do DT.
- **Resultado:** o módulo grey-box é **propenso a erro e sensível a perturbações de entrada**, mas os modelos ainda predizem a resposta dinâmica com acurácia; uso em simulação/monitoramento viável **com certas limitações**.
- **Sustenta:** Intro §2 e RW (A/B): grey-box ID como via de construção de DTs. ✅ CONFIRMA (e a sensibilidade a perturbações de entrada é munição extra para a tese excitação-dependente).

## 5. `tiboni2023dropo` — SLR-2023-Tiboni-SB001.pdf

- **Metadados verificados:** G. Tiboni, K. Arndt, V. Kyrki. "DROPO: Sim-to-real transfer with offline domain randomization". *Robotics and Autonomous Systems* 166 (2023) 104432. DOI 10.1016/j.robot.2023.104432.
- **Contribuição:** método para estimar distribuições de domain randomization a partir de **dataset offline pré-coletado**, modelando explicitamente incerteza de parâmetros via verossimilhança.
- **Método:** otimização likelihood-based das distribuições de parâmetros dinâmicos; validação em recuperação de parâmetros em sim + dois transfers zero-shot reais (hockey puck, box pushing).
- **Resultado:** recupera distribuições de parâmetros, compensa parâmetro mal identificado e transfere políticas zero-shot com sucesso onde métodos anteriores falham.
- **Limitação (conclusão):** custo proibitivo em espaços de parâmetros grandes (>18 dim); escolha manual de quais parâmetros randomizar exige conhecimento de domínio.
- **Sustenta:** Intro §2 e Discussão: estimar parâmetros de simulador de dados offline já disponíveis ↔ logs de competição. ✅ CONFIRMA (paper-âncora do protocolo SLR).

## 6. `araujo2025digital` † — SLR-2025-Victor-849.pdf — **3ª PESSOA**

- **Metadados verificados:** V. Araújo, E. Barros (CIn/UFPE). "Digital Twin-based Architecture and Design for Co-simulation of Omnidirectional Mobile Robots". 2025 Latin American Robotics Symposium (LARS). DOI 10.1109/LARS69345.2025.11273010. (Páginas não visíveis no PDF.)
- **Contribuição:** arquitetura de DT em MATLAB/Simulink + Simscape Multibody para robô SSL omnidirecional 4 rodas, com CAD importado (geometria/inércia) e forças de contato.
- **Método:** cinemática + dinâmica multicorpo + contato; validação com trajetórias de situações de jogo de dataset SSL público.
- **Resultado:** RMSE de trajetória 150–240 mm; erro máximo de posição < 350 mm; desempenho quase tempo-real.
- **Sustenta:** Intro §1 e RW (A/D): DT de omnidirecional no contexto SSL — base que o presente artigo estende. ✅ CONFIRMA. **† citar como trabalho de terceiros.**

## 7. `yang2025digital` — SLR-2024-Hongjiu-762.pdf

- **Metadados verificados:** H. Yang, Z. Qin, Y. Xia, F. Cheng. "Digital Twin-Based Autonomous Navigation and Control of Omnidirectional Mobile Robots". *IEEE Transactions on Vehicular Technology*, vol. 74, no. 4, pp. 5687–5697, abr. **2025**. DOI 10.1109/TVT.2024.3520991. ⚠️ Notion dizia 2024; issue impressa é 2025.
- **Contribuição:** navegação autônoma e controle de OMR baseados em DT (4 dimensões: espaço físico, virtual, serviço, dados).
- **Método:** navegação no espaço virtual (A* + DWA) + sincronização de movimento físico-virtual com sliding mode integral.
- **Resultado:** erro de rastreamento de sincronização físico-virtual de 0.061 m em experimentos.
- **Sustenta:** RW (A): DT de robô omnidirecional (navegação/controle). ✅ CONFIRMA.

## 8. `barioni2024development` — SLR-2024-Wilson-782.pdf

- **Metadados verificados:** W. E. Barioni, I. P. Latini, C. T. S. Barioni, F. Neves-Jr, L. V. R. Arruda, M. Teixeira (UTFPR/PUCPR). "Development and Validation of a Digital Twin for a Commercial Mobile Robot". 2024 Eighth IEEE International Conference on Robotic Computing (IRC), p. 194 (início). DOI 10.1109/IRC63610.2024.00042.
- **Contribuição:** metodologia de DT para AGV comercial visando projetar e validar algoritmos de navegação/desvio de obstáculos antes do deploy físico.
- **Método:** modelo computacional do AGV em CoppeliaSim; algoritmos (PID, Fuzzy) projetados no gêmeo e comparados no robô real.
- **Resultado:** é possível usar o robô simulado para projetar algoritmos do robô real, economizando tempo e equipamento.
- **Sustenta:** RW (A): como a literatura valida fidelidade de DT de robô móvel. ✅ CONFIRMA (validação por comparação de comportamento sim×real, não por parâmetros).

## 9. `machado2025planning` † — SLR-2025-Mateus-2445.pdf — **3ª PESSOA**

- **Metadados verificados:** M. G. Machado, J. G. Melo, C. Zanchettin, P. H. Braga, P. V. Cunha, E. N. S. Barros, H. F. Bassani (CIn/UFPE). "Planning the Path with Reinforcement Learning: Optimal Robot Motion Planning in RoboCup Small Size League Environments".
- ⚠️ **METADADO INCOMPLETO:** o PDF é um preprint em formato Springer/LNCS **sem venue, ano ou DOI impressos** (pdfinfo: gerado em dez. 2024). Entrada `.bib` criada como `@misc` sem ano; completar venue/ano quando o usuário fornecer a versão publicada — **não preencher de memória**.
- **Contribuição:** metodologia model-free de path-planning com RL (políticas goal-conditioned que emitem sub-goals para o controle omnidirecional) no SSL.
- **Método:** RL hierárquico (goToPoint + path-planning) com controle heurístico; ablações em ambientes sem e com obstáculo.
- **Resultado:** ganho de 60% em tempo vs. baselines em ambiente livre; desvio de obstáculos dinâmicos.
- **Sustenta:** Intro §1: times SSL desenvolvem políticas em simulação (rSoccer/SSL); consequência do reality gap. ✅ CONFIRMA. **† citar como trabalho de terceiros.**

## 10. `melo2023dataset` † — SLR-2023-Joo-2435.pdf — **3ª PESSOA**

- **Metadados verificados:** J. G. Melo, L. Cavalcanti, R. Joaquim, V. Araújo, E. Barros (CIn/UFPE). "Dataset and Baseline Experiments for Self-Localization and Tracking in the RoboCup Small Size League". 2023 LARS/SBR/WRE. DOI 10.1109/LARS/SBR/WRE59448.2023.10333068. (6 páginas; numeração não visível.)
- **Contribuição:** dataset aberto para auto-localização/tracking SSL gravado a bordo, com baseline MCL e métricas.
- **Método:** 9 cenários com múltiplas trajetórias e velocidades; registra **poses ground-truth estimadas pelo ssl-vision, odometria e velocidades computadas onboard** (STM32F767ZI; Jetson Nano para gravação), + imagens da câmera onboard.
- **Resultado:** baseline MCL e de odometria avaliados no dataset com métricas para comparação futura.
- **Sustenta:** Discussão §E (Tema B): o que os logs SSL de fato registram (visão/pose/odometria) — ✅ CONFIRMA como evidência da *prática* de logging SSL. Nota: **não** afirma escassez de experimentos dedicados de ID (coerente com a decisão de reformular o Tema B). **† citar como trabalho de terceiros.**

## 11. `freiberger2024implementation` — SLR-2025-Andrei-2465.pdf

- **Metadados verificados:** A. Freiberger, M. R. O. A. Maximo, D. Loubach (ITA). "Implementation of Firmware Based on Real-time Operating System for Small Size League Robot". 2024 Brazilian Symposium on Robotics (SBR) and 2024 Workshop on Robotics in Education (WRE). DOI 10.1109/SBR/WRE63066.2024.10837771. ⚠️ Notion dizia 2025 (ano de indexação); o copyright do PDF é do SBR/WRE **2024**.
- **Contribuição:** firmware RTOS (FreeRTOS, STM32H753BI) para robô SSL com tarefas de controle de motores, kicker e telemetria em taxa constante.
- **Método (o que interessa ao artigo):** o comando de corpo recebido por rádio é convertido em **velocidades angulares por roda**; cada roda tem malha PI própria com estimativa de velocidade por sensores Hall (cálculo PI para as 4 rodas, ~50 µs); ruído na estimativa de velocidade de roda degrada o controle.
- **Resultado:** deadlines rígidos validados com analisador lógico.
- **Sustenta:** Resultados/Discussão: cadeia de atuação **por roda** no firmware SSL — ✅ CONFIRMA a estrutura da cadeia (corpo→roda→PI por roda) que fundamenta o mecanismo da zona morta elétrica por roda. Nota: o paper **não menciona explicitamente zona morta elétrica**; usar como suporte da arquitetura de atuação por roda, não do valor da zona morta.

## 12. `katyara2024benchmarking` — SLR-2025-Sunny-053.pdf

- **Metadados verificados:** S. Katyara, S. Sharma, P. Damacharla, C. Garcia-Santiago, L. Dhirani, B. S. Chowdhry. "Benchmarking Sim2Real Gap: High-fidelity Digital Twinning of Agile Manufacturing". Manuscrito de capítulo ("CHAPTER 2"), compilado 22 abr. 2024.
- ⚠️ **METADADO INCOMPLETO:** sem título do livro, editora, páginas ou DOI no PDF (arquivo Word do autor). Entrada `.bib` como `@misc` ano 2024. ⚠️ O PDF depositado corresponde na prática à versão **2024** (irmã SLR-2024-Sunny-046, "usar apenas uma das duas" — ok, só esta foi depositada).
- **Contribuição:** consolida tecnologias de DT para manufatura ágil e **avalia o gap sim2real com métricas práticas** (latência de dados, taxa de adaptação, fidelidade de simulação).
- **Método:** benchmarking de cenários (bin-picking, inspeção, montagem) sob domain randomization, adaptation, curriculum learning e model-based system identification.
- **Resultado:** avaliação comparativa das técnicas de transferência nos cenários industriais.
- **Sustenta:** Intro §1: definição/medição do sim2real gap com DTs de alta fidelidade — ✅ CONFIRMA, com ressalva de **domínio** (manufatura ágil/manipulação, não robôs móveis); usar como referência de definição/benchmark do gap, não de robô móvel.

## 13. `kosmaga2026digital` — SLR-2026-Shinta-855.pdf

- **Metadados verificados:** S. R. Kosmaga, A. Widyotriatmo, E. Rijanto, A. Hasan. "Digital twin-enabled real-time parameter estimation of a wheeled mobile robot". *Systems Science & Control Engineering*, vol. 14, no. 1, art. 2634459, 2026. DOI 10.1080/21642583.2026.2634459.
- **Contribuição:** framework de estimação de parâmetros em tempo real para WMR dentro de arquitetura de DT (observador adaptativo WyNDA), comparado com SINDy.
- **Método:** estimação de parâmetros estáticos e variantes no tempo em simulação e experimento; DT usado para tracking de posição durante perda de dados.
- **Resultado:** MAPE < 6.1% (sim) e ~10% (experimental), superando SINDy; erros de 3%/6% em x/y durante data loss.
- **Sustenta:** RW (A/B): estimação de parâmetros de robô móvel acoplada a DT. ✅ CONFIRMA.

## 14. `martins2021rsoccer` † — EXT-rsoccer-2021.pdf.pdf — **3ª PESSOA**

- **Metadados verificados:** F. B. Martins, M. G. Machado, H. F. Bassani, P. H. M. Braga, E. S. Barros (CIn/UFPE). "rSoccer: A Framework for Studying Reinforcement Learning in Small and Very Small Size Robot Soccer". arXiv:2106.12895 [cs.LG], 15 jun. 2021.
- ⚠️ O PDF depositado é a **versão arXiv**; a versão de anais (RoboCup 2021 Symposium, LNAI — citada no CANDIDATOS) **não** consta no PDF, portanto a entrada `.bib` cita o arXiv. Se preferir a versão LNAI, depositar esse PDF.
- **Contribuição:** framework OpenAI-Gym para RL em futebol de robôs SSL/VSSS + simulador **rSim** open-source.
- **Método (o que interessa ao artigo):** o rSim foi **derivado do grSim** ("devido à sua simulação física confiável"), removendo GUI e operando de forma síncrona/embarcada para RL — ou seja, herda a engine de física do grSim.
- **Resultado:** 8 ambientes-benchmark; demonstra aprendizagem com dois métodos SOTA e suas limitações.
- **Sustenta:** baseline do artigo (rSim/rSoccer, eixo d). ✅ CONFIRMA — inclusive documenta a linhagem rSim←grSim usada na descrição do baseline. **† citar como trabalho de terceiros.**

## 15. `monajjemi2012grsim` — EXT-grsim-2016.pdf.pdf

- **Metadados verificados:** V. Monajjemi, A. Koochakzadeh, S. Shiry Ghidary. "grSim — RoboCup Small Size Robot Soccer Simulator". In: T. Röfer et al. (Eds.), *RoboCup 2011: Robot Soccer World Cup XV*, LNCS 7416, pp. 450–460, Springer-Verlag, **2012**. ⚠️ CANDIDATOS dizia "2011/2016"; o PDF comprova LNCS 7416, 2012.
- **Contribuição:** simulador 3D multi-robô para SSL com arquitetura distribuída, substituindo todo o hardware durante o desenvolvimento de software.
- **Método (o que interessa ao artigo):** para reduzir complexidade e aumentar velocidade, implementa **modelo dinâmico simplificado das rodas omni** — exatamente o tipo de simplificação que o gêmeo comportamental do artigo confronta.
- **Resultado:** simulação em tempo real de partida SSL completa (física + visão + comandos).
- **Sustenta:** RW (D): simulador SSL de referência, origem da engine do rSim. ✅ CONFIRMA.

## 16. `forssell1999closedloop` — EXT-forssell-ljung-1999.pdf.pdf

- **Metadados verificados:** U. Forssell, L. Ljung (Linköping). "Closed-loop identification revisited". *Automatica* 35 (1999) 1215–1241. (Issue não impressa na página; CANDIDATOS diz no. 7 — não incluído no .bib por não constar no PDF.)
- **Contribuição:** estudo abrangente da identificação em malha fechada no framework de erro de predição, unificando métodos diretos/indiretos como parametrizações diferentes.
- **O que sustenta o \todocite (lido na §1.1):** "O problema fundamental com dados de malha fechada é a **correlação entre o ruído não-mensurável e a entrada**. Sempre que o controlador não é identicamente nulo, entrada e ruído serão correlacionados. É por isso que vários métodos que funcionam em malha aberta falham com dados de malha fechada."
- **Sustenta:** Discussão §B (Tema A) — núcleo do viés de correlação comando↔perturbação em ID direta sob realimentação. ✅ CONFIRMA (citação-núcleo).

## 17. `vandenhof1998closedloop` — EXT-vandenhof-1998.pdf.pdf

- **Metadados verificados:** P. Van den Hof (TU Delft). "Closed-loop issues in system identification". *Annual Reviews in Control* 22 (1998) 173–186.
- **Contribuição:** survey dos procedimentos de identificação com dados de malha fechada (extensões do PEM), comparando propriedades características, e do papel da closed-loop ID em identification-for-control.
- **O que sustenta:** revisa por que dados experimentais muitas vezes **só podem** ser obtidos em malha fechada (segurança/eficiência/instabilidade) e as propriedades de viés/variância resultantes.
- **Sustenta:** Discussão §B (Tema A) — survey de apoio. ✅ CONFIRMA.

## 18. `gustavsson1977identification` — EXT-gustavsson-1977.pdf.pdf

- **Metadados verificados:** I. Gustavsson, L. Ljung, T. Söderström. "Identification of processes in closed loop—identifiability and accuracy aspects" (Survey Paper). *Automatica*, vol. 13, pp. 59–75, 1977.
- **Contribuição:** survey clássico de identificabilidade e acurácia em malha fechada.
- **O que sustenta:** "tem havido confusão sobre as possibilidades de identificação bem-sucedida nesses casos, evidentemente porque **certos métodos comuns falham** [em malha fechada]"; mostra em quais configurações métodos de erro de predição diretos ainda dão estimativas corretas.
- **Sustenta:** Discussão §B (Tema A) — identificabilidade sob realimentação (clássico). ✅ CONFIRMA. Nota: o paper também argumenta que malha fechada *pode* ser favorável com o método/condições certos — citar com precisão (o problema do artigo é a ID direta com controlador desconhecido e excitação pobre, cenário coberto pelo survey).

## 19. `ljung1999system` — EXT-ljung-1999-book.pdf.pdf

- **Metadados verificados (folha de rosto/copyright):** L. Ljung. *System Identification: Theory for the User*, 2nd ed., Prentice Hall PTR, Upper Saddle River, NJ, 1999 (Prentice Hall Information and System Sciences Series). (ISBN não capturado no trecho lido.)
- **O que sustenta:** referência canônica de PEM (base do `procest`) e de **persistência de excitação** — fundamento teórico da tese "identificabilidade é função do regime de excitação".
- **Sustenta:** Método (origem do estimador) + Discussão §B. ✅ CONFIRMA.

## 20. `astrom1995pid` — EXT-astrom-hagglund-1995.pdf.pdf

- **Metadados verificados (copyright):** K. J. Åström, T. Hägglund. *PID Controllers: Theory, Design, and Tuning*, 2nd ed., Instrument Society of America, Research Triangle Park, NC, 1995. ISBN 1-55617-516-7.
- **O que sustenta:** referência clássica de modelos de processo de 1ª ordem com tempo morto (FOPDT) na prática de controle — origem da estrutura P1D usada por DOF.
- **Sustenta:** Método (estrutura FOPDT). ✅ CONFIRMA.

---

## Resumo de flags

| Flag | Papers |
|---|---|
| † 3ª pessoa (double-blind) | `araujo2025digital`, `machado2025planning`, `melo2023dataset`, **`martins2021rsoccer`** (também é do grupo — Martins/Machado/Bassani/Braga/Barros, CIn-UFPE) |
| Metadado incompleto no PDF | `machado2025planning` (sem venue/ano/DOI — preprint); `katyara2024benchmarking` (capítulo sem livro/editora/DOI); `martins2021rsoccer` (só versão arXiv; LNAI não verificável); `giro2023otbot` (preprint arXiv, sem venue) |
| Ano corrigido vs. Notion | `brennan2025greybox` (2024→2025), `yang2025digital` (2024→2025), `freiberger2024implementation` (2025→2024), `monajjemi2012grsim` (2016→2012) |
| Ressalva de escopo (sustenta com cuidado) | `katyara2024benchmarking` (domínio manufatura, não robô móvel); `freiberger2024implementation` (documenta cadeia por roda, **não** menciona zona morta elétrica); `melo2023dataset` (documenta prática de logging, **não** afirma escassez — Tema B já reformulado); `giro2023otbot` (identificação validada só em simulação) |
| NÃO SUSTENTA | — nenhum caso: todas as 20 leituras confirmaram a afirmação mapeada (com as ressalvas acima) |
