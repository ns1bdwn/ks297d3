"""
Processador para modelos T5 utilizados na sumarização e geração de texto.
"""
import logging
from typing import List, Dict, Any, Optional
import torch
import traceback

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("t5_processor")

class T5Processor:
    """
    Processador para modelos T5 para sumarização e geração de texto jurídico.
    """
    
    def __init__(self, model_data: Dict[str, Any]):
        """
        Inicializa o processador com um modelo T5 já carregado.
        
        Args:
            model_data: Dicionário com 'tokenizer' e 'model' do T5
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
            
            logger.info(f"Modelo T5 inicializado com sucesso, usando device: {self.device}")
        except Exception as e:
            logger.error(f"Erro ao inicializar o T5Processor: {str(e)}")
            self.device = torch.device('cpu')
            self.model.eval()
    
    def summarize_text(self, text: str, max_length: int = 150) -> str:
        """
        Sumariza um texto usando o modelo T5.
        
        Args:
            text: Texto a ser sumarizado
            max_length: Tamanho máximo do resumo
            
        Returns:
            Texto resumido
        """
        try:
            # Verificar se o texto está vazio
            if not text or len(text.strip()) == 0:
                return "Não há texto para resumir."
            
            # Limitar tamanho do texto de entrada para evitar problemas
            max_input_length = 1024
            if len(text) > max_input_length:
                text = text[:max_input_length]
                logger.warning(f"Texto truncado para {max_input_length} caracteres")
            
            # Prefixo para tarefa de sumarização
            input_text = f"resumir: {text}"
            
            # Tokenizar o texto
            inputs = self.tokenizer(input_text, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Gerar resumo
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=4,
                    early_stopping=True,
                    no_repeat_ngram_size=2
                )
            
            # Decodificar saída
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return summary
        except Exception as e:
            logger.error(f"Erro ao sumarizar texto: {str(e)}")
            logger.debug(traceback.format_exc())
            return "Erro ao gerar resumo. " + str(e)
    
    def generate_legal_analysis(self, text: str, instruction: str, max_length: int = 500) -> str:
        """
        Gera uma análise jurídica baseada em um texto e uma instrução.
        
        Args:
            text: Texto base para análise
            instruction: Instrução específica para a análise
            max_length: Tamanho máximo da saída
            
        Returns:
            Análise jurídica gerada
        """
        try:
            # Verificar se o texto está vazio
            if not text or len(text.strip()) == 0:
                return "Não há texto para analisar."
            
            # Limitar tamanho do texto de entrada para evitar problemas
            max_input_length = 1024
            if len(text) > max_input_length:
                text = text[:max_input_length]
                logger.warning(f"Texto truncado para {max_input_length} caracteres")
            
            # Combinar instrução e texto
            input_text = f"{instruction}: {text}"
            
            # Tokenizar o texto
            inputs = self.tokenizer(input_text, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Ajustar configurações de geração com base no tamanho do texto
            temperature = 0.7
            if len(text) < 200:
                # Para textos curtos, usar configurações mais criativas
                temperature = 0.8
                top_p = 0.95
                num_beams = 4
            else:
                # Para textos longos, ser mais conservador
                temperature = 0.6
                top_p = 0.9
                num_beams = 5
            
            # Gerar análise
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=num_beams,
                    top_k=50,
                    top_p=top_p,
                    temperature=temperature,
                    do_sample=True,
                    repetition_penalty=1.2,
                    early_stopping=True
                )
            
            # Decodificar saída
            analysis = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return analysis
        except Exception as e:
            logger.error(f"Erro ao gerar análise jurídica: {str(e)}")
            logger.debug(traceback.format_exc())
            return "Erro ao gerar análise. " + str(e)
    
    def analyze_political_context(self, text: str, max_length: int = 200) -> str:
        """
        Analisa o contexto político de um texto legislativo.
        
        Args:
            text: Texto legislativo
            max_length: Tamanho máximo da análise
            
        Returns:
            Análise do contexto político
        """
        instruction = "Analisar o contexto político atual deste projeto de lei"
        return self.generate_legal_analysis(text, instruction, max_length)
    
    def analyze_sector_impact(self, text: str, sector: str = "", max_length: int = 200) -> str:
        """
        Analisa o impacto setorial de um texto legislativo.
        
        Args:
            text: Texto legislativo
            sector: Setor específico para análise (opcional)
            max_length: Tamanho máximo da análise
            
        Returns:
            Análise do impacto setorial
        """
        if sector:
            instruction = f"Analisar o impacto deste projeto de lei no setor de {sector}"
        else:
            instruction = "Analisar o impacto setorial potencial deste projeto de lei"
        
        return self.generate_legal_analysis(text, instruction, max_length)