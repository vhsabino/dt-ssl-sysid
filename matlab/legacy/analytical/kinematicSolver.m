function [w1, w2, w3, w4] = kinematic_solver(action, vx, vy, omega)
% --- ZONAS MORTAS ---
if abs(vx) < 0.1, vx = 0; end
if abs(vy) < 0.1, vy = 0; end
if abs(omega) < 0.3, omega = 0; end

% --- AS 4 CONSTANTES TEÓRICAS BASE ---
% Esses valores funcionam como o "zero" do seu espaço de busca
K1_base = 29.36475667;
K2_base = 16.95375017;
K3_base = 23.97622342;
K4_base = 2.699070934;

%K1_base = -34.990925405431859; 
%K2_base =  20.2020202020202;   
%K3_base =  3.324525253;
%K4_base = -28.569970957032222;  
%K5_base = -28.569970957032222; 
%K6_base =  3.324525253;   
%K7_base =  28.569970957032222; 
%K8_base = -28.569970957032222;
%K9_base =  3.324525253;
%K10_base = 34.990925405431859;   
%K11_base = 20.2020202020202;  
%K12_base = 3.324525253;  

% --- APLICAÇÃO DO DELTA DO PSO ---
% O PSO entrega um vetor 'action' de 1x4 com valores em torno de 0.
% Multiplicamos por (1 + delta) para ajustar as grandezas físicas reais.
K1 = K1_base * (1 + action(1));
K2 = K2_base * (1 + action(2));
K3 = K3_base * (1 + action(3));
K4 = K4_base * (1 + action(4));
%K5 = K5_base * (1 + action(5));
%K6 = K6_base * (1 + action(6));
%K7 = K7_base * (1 + action(7));
%K8 = K8_base * (1 + action(8));
%K9 = K9_base * (1 + action(9));
%K10 = K10_base * (1 + action(10));
%K11 = K11_base * (1 + action(11));
%K12 = K12_base * (1 + action(12));

% --- RECONSTRUÇÃO DA MATRIZ CINEMÁTICA ---
% Mapeia as 4 constantes calibradas de volta para as 12 posições
K = [
    -K1,  K2,  K4; % Roda 1
    -K3, -K3,  K4; % Roda 2
    K3, -K3,  K4; % Roda 3
    K1,  K2,  K4  % Roda 4
    ];

%K = [
%    K1,  K2,  K3; % Roda 1
%    K4,  K5,  K6; % Roda 2
%    K7,  K8,  K9; % Roda 3
%    K10,  K11,  K12  % Roda 4
%    ];


% --- CÁLCULO DAS VELOCIDADES DAS RODAS ---
inputs = [vx; vy; omega];
wheels = K * inputs;

% Assinalamento
w1 = wheels(1);
w2 = wheels(2);
w3 = wheels(3);
w4 = wheels(4);
end