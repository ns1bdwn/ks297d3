# src/intelligence/collectors/senado/autoria_collector.py
"""
Coletor especializado em autoria de PLs.
"""
import logging
from typing import Dict, List, Any, Optional

from .api_base import SenadoAPIBase

# Configuração de logging
logger = logging.getLogger("senado_autoria_collector")

class AutoriaCollector(SenadoAPIBase):
    """Especializado em obter informações detalhadas de autoria de PLs"""
    
    def get_autoria_detalhada(self, codigo_materia: str) -> List[Dict[str, Any]]:
        """
        Obtém informações detalhadas sobre os autores da matéria.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de autores com informações detalhadas
        """
        logger.info(f"Buscando autoria detalhada para matéria {codigo_materia}")
        
        # Endpoint específico para autoria
        endpoint = f"materia/autoria/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Autoria não encontrada para matéria {codigo_materia}")
            return []
        
        # Processar autores
        if not from_cache:
            try:
                # Extrair dados de autoria
                autoria = data.get('AutoriaMateria', {}).get('Autores', {}).get('Autor', [])
                
                # Garantir que seja uma lista
                if not isinstance(autoria, list):
                    autoria = [autoria]
                
                # Processar cada autor
                resultado = []
                for autor in autoria:
                    autor_processado = self._processar_autor(autor)
                    if autor_processado:
                        resultado.append(autor_processado)
                
                logger.info(f"Encontrados {len(resultado)} autores para matéria {codigo_materia}")
                return resultado
            except Exception as e:
                logger.error(f"Erro ao processar autoria da matéria {codigo_materia}: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def _processar_autor(self, autor_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Processa dados de um autor.
        
        Args:
            autor_data: Dados do autor
            
        Returns:
            Dicionário com informações processadas do autor ou None se dados inválidos
        """
        if not autor_data:
            return None
        
        try:
            # Verificar se tem informações mínimas
            nome = autor_data.get('NomeAutor', '')
            
            if not nome:
                return None
            
            # Extrair tipo de autor
            tipo_autor = "Parlamentar"  # Valor padrão
            
            # Determinar tipo de autor com base no nome ou atributos
            if "Senador" in nome or "Senadora" in nome:
                tipo_autor = "Parlamentar"
            elif "Comissão" in nome:
                tipo_autor = "Comissão"
            elif "Executivo" in nome or "Presidente" in nome or "Ministério" in nome:
                tipo_autor = "Poder Executivo"
            elif "Judiciário" in nome or "Supremo" in nome or "Tribunal" in nome:
                tipo_autor = "Poder Judiciário"
            elif "Popular" in nome:
                tipo_autor = "Iniciativa Popular"
            
            # Verificar se há uma chave explícita de tipo
            if 'TipoAutor' in autor_data:
                # Usar o tipo explícito se disponível
                tipo_explicito = autor_data.get('TipoAutor', '')
                if tipo_explicito:
                    tipo_autor = tipo_explicito
            
            # Extrair partido/UF
            partido = ""
            uf = ""
            
            # Para parlamentares, tentar extrair partido/UF do nome
            if tipo_autor == "Parlamentar":
                import re
                partido_uf_match = re.search(r'\(([A-Z]+)[\/\-]([A-Z]{2})\)', nome)
                if partido_uf_match:
                    partido = partido_uf_match.group(1)
                    uf = partido_uf_match.group(2)
                    
                    # Remover parte do partido/UF do nome
                    nome_limpo = re.sub(r'\([A-Z]+[\/\-][A-Z]{2}\)', '', nome).strip()
                    nome = nome_limpo
            
            # Verificar se há um identificador parlamentar
            codigo_parlamentar = ""
            if 'IdentificacaoParlamentar' in autor_data:
                identificacao = autor_data.get('IdentificacaoParlamentar', {})
                codigo_parlamentar = identificacao.get('CodigoParlamentar', '')
                
                # Se tivermos identificação parlamentar, podemos obter mais dados
                if not partido:
                    partido = identificacao.get('SiglaPartidoParlamentar', '')
                if not uf:
                    uf = identificacao.get('UfParlamentar', '')
                
                # Verificar se há nome completo
                nome_completo = identificacao.get('NomeCompletoParlamentar', '')
                if nome_completo:
                    # Usar nome completo se disponível
                    nome = nome_completo
            
            # Organizar resultado
            return {
                "nome": nome,
                "tipo": tipo_autor,
                "partido": partido,
                "uf": uf,
                "codigo_parlamentar": codigo_parlamentar,
                "primeiro_autor": autor_data.get('IndicadorAutorPrincipal', 'Não') == 'Sim'
            }
        except Exception as e:
            logger.error(f"Erro ao processar dados do autor: {str(e)}")
            return None
    
    def get_autor_principal(self, codigo_materia: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações apenas do autor principal da matéria.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Dicionário com informações do autor principal ou None se não encontrado
        """
        # Buscar todos os autores
        autores = self.get_autoria_detalhada(codigo_materia)
        
        if not autores:
            return None
        
        # Procurar autor principal
        autor_principal = next((autor for autor in autores if autor.get('primeiro_autor', False)), None)
        
        # Se não encontrou marcado como principal, pegar o primeiro
        if not autor_principal and autores:
            autor_principal = autores[0]
        
        return autor_principal