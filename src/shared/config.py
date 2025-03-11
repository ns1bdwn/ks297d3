# src/shared/config.py
"""
Configurações globais do Regulatory Suite.
"""
import os
from pathlib import Path

# Diretórios principais
ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = os.path.join(ROOT_DIR, "src")
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Subdiretórios de dados
CLIENT_DATA_DIR = os.path.join(DATA_DIR, "clients")
MODEL_DIR = os.path.join(DATA_DIR, "models")
REGULATION_DIR = os.path.join(DATA_DIR, "regulations")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")

# Configurações de modelo de IA
MODELS = {
    "legal_bert": {
        "name": "legal-bert-base-cased-ptbr",
        "source": "dominguesm/legal-bert-base-cased-ptbr"
    },
    "jurisbert": {
        "name": "jurisbert-base-portuguese-sts",
        "source": "alfaneo/jurisbert-base-portuguese-sts"
    }
}

# Setores de monitoramento
SECTORS = [
    "iGaming",
    "Meios de Pagamento",
    "Digital Assets"
]

# Frameworks e pesos
FRAMEWORKS = {
    "COSO ERM": {"weight": 0.50, "color": "#366092"},
    "IBGC": {"weight": 0.20, "color": "#70AD47"},
    "ISO 31000": {"weight": 0.20, "color": "#ED7D31"},
    "AIR": {"weight": 0.10, "color": "#4472C4"}
}

# Dimensões de avaliação
DIMENSIONS = {
    "Governança": "Estrutura e processos para direcionar e supervisionar",
    "Cultura": "Valores, atitudes e comportamentos em relação à regulação",
    "Estratégia": "Direcionamento de longo prazo para gestão regulatória",
    "Riscos": "Identificação, avaliação e tratamento de riscos",
    "Compliance": "Aderência a normas e requisitos regulatórios",
    "Advocacy": "Influência e participação no processo regulatório",
    "Tecnologia": "Uso de recursos tecnológicos para gestão regulatória"
}

# Criação de diretórios necessários
def ensure_directories():
    """Garante que todos os diretórios necessários existem."""
    for directory in [CLIENT_DATA_DIR, MODEL_DIR, REGULATION_DIR, BACKUP_DIR]:
        os.makedirs(directory, exist_ok=True)
    
    # Criar diretórios de módulos src se não existirem
    module_dirs = [
        os.path.join(SRC_DIR, "maturity"),
        os.path.join(SRC_DIR, "intelligence"),
        os.path.join(SRC_DIR, "intelligence", "utils"),
        os.path.join(SRC_DIR, "intelligence", "analyzers"),
        os.path.join(SRC_DIR, "intelligence", "collectors"),
        os.path.join(SRC_DIR, "shared"),
        os.path.join(SRC_DIR, "ui"),
        os.path.join(SRC_DIR, "reporting")
    ]
    
    for directory in module_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            # Criar arquivo __init__.py para garantir que é um módulo válido
            init_file = os.path.join(directory, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, "w") as f:
                    f.write("# Arquivo de inicialização do módulo\n")

# Garante que diretórios existem ao importar o módulo
ensure_directories()