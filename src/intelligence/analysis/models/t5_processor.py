"""
Processador para modelos T5 utilizados na sumarização e geração de texto.
"""
import logging
from typing import List, Dict, Any, Optional
import torch

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
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Colocar modelo em modo de avaliação
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
            return ""
    
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
            # Combinando instrução e texto
            input_text = f"{instruction}: {text}"
            
            # Tokenizar o texto
            inputs = self.tokenizer(input_text, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Gerar análise
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=5,
                    top_k=50,
                    top_p=0.95,
                    temperature=0.7,
                    do_sample=True,
                    repetition_penalty=1.2,
                    early_stopping=True
                )
            
            # Decodificar saída
            analysis = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return analysis
        except Exception as e:
            logger.error(f"Erro ao gerar análise jurídica: {str(e)}")
            return ""