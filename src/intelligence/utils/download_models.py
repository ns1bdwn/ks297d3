from pathlib import Path
from datetime import datetime, timezone
import os
import logging
import subprocess
import json
import requests
import torch
from transformers import AutoModel, AutoTokenizer

class ModelManager:
    """Gerenciador de modelos de IA e NLP para análise regulatória."""

    MODELS = {
        "legal_bert": {
            "version": "1.0",
            "name": "legal-bert-base-cased-ptbr",
            "type": "huggingface",
            "hub": "dominguesm/legal-bert-base-cased-ptbr"
        },
        "legal_bert_ner": {
            "version": "1.0",
            "name": "legal-bert-ner-base-cased-ptbr",
            "type": "huggingface",
            "hub": "dominguesm/legal-bert-ner-base-cased-ptbr"
        },
        "jurisbert_sts": {
            "version": "1.0",
            "name": "jurisbert-base-portuguese-sts",
            "type": "huggingface",
            "hub": "alfaneo/jurisbert-base-portuguese-sts"
        },
        "jurisbert_uncased": {
            "version": "1.0",
            "name": "jurisbert-base-portuguese-uncased",
            "type": "huggingface",
            "hub": "alfaneo/jurisbert-base-portuguese-uncased"
        },
        "mt5": {
            "version": "1.0",
            "name": "ptt5-large-portuguese-vocab",
            "type": "huggingface",
            "hub": "unicamp-dl/ptt5-large-portuguese-vocab"
        },
        "bertimbau_large": {
            "version": "1.0",
            "name": "bert-large-portuguese-cased",
            "type": "huggingface",
            "hub": "neuralmind/bert-large-portuguese-cased"
        }
    }

    # Mapeamento reverso para permitir busca pelo nome completo do modelo
    NAME_TO_KEY = {info["name"]: key for key, info in MODELS.items()}

    def __init__(self):
        # Encontrar a raiz do projeto corretamente (4 níveis acima, assumindo que o arquivo está em src/intelligence/utils/)
        self.base_dir = Path(__file__).resolve().parents[3]  # Ajuste para subir para a raiz do projeto
        self.models_dir = self.base_dir / "data" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.version_file = self.models_dir / "model_status.json"

        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "true"  # Desabilitar aviso de symlinks

        self.setup_logging()
        self.load_versions()
        self.ensure_dependencies()

    def setup_logging(self):
        log_dir = self.base_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            filename=log_dir / "model_manager.log",
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

    def load_versions(self):
        if self.version_file.exists():
            with open(self.version_file, "r", encoding='utf-8') as f:
                self.installed_versions = json.load(f)
        else:
            self.installed_versions = {}

    def save_versions(self):
        with open(self.version_file, "w", encoding='utf-8') as f:
            json.dump(self.installed_versions, f, indent=4, ensure_ascii=False)

    def ensure_dependencies(self):
        """Garante que todas as dependências necessárias estão instaladas."""
        try:
            # Verificar se sentencepiece está instalado
            import importlib.util
            if importlib.util.find_spec("sentencepiece") is None:
                print("Instalando biblioteca SentencePiece necessária para modelos T5...")
                subprocess.check_call(
                    ["pip", "install", "sentencepiece"],
                    stdout=subprocess.DEVNULL
                )
                print("✅ SentencePiece instalado com sucesso!")
            else:
                print("SentencePiece já está instalado.")
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível verificar/instalar SentencePiece: {str(e)}")

    def get_model_path(self, model_name: str) -> Path:
        # Obter a chave do modelo, seja pelo identificador curto ou pelo nome completo
        model_key = self.get_model_key(model_name)
        model_info = self.MODELS[model_key]
        
        if model_info["type"] == "huggingface":
            safe_name = model_info["hub"].replace("/", "_")
            return self.models_dir / safe_name
        return self.models_dir / model_key

    def get_model_key(self, model_name: str) -> str:
        """Converte um nome de modelo (completo ou chave) para a chave apropriada."""
        # Se o nome já for uma chave válida
        if model_name in self.MODELS:
            return model_name
            
        # Se o nome for um nome completo de modelo
        if model_name in self.NAME_TO_KEY:
            return self.NAME_TO_KEY[model_name]
            
        # Se não for encontrado
        raise ValueError(f"Modelo '{model_name}' não reconhecido. Use --list para ver modelos disponíveis.")

    def is_model_installed(self, model_name: str) -> bool:
        try:
            model_key = self.get_model_key(model_name)
            model_path = self.get_model_path(model_key)
            return model_path.exists() and model_key in self.installed_versions
        except ValueError:
            return False

    def check_for_updates(self, model_name: str) -> bool:
        """Verifica se há atualizações disponíveis para um modelo.
        
        Returns:
            bool: True se há atualizações, False caso contrário
        """
        try:
            model_key = self.get_model_key(model_name)
            model_info = self.MODELS[model_key]
            
            if model_key not in self.installed_versions:
                # Modelo não instalado, então precisa de atualização
                return True
            
            # Verificar última atualização no Hugging Face
            api_url = f"https://huggingface.co/api/models/{model_info['hub']}"
            
            try:
                response = requests.get(api_url)
                if response.status_code == 200:
                    model_data = response.json()
                    # Extrair a data da última modificação
                    last_modified = model_data.get('lastModified')
                    
                    if last_modified:
                        # Converter para objeto datetime com timezone (aware)
                        hf_update_time = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                        
                        # Pegar a data de instalação local
                        local_date_str = self.installed_versions[model_key].get('date')
                        
                        # Garantir que a data local também tenha informações de timezone
                        if local_date_str:
                            try:
                                # Tentar converter com timezone
                                if local_date_str.endswith('Z'):
                                    local_date_str = local_date_str.replace('Z', '+00:00')
                                    
                                if '+' in local_date_str or '-' in local_date_str and 'T' in local_date_str:
                                    # Se já tiver timezone
                                    local_date = datetime.fromisoformat(local_date_str)
                                else:
                                    # Se não tiver timezone, assumir UTC
                                    local_date = datetime.fromisoformat(local_date_str).replace(tzinfo=timezone.utc)
                                
                                # Comparar datas (ambas com timezone)
                                return hf_update_time > local_date
                            except Exception as e:
                                logging.error(f"Erro ao converter data local '{local_date_str}': {str(e)}")
                                # Em caso de erro na conversão de data, assumir que precisa atualizar
                                return True
                        else:
                            # Se não tiver data local, assumir que precisa atualizar
                            return True
            except Exception as e:
                logging.error(f"Erro ao verificar atualizações para {model_name}: {str(e)}")
                print(f"⚠️ Não foi possível verificar atualizações online para {model_name}")
                # Em caso de erro, assumir que não há atualizações
                return False
                
            # Se chegou até aqui, não conseguiu determinar se há atualizações
            return False
        except ValueError:
            # Modelo não reconhecido
            return False

    def download_model(self, model_name: str, force_update=False):
        try:
            model_key = self.get_model_key(model_name)
        except ValueError as e:
            print(f"Erro: {str(e)}")
            return

        model_info = self.MODELS[model_key]
        model_path = self.get_model_path(model_key)

        # Verificar se o modelo já está instalado
        if self.is_model_installed(model_key) and not force_update:
            # Verificar se há atualizações disponíveis
            if self.check_for_updates(model_key):
                print(f"Há uma atualização disponível para {model_info['name']}. Baixando...")
            else:
                print(f"O modelo {model_info['name']} já está instalado e atualizado.")
                return
        elif self.is_model_installed(model_key) and force_update:
            print(f"Forçando atualização do modelo {model_info['name']}...")
        else:
            print(f"\nBaixando modelo: {model_info['name']}...")

        try:
            if model_info["type"] == "huggingface":
                self._download_huggingface(model_info, model_path)
            else:
                self._download_custom_model(model_info, model_path)

            # Armazenar a data com timezone para evitar problemas de comparação
            self.installed_versions[model_key] = {
                "version": model_info["version"],
                "date": datetime.now(timezone.utc).isoformat(),
                "path": str(model_path)
            }
            self.save_versions()
            
            print(f"✅ Modelo {model_info['name']} instalado com sucesso!")

        except Exception as e:
            print(f"❌ Erro ao baixar {model_info['name']}: {str(e)}")
            raise

    def _download_huggingface(self, info, model_path):
        """Baixa um modelo do Hugging Face."""
        # Tratamento especial para modelos T5
        if "t5" in info["name"].lower():
            try:
                # Garantir que as importações estejam disponíveis
                import sentencepiece
                from transformers import T5Model, T5Tokenizer
                
                print("Baixando tokenizer T5...")
                tokenizer = T5Tokenizer.from_pretrained(info["hub"])
                
                print("Baixando modelo T5...")
                model = T5Model.from_pretrained(info["hub"])
            except ImportError:
                print("SentencePiece não está disponível. Tentando alternativa...")
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer as T5AutoTokenizer
                tokenizer = T5AutoTokenizer.from_pretrained(info["hub"], use_fast=False)
                model = AutoModelForSeq2SeqLM.from_pretrained(info["hub"])
        else:
            # Para modelos BERT e outros
            # Reimportar aqui para garantir que as variáveis estejam no escopo
            from transformers import AutoTokenizer as BertAutoTokenizer, AutoModel as BertAutoModel
            print(f"Baixando tokenizer para {info['name']}...")
            tokenizer = BertAutoTokenizer.from_pretrained(info["hub"])
            
            print(f"Baixando modelo para {info['name']}...")
            model = BertAutoModel.from_pretrained(info["hub"])

        model_path.mkdir(parents=True, exist_ok=True)

        print(f"Salvando tokenizer e modelo em {model_path}...")
        tokenizer.save_pretrained(model_path)
        model.save_pretrained(model_path)

        print(f"✅ Modelo {info['name']} baixado e salvo em {model_path}")

    def _download_custom_model(self, info, model_path):
        # Lógica de download para o modelo customizado, se necessário
        print(f"Baixando modelo customizado: {info['name']}...")
        # Exemplo: copy do arquivo, ou download de repositório

        print(f"✅ Modelo {info['name']} baixado e salvo em {model_path}")

    def check_environment(self):
        return {
            "cuda_available": torch.cuda.is_available(),
            "gpu_memory": torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else None
        }

