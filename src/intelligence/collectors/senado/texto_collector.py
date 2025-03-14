# src/intelligence/collectors/senado/texto_collector.py
"""
Coletor especializado em textos e emendas de PLs.
"""
import logging
from typing import Dict, List, Any, Optional

from .api_base import SenadoAPIBase

# Configuração de logging
logger = logging.getLogger("senado_texto_collector")

class TextoCollector(SenadoAPIBase):
    """Especializado em obter textos e emendas de PLs"""
    
    def get_texto_completo(self, codigo_materia: str) -> Dict[str, Any]:
        """
        Obtém o texto integral do PL e seus metadados.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Dicionário com texto integral e metadados
        """
        logger.info(f"Buscando texto completo para matéria {codigo_materia}")
        
        # Endpoint específico para textos
        endpoint = f"materia/textos/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Textos não encontrados para matéria {codigo_materia}")
            return {
                "UrlTexto": "",
                "UrlRedacao": "",
                "TextoAtual": "",
                "TextoIntegral": "",
                "DataApresentacao": "",
                "Ementa": "",
                "ExplicacaoEmenta": ""
            }
        
        # Processar textos
        if not from_cache:
            try:
                # Extrair dados dos textos
                textos = data.get('TextoMateria', {}).get('Materia', {}).get('Textos', {}).get('Texto', [])
                
                # Garantir que seja uma lista
                if not isinstance(textos, list):
                    textos = [textos]
                
                # Buscar texto mais atual
                texto_atual = None
                for texto in textos:
                    if texto.get('IndicadorTextoAtual', '') == 'Sim':
                        texto_atual = texto
                        break
                
                # Se não encontrou texto atual, pega o último
                if not texto_atual and textos:
                    texto_atual = textos[-1]
                
                # Se ainda não temos texto, retornar valores vazios
                if not texto_atual:
                    return {
                        "UrlTexto": "",
                        "UrlRedacao": "",
                        "TextoAtual": "",
                        "TextoIntegral": "",
                        "DataApresentacao": "",
                        "Ementa": "",
                        "ExplicacaoEmenta": ""
                    }
                
                # Extrair URLs dos textos
                url_texto = texto_atual.get('UrlTexto', '')
                url_redacao = texto_atual.get('UrlRedacaoFinal', '')
                
                # Dados básicos da matéria
                dados_basicos = data.get('TextoMateria', {}).get('Materia', {}).get('DadosBasicosMateria', {})
                
                resultado = {
                    "UrlTexto": url_texto,
                    "UrlRedacao": url_redacao,
                    "TextoAtual": "Sim" if texto_atual.get('IndicadorTextoAtual', '') == 'Sim' else "Não",
                    "TextoIntegral": "",  # Implementação futura: baixar o texto de url_texto
                    "DataApresentacao": dados_basicos.get('DataApresentacao', ''),
                    "Ementa": dados_basicos.get('EmentaMateria', ''),
                    "ExplicacaoEmenta": dados_basicos.get('ExplicacaoEmentaMateria', '')
                }
                
                # Se tiver URL, tentar baixar o texto
                if url_texto:
                    texto_integral = self._baixar_texto(url_texto)
                    if texto_integral:
                        resultado["TextoIntegral"] = texto_integral
                
                return resultado
            except Exception as e:
                logger.error(f"Erro ao processar textos da matéria {codigo_materia}: {str(e)}")
                return {
                    "UrlTexto": "",
                    "UrlRedacao": "",
                    "TextoAtual": "",
                    "TextoIntegral": "",
                    "DataApresentacao": "",
                    "Ementa": "",
                    "ExplicacaoEmenta": ""
                }
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def _baixar_texto(self, url: str) -> str:
        """
        Baixa o texto de uma URL.
        
        Args:
            url: URL do texto
            
        Returns:
            Conteúdo do texto ou string vazia se falhar
        """
        if not url:
            return ""
        
        try:
            # Fazer requisição para a URL
            response = self.session.get(url, timeout=30)
            
            # Verificar resposta
            if response.status_code == 200:
                # Tentar detectar encoding
                encoding = response.encoding or 'utf-8'
                
                # Retornar texto
                return response.text
            else:
                logger.error(f"Erro {response.status_code} ao baixar texto de {url}")
                return ""
        except Exception as e:
            logger.error(f"Erro ao baixar texto de {url}: {str(e)}")
            return ""
    
    def get_emendas(self, codigo_materia: str) -> List[Dict[str, Any]]:
        """
        Obtém as emendas apresentadas ao PL.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de emendas com informações detalhadas
        """
        logger.info(f"Buscando emendas para matéria {codigo_materia}")
        
        # Endpoint específico para emendas
        endpoint = f"materia/emendas/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Emendas não encontradas para matéria {codigo_materia}")
            return []
        
        # Processar emendas
        if not from_cache:
            try:
                # Extrair dados das emendas
                emendas = data.get('EmendaMateria', {}).get('Materia', {}).get('Emendas', {}).get('Emenda', [])
                
                # Garantir que seja uma lista
                if not isinstance(emendas, list):
                    emendas = [emendas]
                
                # Processar cada emenda
                resultado = []
                for emenda in emendas:
                    emenda_processada = self._processar_emenda(emenda)
                    if emenda_processada:
                        resultado.append(emenda_processada)
                
                logger.info(f"Encontradas {len(resultado)} emendas para matéria {codigo_materia}")
                return resultado
            except Exception as e:
                logger.error(f"Erro ao processar emendas da matéria {codigo_materia}: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def _processar_emenda(self, emenda_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Processa dados de uma emenda.
        
        Args:
            emenda_data: Dados da emenda
            
        Returns:
            Dicionário com informações processadas da emenda ou None se dados inválidos
        """
        if not emenda_data:
            return None
        
        try:
            # Extrair informações básicas
            numero_emenda = emenda_data.get('NumeroEmenda', '')
            data_apresentacao = emenda_data.get('DataApresentacao', '')
            
            # Se não tiver número, considerar inválido
            if not numero_emenda:
                return None
            
            # Extrair autor
            autor = ""
            autoria = emenda_data.get('Autoria', {})
            if autoria:
                autor_obj = autoria.get('Autor', {})
                if autor_obj:
                    autor = autor_obj.get('NomeAutor', '')
            
            # Extrair texto e URLs
            texto = emenda_data.get('TextoEmenda', '')
            url_texto = emenda_data.get('UrlTexto', '')
            
            # Se tiver URL mas não texto, tentar baixar
            if url_texto and not texto:
                texto = self._baixar_texto(url_texto)
            
            # Organizar resultado
            resultado = {
                "Numero": numero_emenda,
                "Data": data_apresentacao,
                "Autor": autor,
                "Texto": texto,
                "UrlTexto": url_texto,
                "Local": emenda_data.get('Local', {}).get('NomeLocal', '')
            }
            
            # Adicionar informações de comissão se disponíveis
            comissao = emenda_data.get('Comissao', {})
            if comissao:
                resultado["Comissao"] = comissao.get('NomeComissao', '')
                resultado["SiglaComissao"] = comissao.get('SiglaComissao', '')
            
            return resultado
        except Exception as e:
            logger.error(f"Erro ao processar dados da emenda: {str(e)}")
            return None