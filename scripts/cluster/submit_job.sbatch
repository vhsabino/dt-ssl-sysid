#!/bin/bash
#SBATCH --job-name=digitaltwin_train
#SBATCH --output=logs/output_%j.txt    # Log de saída (crie a pasta logs antes!)
#SBATCH --error=logs/error_%j.txt      # Log de erro
#SBATCH --nodes=1                      # 1 máquina
#SBATCH --ntasks-per-node=1            # 1 tarefa
#SBATCH --cpus-per-task=8              # 8 CPUs (ajuste conforme necessário)
#SBATCH --gres=gpu:1                   # 1 GPU (O Slurm vai te dar uma 3090 ou A100)
#SBATCH --partition=gpu                # Partição de GPU (verificar nome exato no cluster)
#SBATCH --time=24:00:00                # Tempo máximo (24 horas)

# 1. Carregar módulos necessários (Verifique no cluster com 'module avail')
module load cuda/11.8  # Exemplo, ajuste para a versão do Isaac Sim
module load python/3.10

# 2. Ativar seu ambiente virtual (Crie isso no cluster na primeira vez)
source ~/envs/digitaltwin/bin/activate

# 3. Definir variáveis do Isaac Sim (Modo Headless é OBRIGATÓRIO)
# Isso impede que o Isaac tente abrir janelas e trave o job
export OMNI_KIT_ALLOW_ROOT=1 # Às vezes necessário em container, talvez não no cluster direto
export DISPLAY= 

# 4. Rodar o treino
# 'python -u' para o print aparecer no log em tempo real (unbuffered)
echo "Iniciando treinamento no host: $(hostname)"
python -u src/train_agent.py --headless --video --checkpoint_dir $SCRATCH/checkpoints