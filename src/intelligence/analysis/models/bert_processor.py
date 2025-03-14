"""
Processador para modelos BERT utilizados na análise jurídica.
"""
import logging
from typing import List, Dict, Any, Optional
import torch
import numpy as np
import traceback

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
        try:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model.to(self.device)
            
            # Colocar modelo em modo de avaliação
            self.model.eval()
            
            logger.info(f"Modelo BERT inicializado com sucesso, usando device: {self.device}")
        except Exception as e:
            logger.error(f"Erro ao inicializar o BERTProcessor: {str(e)}")
            self.device = torch.device('cpu')
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
            # Verificar se a lista está vazia
            if not texts:
                logger.warning("Lista de textos vazia para geração de embeddings")
                return np.array([])
            
            # Normalizar entrada
            texts = [text if text else "" for text in texts]
            
            # Truncar textos muito longos
            max_token_length = 512
            truncated_texts = []
            for text in texts:
                tokens = self.tokenizer.tokenize(text)
                if len(tokens) > max_token_length - 2:  # -2 para tokens [CLS] e [SEP]
                    truncated_tokens = tokens[:max_token_length - 2]
                    truncated_text = self.tokenizer.convert_tokens_to_string(truncated_tokens)
                    truncated_texts.append(truncated_text)
                    logger.warning(f"Texto truncado de {len(tokens)} para {max_token_length - 2} tokens")
                else:
                    truncated_texts.append(text)
            
            # Tokenizar os textos
            encoded_input = self.tokenizer(
                truncated_texts, 
                padding=True, 
                truncation=True, 
                max_length=max_token_length,
                return_tensors='pt'
            )
            
            # Mover para GPU se disponível
            encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}
            
            # Computar embeddings em lotes para manejar memória
            batch_size = 8
            all_embeddings = []
            
            for i in range(0, len(truncated_texts), batch_size):
                batch_input = {
                    k: v[i:i+batch_size] for k, v in encoded_input.items()
                }
                
                # Computar embeddings
                with torch.no_grad():
                    output = self.model(**batch_input)
                
                # Usar representação do token [CLS] como embedding do texto
                batch_embeddings = output.last_hidden_state[:, 0, :].cpu().numpy()
                all_embeddings.append(batch_embeddings)
            
            # Concatenar resultados
            embeddings = np.concatenate(all_embeddings, axis=0) if all_embeddings else np.array([])
            
            return embeddings
        except Exception as e:
            logger.error(f"Erro ao gerar embeddings: {str(e)}")
            logger.debug(traceback.format_exc())
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
            # Validar entradas
            if not text1 or not text2:
                logger.warning("Textos vazios para cálculo de similaridade")
                return 0.0
            
            # Gerar embeddings
            embeddings = self.get_embeddings([text1, text2])
            
            if len(embeddings) != 2:
                logger.warning("Falha ao gerar embeddings para cálculo de similaridade")
                return 0.0
            
            # Calcular similaridade do cosseno
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
                
                # Normalizar para [0, 1] (cosine_similarity pode dar -1 a 1)
                similarity = (similarity + 1) / 2 if similarity < 0 else similarity
                
                return max(0.0, min(1.0, similarity))
            except ImportError:
                # Fallback se sklearn não estiver disponível
                norm1 = np.linalg.norm(embeddings[0])
                norm2 = np.linalg.norm(embeddings[1])
                
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                    
                dot_product = np.dot(embeddings[0], embeddings[1])
                similarity = dot_product / (norm1 * norm2)
                
                # Normalizar para [0, 1]
                similarity = (similarity + 1) / 2 if similarity < 0 else similarity
                
                return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.error(f"Erro ao calcular similaridade: {str(e)}")
            logger.debug(traceback.format_exc())
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
            # Validar entradas
            if not text:
                logger.warning("Texto vazio para classificação")
                return {category: 0.0 for category in categories}
            
            if not categories:
                logger.warning("Lista de categorias vazia para classificação")
                return {}
            
            # Gerar embedding para o texto
            text_embedding = self.get_embeddings([text])
            
            if len(text_embedding) == 0:
                logger.warning("Falha ao gerar embedding para classificação")
                return {category: 0.0 for category in categories}
                
            text_embedding = text_embedding[0]
            
            # Gerar embeddings para as descrições das categorias
            category_embeddings = self.get_embeddings(categories)
            
            if len(category_embeddings) != len(categories):
                logger.warning("Falha ao gerar embeddings para categorias")
                return {category: 0.0 for category in categories}
            
            # Calcular similaridade com cada categoria
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                similarities = cosine_similarity([text_embedding], category_embeddings)[0]
                
                # Normalizar valores para [0, 1]
                similarities = [(sim + 1) / 2 if sim < 0 else sim for sim in similarities]
                similarities = [max(0.0, min(1.0, sim)) for sim in similarities]
            except ImportError:
                # Fallback se sklearn não estiver disponível
                similarities = []
                for cat_embedding in category_embeddings:
                    norm1 = np.linalg.norm(text_embedding)
                    norm2 = np.linalg.norm(cat_embedding)
                    
                    if norm1 == 0 or norm2 == 0:
                        similarities.append(0.0)
                        continue
                        
                    dot_product = np.dot(text_embedding, cat_embedding)
                    similarity = dot_product / (norm1 * norm2)
                    
                    # Normalizar para [0, 1]
                    similarity = (similarity + 1) / 2 if similarity < 0 else similarity
                    similarities.append(max(0.0, min(1.0, similarity)))
            
            # Criar dicionário de resultados
            result = {}
            for i, category in enumerate(categories):
                if i < len(similarities):
                    result[category] = float(similarities[i])
                else:
                    result[category] = 0.0
            
            return result
        except Exception as e:
            logger.error(f"Erro ao classificar texto: {str(e)}")
            logger.debug(traceback.format_exc())
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
            
            # Verificar texto
            if not text:
                logger.warning("Texto vazio para extração de entidades")
                return {}
            
            # Limitar tamanho do texto para evitar problemas de memória
            max_length = 512
            truncated = False
            if len(text) > max_length * 2:  # Aproximação grosseira
                text = text[:max_length * 2]
                truncated = True
                logger.warning(f"Texto truncado para extração de entidades")
            
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
            
            try:
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
                
                # Ordenar e remover duplicatas
                for entity_type in entities:
                    entities[entity_type] = sorted(list(set(entities[entity_type])))
                
                # Adicionar informação de truncamento
                if truncated:
                    entities["INFO"] = ["Texto truncado para extração de entidades"]
                
                return entities
            except Exception as e:
                logger.error(f"Erro ao processar tokens para extração de entidades: {str(e)}")
                logger.debug(traceback.format_exc())
                return {}
        except Exception as e:
            logger.error(f"Erro ao extrair entidades jurídicas: {str(e)}")
            logger.debug(traceback.format_exc())
            return {}