figure;

% Extraindo o .Data para o Gêmeo Digital
plot(out.pos_x_out.Data, out.pos_y_out.Data, 'b-', 'LineWidth', 1.5); 
hold on;

% Extraindo o .Data para o Log Real (Ground Truth)
% Corrigido para usar o X no primeiro argumento
plot(out.pos_x_truth_out.Data, out.pos_y_truth_out.Data, 'r.', 'LineWidth', 2.5);

legend('Gêmeo Digital', 'Log Real (Ground Truth)');
xlabel('X (metros)'); 
ylabel('Y (metros)');
title('Validação de Trajetória: Sim-to-Real');
axis equal; 
grid on;