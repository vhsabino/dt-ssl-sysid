function [vx, vy, omega] = inverse_kinematics_solver(w1, w2, w3, w4)
% --- MATRIZ DE CINEMÁTICA INVERSA ---
% --- CÁLCULO DA MATRIZ INVERSA (Pseudo-Inversa) ---
K_inv = [
    -0.010216328484506,	-0.008341597276945,	0.008341597276945,	0.010216328484506;
    0.012215986382218,	-0.012215986382218,	-0.012215986382218,	0.012215986382218;
    0.108516310225934,	0.076732618841300,	0.076732618841300,	0.108516310225934
];
% Vetor de entrada (Velocidades Lidas dos Encoders)
wheels = [w1; w2; w3; w4];

% Cálculo: Velocidades do Corpo = Matriz_Inv * Velocidades_Rodas
vels = K_inv * wheels;

% Separa as saídas
vx = vels(1);
vy = vels(2);
omega = vels(3);

% não aplicamos Deadzone na Odometria (inversa),
% pois queremos saber se o robô está deslizando minimamente.
end