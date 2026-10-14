function [v_global_x, v_global_y] = local2global(vx, vy, theta)
% Matriz de Rotação 2D
c = cos(theta);
s = sin(theta);

% Rotação
v_global_x = vx * c - vy * s;
v_global_y = vx * s + vy * c;
end