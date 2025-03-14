"""
Gerenciador para modelos de IA usados na análise avançada.
"""
import os
import logging
from typing import Dict, Any, Optional
import importlib.util

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("model_manager")

class ModelManager:
    """
    Gerencia o carregamento e utilização de modelos de IA.
    Implementa verificação de disponibilidade e fallback para métodos baseados em regras.
    """
    
    # Mapeamento de modelos disponíveis
    MODELS = {
        "legal_bert": {
            "name": "legal-bert-base-cased-ptbr",
            "path": "dominguesm/legal-bert-base-cased-ptbr",
            "type": "bert"
        },
        "legal_bert_ner": {
            "name": "legal-bert-ner-base-cased-ptbr",
            "path": "dominguesm/legal-bert-ner-base-cased-ptbr",
            "type": "bert_ner"
        },
        "jurisbert_sts": {
            "name": "jurisbert-base-portuguese-sts",
            "path": "alfaneo/jurisbert-base-portuguese-sts",
            "type": "bert"
        },
        "jurisbert_uncased": {
            "name": "jurisbert-base-portuguese-uncased",
            "path": "alfaneo/jurisbert-base-portuguese-uncased",
            "type": "bert"
        },
        "bertimbau": {
            "name": "bert-large-portuguese-cased",
            "path": "neuralmind/bert-large-portuguese-cased",
            "type": "bert"
        },
        "ptt5": {
            "name": "ptt5-large-portuguese-vocab",
            "path": "unicamp-dl/ptt5-large-portuguese-vocab",
            "type": "t5"
        }
    }
    
    def __init__(self, models_dir: str = None):
        """
        Inicializa o gerenciador de modelos.
        
        Args:
            models_dir: Diretório para armazenar modelos. Se None, usa o padrão.
        """
        if models_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(script_dir, "../../../.."))
            self.models_dir = os.path.join(project_root, "data", "models")
        else:
            self.models_dir = models_dir
        
        # Garantir que o diretório existe
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Dicionário para armazenar modelos carregados
        self.loaded_models = {}
        
        # Verificar disponibilidade de dependências
        self.dependencies_available = self._check_dependencies()
    
    def _check_dependencies(self) -> Dict[str, bool]:
        """
        Verifica se as dependências para os modelos estão disponíveis.
        
        Returns:
            Dicionário com status de disponibilidade de cada dependência
        """
        dependencies = {
            "transformers": False,
            "torch": False,
            "sentencepiece": False,
            "tokenizers": False
        }
        
        # Verificar transformers
        if importlib.util.find_spec("transformers") is not None:
            dependencies["transformers"] = True
        
        # Verificar torch
        if importlib.util.find_spec("torch") is not None:
            dependencies["torch"] = True
        
        # Verificar sentencepiece (para T5)
        if importlib.util.find_spec("sentencepiece") is not None:
            dependencies["sentencepiece"] = True
        
        # Verificar tokenizers
        if importlib.util.find_spec("tokenizers") is not None:
            dependencies["tokenizers"] = True
        
        logger.info(f"Status das dependências: {dependencies}")
        return dependencies
    
    def is_available(self, model_key: str) -> bool:
        """
        Verifica se um modelo específico está disponível para uso.
        
        Args:
            model_key: Chave do modelo no dicionário MODELS
            
        Returns:
            True se o modelo estiver disponível, False caso contrário
        """
        # Verificar se o modelo existe
        if model_key not in self.MODELS:
            logger.warning(f"Modelo '{model_key}' não encontrado na lista de modelos disponíveis")
            return False
        
        # Verificar dependências necessárias
        model_type = self.MODELS[model_key]["type"]
        if model_type == "bert" or model_type == "bert_ner":
            if not (self.dependencies_available["transformers"] and self.dependencies_available["torch"]):
                logger.warning(f"Dependências para modelo {model_key} não disponíveis")
                return False
        elif model_type == "t5":
            if not (self.dependencies_available["transformers"] and self.dependencies_available["torch"] and 
                    self.dependencies_available["sentencepiece"]):
                logger.warning(f"Dependências para modelo {model_key} não disponíveis")
                return False
        
        # Verificar se o modelo está em disco
        model_path = os.path.join(self.models_dir, self.MODELS[model_key]["name"])
        if not os.path.exists(model_path):
            logger.warning(f"Modelo {model_key} não encontrado em disco: {model_path}")
            return False
        
        return True
    
    def load_model(self, model_key: str) -> Any:
        """
        Carrega um modelo específico em memória.
        
        Args:
            model_key: Chave do modelo no dicionário MODELS
            
        Returns:
            Modelo carregado ou None se não for possível carregar
        """
        # Verificar se já está carregado
        if model_key in self.loaded_models:
            return self.loaded_models[model_key]
        
        # Verificar disponibilidade
        if not self.is_available(model_key):
            logger.error(f"Modelo {model_key} não está disponível")
            return None
        
        try:
            model_type = self.MODELS[model_key]["type"]
            model_path = os.path.join(self.models_dir, self.MODELS[model_key]["name"])
            
            if model_type == "bert":
                from transformers import AutoTokenizer, AutoModel
                tokenizer = AutoTokenizer.from_pretrained(model_path)
                model = AutoModel.from_pretrained(model_path)
                self.loaded_models[model_key] = {
                    "tokenizer": tokenizer,
                    "model": model
                }
            elif model_type == "bert_ner":
                from transformers import AutoTokenizer, AutoModelForTokenClassification
                tokenizer = AutoTokenizer.from_pretrained(model_path)
                model = AutoModelForTokenClassification.from_pretrained(model_path)
                self.loaded_models[model_key] = {
                    "tokenizer": tokenizer,
                    "model": model
                }
            elif model_type == "t5":
                from transformers import T5Tokenizer, T5ForConditionalGeneration
                tokenizer = T5Tokenizer.from_pretrained(model_path)
                model = T5ForConditionalGeneration.from_pretrained(model_path)
                self.loaded_models[model_key] = {
                    "tokenizer": tokenizer,
                    "model": model
                }
            else:
                logger.error(f"Tipo de modelo {model_type} não suportado")
                return None
            
            logger.info(f"Modelo {model_key} carregado com sucesso")
            return self.loaded_models[model_key]
        except Exception as e:
            logger.error(f"Erro ao carregar modelo {model_key}: {str(e)}")
            return None
    
    def unload_model(self, model_key: str) -> bool:
        """
        Descarrega um modelo da memória.
        
        Args:
            model_key: Chave do modelo no dicionário MODELS
            
        Returns:
            True se o modelo foi descarregado, False caso contrário
        """
        if model_key in self.loaded_models:
            try:
                # Remover referências ao modelo
                del self.loaded_models[model_key]
                # Sugerir coleta de lixo
                import gc
                gc.collect()
                logger.info(f"Modelo {model_key} descarregado com sucesso")
                return True
            except Exception as e:
                logger.error(f"Erro ao descarregar modelo {model_key}: {str(e)}")
                return False
        
        return False