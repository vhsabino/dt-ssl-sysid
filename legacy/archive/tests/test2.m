% Verifica se o sinal do modelo está em body ou world
% Compara também com std do comando bruto
fprintf('std(cmd_vx body)         = %.3f\n', std(cmd_vx_ts.Data));
fprintf('std(cmd_vy body)         = %.3f\n', std(cmd_vy_ts.Data));
fprintf('std(v_y modelo)          = %.3f  <-- está saindo do FK\n', std(out.vy_out));
fprintf('std(vy_world real)       = %.3f  <-- derivada da pose world\n', std(vy_world_real));
fprintf('std(cmd_vy world rotac.) = %.3f  <-- cmd body rotacionado\n', std(cmd_vy_world));