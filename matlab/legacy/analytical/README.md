# `analytical/` — cinemática de rodas em MATLAB (ARQUIVADO como referência)

Era `matlab/analytical/`. Cópias standalone das fórmulas embutidas nos charts Stateflow dos `.slx`
(ver CHANGELOG 2026-07-24 16:00, item 3: as 8 cópias em `.slx` ainda usam `K4=3.324525253`).

| Script | Papel | Estado |
|---|---|---|
| `kinematicSolver.m` | cinemática **inversa** corpo→rodas com zonas mortas (`|vx|,|vy|<0.1`, `|ω|<0.3` — herança sem fonte, CHANGELOG 2026-07-24 19:35 Parte D) e constantes base K1..K4 (K4 corrigido manualmente para `2.699070934` = R/r do CAD) | referência; zona morta removida do `pid_v3` em `eb97620` (2026-06-11) |
| `inverse_kinematics_solver.m` | matriz `K_inv` (pseudo-inversa rodas→corpo) | **correta**: CHANGELOG 2026-08-10 (R1 encerrado — a assimetria √2 entre rodas {1,4}/{2,3} na linha ω é a pinv correta para φ=[60,135,225,300]°); refuta as suspeitas de 2026-07-24 13:00 e 2026-08-09 |
| `local2global.m` | rotação corpo→mundo | trivial |

Porte Python vivo: `dtssl.kinematics` (`body_to_wheel_matrix`, `wheel_to_body_matrix`, `local_to_global`,
`apply_wheel_deadzone`), verificado contra `kinematicSolver.m` (1e-6) e contra o `K_inv` literal (2e-11);
geometria em `config/robot_geometry.json` (`physical`: R=0,079601 m, r=0,029492 m, φ=[60,135,225,300]°).