def main():
    """Função principal para execução via linha de comando."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gerenciador de Modelos de IA para Análise Regulatória")
    parser.add_argument("--model", type=str, help="Nome do modelo para download (por identificador ou nome completo)")
    parser.add_argument("--update", action="store_true", help="Atualizar modelo mesmo se já existir")
    parser.add_argument("--list", action="store_true", help="Listar modelos disponíveis")
    parser.add_argument("--check", action="store_true", help="Verificar status do ambiente")
    parser.add_argument("--check-updates", action="store_true", help="Verificar atualizações disponíveis")
    parser.add_argument("--download-all", action="store_true", help="Baixar todos os modelos disponíveis")
    
    args = parser.parse_args()
    manager = ModelManager()
    
    if args.check:
        env_status = manager.check_environment()
        print(f"Status do ambiente:")
        print(f"  CUDA disponível: {env_status['cuda_available']}")
        if env_status['cuda_available']:
            print(f"  Memória GPU: {env_status['gpu_memory'] / (1024**3):.2f} GB")
        return
    
    if args.list:
        print("Modelos disponíveis:")
        for key, info in manager.MODELS.items():
            status = "Instalado" if manager.is_model_installed(key) else "Não instalado"
            print(f"  - {key} ({info['name']}): {status}")
        return
    
    if args.check_updates:
        print("Verificando atualizações disponíveis:")
        for key, info in manager.MODELS.items():
            if manager.is_model_installed(key):
                has_updates = manager.check_for_updates(key)
                status = "Atualização disponível" if has_updates else "Atualizado"
                print(f"  - {info['name']}: {status}")
        return
    
    if args.download_all:
        print("Baixando todos os modelos disponíveis:")
        for key in manager.MODELS:
            try:
                print(f"\n--- Processando modelo: {key} ---")
                manager.download_model(key, force_update=args.update)
            except Exception as e:
                print(f"Erro ao baixar modelo {key}: {e}")
        return
    
    if args.model:
        try:
            model_key = manager.get_model_key(args.model)
            if manager.is_model_installed(model_key) and not args.update:
                if manager.check_for_updates(model_key):
                    print(f"Há uma atualização disponível para {args.model}. Use --update para atualizar.")
                else:
                    print(f"Modelo {args.model} já está instalado e atualizado.")
                return
            
            manager.download_model(args.model, force_update=args.update)
        except ValueError as e:
            print(f"Erro: {e}")
        except Exception as e:
            print(f"Erro ao baixar modelo: {e}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()