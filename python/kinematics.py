import numpy as np # Opcional, mas facilita se quiser usar arrays no futuro

def compute(db):
    # --- 1. Leitura dos Inputs (do ROS/Simulink) ---
    # Vx e Vy são as velocidades lineares
    # W (aqui chamado de omega) é a velocidade angular
    vx = db.inputs.vx
    vy = db.inputs.vy
    omega = db.inputs.w 

    # --- 2. Definição da Matriz Kinematics.prod2 ---
    # Estou usando variáveis explícitas para facilitar a leitura 
    # e comparação visual com seu diagrama Simulink.
    
    # Linha 1 da matriz (Para a Roda 1)
    k1_1 = -34.990925405431859
    k1_2 =  20.2020202020202
    k1_3 =  3.324525253

    # Linha 2 da matriz (Para a Roda 2)
    k2_1 = -28.569970957032222
    k2_2 = -28.569970957032222
    k2_3 =  3.324525253

    # Linha 3 da matriz (Para a Roda 3)
    k3_1 =  28.569970957032222
    k3_2 = -28.569970957032222
    k3_3 =  3.324525253

    # Linha 4 da matriz (Para a Roda 4)
    k4_1 =  34.990925405431859
    k4_2 =  20.2020202020202
    k4_3 =  3.324525253

    # --- 3. Cálculo (A lógica dos blocos de soma e produto da imagem) ---
    # Equação: W_n = (K_n1 * Vx) + (K_n2 * Vy) + (K_n3 * Omega)
    
    w1 = (k1_1 * vx) + (k1_2 * vy) + (k1_3 * omega)
    w2 = (k2_1 * vx) + (k2_2 * vy) + (k2_3 * omega)
    w3 = (k3_1 * vx) + (k3_2 * vy) + (k3_3 * omega)
    w4 = (k4_1 * vx) + (k4_2 * vy) + (k4_3 * omega)

    # --- 4. Envio para os Outputs (Para o Articulation Controller) ---
    db.outputs.w1 = w1
    db.outputs.w2 = w2
    db.outputs.w3 = w3
    db.outputs.w4 = w4
    
    return True