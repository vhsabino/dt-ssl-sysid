function [vx, vy, omega] = inverse_kinematics_solver(w1, w2, w3, w4)
% --- MATRIZ DE CINEMÁTICA INVERSA ---
% --- CÁLCULO DA MATRIZ INVERSA (Pseudo-Inversa) ---
K_inv = [
    -0.008573651497466, -0.007000357133747, 0.007000357133747, ...
    0.008573651497466;
    0.010251785668734, -0.010251785668734, -0.010251785668734, ... 
    0.010251785668734;
    0.088100765229306, 0.062296648521366, 0.062296648521366, ...
    0.088100765229306
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