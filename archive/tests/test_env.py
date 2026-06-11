# scripts/local/test_env.py
import argparse
from pathlib import Path
import os

# Simulação básica (Exemplo genérico)
def main():
    print(f"Iniciando simulação no sistema: {os.name}")
    
    # Exemplo de como carregar um asset usando caminho relativo
    # Funciona tanto no Windows quanto no Linux do Cluster
    asset_path = Path(__file__).parent.parent.parent / "assets" / "robots" / "robot.usd"
    
    print(f"Procurando robô em: {asset_path}")
    
    if asset_path.exists():
        print("Asset encontrado!")
    else:
        print("Aviso: Asset ainda não criado.")

    # código do Isaac Sim
    # from omni.isaac.kit import SimulationApp...
    
    print("Teste finalizado com sucesso.")

if __name__ == "__main__":
    main()