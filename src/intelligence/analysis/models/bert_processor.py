"""
Processador para modelos BERT utilizados na análise jurídica.
"""
import logging
from typing import List, Dict, Any, Optional
import torch
import numpy as np

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bert_processor")

class BERTProcessor:
    """
    Processador para modelos BERT para análise de texto jurídico e legislativo.
    """
    
    def __init__(self, model_data: Dict[str, Any]):
        """
        Inicializa o processador com um modelo BERT já carregado.
        
        Args:
            model_data: Dicionário com 'tokenizer' e 'model' do BERT
        """
        if 'tokenizer' not in model_data or 'model' not in model_data:
            raise ValueError("Dados do modelo incompletos. Necessário 'tokenizer' e 'model'.")
        
        self.tokenizer = model_data['tokenizer']
        self.model = model_data['model']
        
        # Verificar se CUDA está disponível
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Colocar modelo em modo de avaliação
        self.model.eval()
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Gera embeddings para uma lista de textos.
        
        Args:
            texts: Lista de textos para gerar embeddings
            
        Returns:
            Array NumPy com embeddings
        """
        try:
            # Tokenizar os textos
            encoded_input = self.tokenizer(
                texts, 
                padding=True, 
                truncation=True, 
                return_tensors='pt'
            )
            
            # Mover para GPU se disponível
            encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}
            
            # Computar embeddings
            with torch.no_grad():
                output = self.model(**encoded_input)
            
            # Usar representação do token [CLS] como embedding do texto
            embeddings = output.last_hidden_state[:, 0, :].cpu().numpy()
            
            return embeddings
        except Exception as e:
            logger.error(f"Erro ao gerar embeddings: {str(e)}")
            return np.array([])
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula a similaridade entre dois textos usando embeddings BERT.
        
        Args:
            text1: Primeiro texto
            text2: Segundo texto
            
        Returns:
            Valor de similaridade entre 0 e 1
        """
        try:
            # Gerar embeddings
            embeddings = self.get_embeddings([text1, text2])
            
            if len(embeddings) != 2:
                return 0.0
            
            # Calcular similaridade do cosseno
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.error(f"Erro ao calcular similaridade: {str(e)}")
            return 0.0
    
    def classify_legal_text(self, text: str, categories: List[str]) -> Dict[str, float]:
        """
        Classifica um texto em categorias jurídicas/legislativas.
        
        Args:
            text: Texto a ser classificado
            categories: Lista de categorias possíveis
            
        Returns:
            Dicionário com scores para cada categoria
        """
        try:
            # Gerar embedding para o texto
            text_embedding = self.get_embeddings([text])[0]
            
            # Gerar embeddings para as descrições das categorias
            category_embeddings = self.get_embeddings(categories)
            
            # Calcular similaridade com cada categoria
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity([text_embedding], category_embeddings)[0]
            
            # Criar dicionário de resultados
            result = {}
            for i, category in enumerate(categories):
                result[category] = float(similarities[i])
            
            return result
        except Exception as e:
            logger.error(f"Erro ao classificar texto: {str(e)}")
            return {category: 0.0 for category in categories}
    
    def extract_legal_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extrai entidades jurídicas/legislativas de um texto.
        Requer um modelo BERT-NER treinado para entidades jurídicas.
        
        Args:
            text: Texto para extrair entidades
            
        Returns:
            Dicionário com listas de entidades por tipo
        """
        try:
            # Verificar se é um modelo NER
            if not hasattr(self.model, 'config') or not hasattr(self.model.config, 'id2label'):
                logger.error("Modelo não é um BERT-NER. Use 'legal_bert_ner' para esta função.")
                return {}
            
            # Tokenizar o texto
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Executar modelo NER
            with torch.no_grad():
                outputs = self.model(**inputs)
            
            # Extrair previsões
            predictions = torch.argmax(outputs.logits, dim=2)
            
            # Converter previsões em entidades
            predicted_token_ids = predictions[0].cpu().numpy()
            input_ids = inputs["input_ids"][0].cpu().numpy()
            
            # Mapear IDs de tokens para classes (B-LEI, I-LEI, B-PESSOA, etc.)
            id2label = self.model.config.id2label
            
            # Extrair entidades
            entities = {}
            current_entity = None
            current_entity_text = ""
            
            for token_id, pred_id in zip(input_ids, predicted_token_ids):
                # Pular tokens especiais
                if token_id in [self.tokenizer.cls_token_id, self.tokenizer.sep_token_id, self.tokenizer.pad_token_id]:
                    continue
                
                # Obter token e label
                token = self.tokenizer.convert_ids_to_tokens([token_id])[0]
                label = id2label[pred_id]
                
                # Processar label
                if label.startswith("B-"):
                    # Finalizar entidade anterior, se houver
                    if current_entity and current_entity_text:
                        if current_entity not in entities:
                            entities[current_entity] = []
                        entities[current_entity].append(current_entity_text.strip())
                    
                    # Iniciar nova entidade
                    current_entity = label[2:]  # Remover "B-"
                    current_entity_text = token
                elif label.startswith("I-") and current_entity == label[2:]:
                    # Continuar entidade atual
                    current_entity_text += " " + token
                else:
                    # Finalizar entidade anterior, se houver
                    if current_entity and current_entity_text:
                        if current_entity not in entities:
                            entities[current_entity] = []
                        entities[current_entity].append(current_entity_text.strip())
                    
                    current_entity = None
                    current_entity_text = ""
            
            # Finalizar última entidade, se houver
            if current_entity and current_entity_text:
                if current_entity not in entities:
                    entities[current_entity] = []
                entities[current_entity].append(current_entity_text.strip())
            
            return entities
        except Exception as e:
            logger.error(f"Erro ao extrair entidades jurídicas: {str(e)}")
            return {}