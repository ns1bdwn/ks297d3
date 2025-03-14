"""
Gerenciador para modelos de IA usados na análise avançada.
"""
import os
import json
import logging
from typing import Dict, Any, Optional

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
        "bertimbau_large": {
            "name": "bert-large-portuguese-cased",
            "path": "neuralmind/bert-large-portuguese-cased",
            "type": "bert"
        },
        "mt5": {
            "name": "ptt5-large-portuguese-vocab",
            "path": "unicamp-dl/ptt5-large-portuguese-vocab",
            "type": "t5"
        }
    }
    
    # Mapeamento reverso para permitir busca pelo nome completo do modelo
    NAME_TO_KEY = {info["name"]: key for key, info in MODELS.items()}
    
    # Nomes alternativas para modelos (para compatibilidade com arquivos existentes)
    ALT_NAMES = {
        "dominguesm_legal-bert-base-cased-ptbr": "legal_bert",
        "dominguesm_legal-bert-ner-base-cased-ptbr": "legal_bert_ner",
        "alfaneo_jurisbert-base-portuguese-sts": "jurisbert_sts",
        "alfaneo_jurisbert-base-portuguese-uncased": "jurisbert_uncased",
        "neuralmind_bert-large-portuguese-cased": "bertimbau_large",
        "unicamp-dl_ptt5-large-portuguese-vocab": "mt5"
    }
    
    def __init__(self, models_dir: str = None):
        """
        Inicializa o gerenciador de modelos.
        
        Args:
            models_dir: Diretório para armazenar modelos. Se None, usa o padrão.
        """
        if models_dir is None:
            # Usar caminho absoluto relativo ao script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(script_dir, "../../../.."))
            self.models_dir = os.path.join(project_root, "data", "models")
            logger.info(f"Diretório de modelos configurado: {self.models_dir}")
        else:
            self.models_dir = models_dir
        
        # Garantir que o diretório existe
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Dicionário para armazenar modelos carregados
        self.loaded_models = {}
        
        # Verificar disponibilidade de dependências
        self.dependencies_available = self._check_dependencies()
        
        # Verificar status de instalação dos modelos
        self.installed_versions = self._load_installed_versions()
    
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
        try:
            import importlib.util
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
        except Exception as e:
            logger.error(f"Erro ao verificar dependências: {str(e)}")
        
        return dependencies
    
    def _load_installed_versions(self) -> Dict[str, Dict[str, Any]]:
        """
        Carrega informações sobre modelos instalados.
        
        Returns:
            Dicionário com informações sobre modelos instalados
        """
        # Verificar arquivo de status de modelos
        versions_file = os.path.join(self.models_dir, "model_status.json")
        
        if os.path.exists(versions_file):
            try:
                with open(versions_file, "r", encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar status de modelos: {str(e)}")
        
        # Se não conseguir carregar, verificar diretamente no disco
        installed = {}
        
        # Verificar cada modelo diretamente
        for model_key, model_info in self.MODELS.items():
            model_name = model_info["name"]
            
            # Caminhos possíveis para o modelo
            model_paths = [
                os.path.join(self.models_dir, model_name),
                os.path.join(self.models_dir, model_info["path"].replace("/", "_"))
            ]
            
            # Verificar se algum dos caminhos existe
            model_path = None
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    break
            
            if model_path:
                installed[model_key] = {
                    "version": "1.0",
                    "path": model_path
                }
        
        logger.info(f"Modelos instalados encontrados: {list(installed.keys())}")
        return installed
    
    def is_available(self, model_key: str) -> bool:
        """
        Verifica se um modelo específico está disponível para uso.
        
        Args:
            model_key: Chave do modelo no dicionário MODELS
            
        Returns:
            True se o modelo estiver disponível, False caso contrário
        """
        # Resolver chave do modelo se for um nome alternativo
        if model_key in self.ALT_NAMES:
            model_key = self.ALT_NAMES[model_key]
        elif model_key in self.NAME_TO_KEY:
            model_key = self.NAME_TO_KEY[model_key]
        
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
        
        # Verificar se o modelo está instalado
        if model_key in self.installed_versions:
            model_path = self.installed_versions[model_key].get("path", "")
            if model_path and os.path.exists(model_path):
                return True
        
        # Se não está no arquivo de status, verificar no disco
        model_info = self.MODELS[model_key]
        model_name = model_info["name"]
        safe_path = model_info["path"].replace("/", "_")
        
        # Verificar possíveis caminhos
        model_paths = [
            os.path.join(self.models_dir, model_name),
            os.path.join(self.models_dir, safe_path)
        ]
        
        for path in model_paths:
            if os.path.exists(path):
                # Atualizar informações de instalação
                self.installed_versions[model_key] = {
                    "version": "1.0",
                    "path": path
                }
                return True
        
        logger.warning(f"Modelo {model_key} não encontrado em disco")
        return False
    
    def get_model_path(self, model_key: str) -> str:
        """
        Obtém o caminho do modelo no disco.
        
        Args:
            model_key: Chave do modelo
            
        Returns:
            Caminho do modelo no disco
        """
        # Resolver chave do modelo se for um nome alternativo
        if model_key in self.ALT_NAMES:
            model_key = self.ALT_NAMES[model_key]
        elif model_key in self.NAME_TO_KEY:
            model_key = self.NAME_TO_KEY[model_key]
        
        # Verificar se o modelo está registrado como instalado
        if model_key in self.installed_versions:
            return self.installed_versions[model_key].get("path", "")
        
        # Se não estiver, verificar possíveis caminhos
        model_info = self.MODELS.get(model_key, {})
        if not model_info:
            logger.error(f"Modelo '{model_key}' não encontrado na lista de modelos disponíveis")
            return ""
        
        model_name = model_info.get("name", "")
        safe_path = model_info.get("path", "").replace("/", "_")
        
        # Verificar possíveis caminhos
        model_paths = [
            os.path.join(self.models_dir, model_name),
            os.path.join(self.models_dir, safe_path)
        ]
        
        for path in model_paths:
            if os.path.exists(path):
                return path
        
        return ""
    
    def load_model(self, model_key: str) -> Optional[Dict[str, Any]]:
        """
        Carrega um modelo específico em memória.
        
        Args:
            model_key: Chave do modelo no dicionário MODELS
            
        Returns:
            Dicionário com tokenizer e modelo carregados ou None se não for possível carregar
        """
        # Resolver chave do modelo se for um nome alternativo
        if model_key in self.ALT_NAMES:
            model_key = self.ALT_NAMES[model_key]
        elif model_key in self.NAME_TO_KEY:
            model_key = self.NAME_TO_KEY[model_key]
        
        # Verificar se já está carregado
        if model_key in self.loaded_models:
            logger.info(f"Usando modelo {model_key} já carregado em memória")
            return self.loaded_models[model_key]
        
        # Verificar disponibilidade
        if not self.is_available(model_key):
            logger.error(f"Modelo {model_key} não está disponível")
            return None
        
        # Obter caminho do modelo
        model_path = self.get_model_path(model_key)
        if not model_path:
            logger.error(f"Não foi possível determinar o caminho do modelo {model_key}")
            return None
        
        try:
            model_type = self.MODELS[model_key]["type"]
            
            if model_type == "bert":
                try:
                    from transformers import AutoTokenizer, AutoModel
                    
                    logger.info(f"Carregando modelo BERT {model_key} de {model_path}")
                    tokenizer = AutoTokenizer.from_pretrained(model_path)
                    model = AutoModel.from_pretrained(model_path)
                    
                    self.loaded_models[model_key] = {
                        "tokenizer": tokenizer,
                        "model": model
                    }
                    
                    logger.info(f"Modelo {model_key} carregado com sucesso")
                    return self.loaded_models[model_key]
                except Exception as e:
                    logger.error(f"Erro ao carregar modelo BERT {model_key}: {str(e)}")
                    return None
                    
            elif model_type == "bert_ner":
                try:
                    from transformers import AutoTokenizer, AutoModelForTokenClassification
                    
                    logger.info(f"Carregando modelo BERT-NER {model_key} de {model_path}")
                    tokenizer = AutoTokenizer.from_pretrained(model_path)
                    model = AutoModelForTokenClassification.from_pretrained(model_path)
                    
                    self.loaded_models[model_key] = {
                        "tokenizer": tokenizer,
                        "model": model
                    }
                    
                    logger.info(f"Modelo {model_key} carregado com sucesso")
                    return self.loaded_models[model_key]
                except Exception as e:
                    logger.error(f"Erro ao carregar modelo BERT-NER {model_key}: {str(e)}")
                    return None
                    
            elif model_type == "t5":
                try:
                    # Tratamento especial para modelo T5
                    logger.info(f"Carregando modelo T5 {model_key} de {model_path}")
                    
                    try:
                        from transformers import T5Tokenizer, T5ForConditionalGeneration
                        tokenizer = T5Tokenizer.from_pretrained(model_path)
                        model = T5ForConditionalGeneration.from_pretrained(model_path)
                    except ImportError:
                        # Fallback para AutoTokenizer/AutoModel se T5Tokenizer não estiver disponível
                        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                        tokenizer = AutoTokenizer.from_pretrained(model_path)
                        model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
                    
                    self.loaded_models[model_key] = {
                        "tokenizer": tokenizer,
                        "model": model
                    }
                    
                    logger.info(f"Modelo {model_key} carregado com sucesso")
                    return self.loaded_models[model_key]
                except Exception as e:
                    logger.error(f"Erro ao carregar modelo T5 {model_key}: {str(e)}")
                    return None
            else:
                logger.error(f"Tipo de modelo {model_type} não suportado")
                return None
                
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
        # Resolver chave do modelo se for um nome alternativo
        if model_key in self.ALT_NAMES:
            model_key = self.ALT_NAMES[model_key]
        elif model_key in self.NAME_TO_KEY:
            model_key = self.NAME_TO_KEY[model_key]
            
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
    
    def get_available_models(self) -> Dict[str, bool]:
        """
        Retorna uma lista de todos os modelos e sua disponibilidade.
        
        Returns:
            Dicionário com status de disponibilidade de cada modelo
        """
        status = {}
        
        for model_key in self.MODELS:
            status[model_key] = self.is_available(model_key)
        
        return status