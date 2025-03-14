# src/intelligence/collectors/senado/tramitacao_collector.py
"""
Coletor especializado em tramitação e situação atual de PLs.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .api_base import SenadoAPIBase

# Configuração de logging
logger = logging.getLogger("senado_tramitacao_collector")

class TramitacaoCollector(SenadoAPIBase):
    """Especializado em coletar tramitação e situação atual de PLs"""
    
    def get_situacao_atual(self, codigo_materia: str) -> Dict[str, Any]:
        """
        Obtém a situação atual de um PL.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Dicionário com a situação atual
        """
        logger.info(f"Buscando situação atual da matéria {codigo_materia}")
        
        # Endpoint para situação atual
        endpoint = f"materia/situacaoatual/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Situação atual não encontrada para matéria {codigo_materia}")
            return {
                "Local": "",
                "Situacao": "",
                "Data": ""
            }
        
        # Processar situação atual
        if not from_cache:
            try:
                situacao = data.get('SituacaoAtualMateria', {}).get('Materia', {})
                
                if situacao:
                    local = situacao.get('Local', {}).get('NomeLocal', '')
                    sigla_local = situacao.get('Local', {}).get('SiglaLocal', '')
                    situacao_desc = situacao.get('Situacao', {}).get('DescricaoSituacao', '')
                    data_situacao = situacao.get('Situacao', {}).get('DataSituacao', '')
                    
                    return {
                        "Local": local,
                        "SiglaLocal": sigla_local,
                        "Situacao": situacao_desc,
                        "Data": data_situacao
                    }
            except Exception as e:
                logger.error(f"Erro ao processar situação atual da matéria {codigo_materia}: {str(e)}")
        else:
            # Se veio do cache, retorna diretamente
            return data
        
        return {
            "Local": "",
            "Situacao": "",
            "Data": ""
        }
    
    def get_tramitacao(self, codigo_materia: str) -> List[Dict[str, Any]]:
        """
        Obtém o histórico completo de tramitação de um PL.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de eventos de tramitação
        """
        logger.info(f"Buscando tramitação da matéria {codigo_materia}")
        
        # Endpoint para movimentações
        endpoint = f"materia/movimentacoes/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Tramitação não encontrada para matéria {codigo_materia}")
            return []
        
        # Processar tramitação
        if not from_cache:
            try:
                movimentacoes = data.get('MovimentacaoMateria', {}).get('Movimentacoes', {}).get('Movimentacao', [])
                
                # Garantir que seja uma lista
                if not isinstance(movimentacoes, list):
                    movimentacoes = [movimentacoes]
                
                # Processar cada evento
                processed_data = []
                for evento in movimentacoes:
                    processed_data.append({
                        "Data": evento.get('DataMovimentacao', ''),
                        "Local": evento.get('Local', {}).get('NomeLocal', ''),
                        "SiglaLocal": evento.get('Local', {}).get('SiglaLocal', ''),
                        "Situacao": evento.get('Situacao', {}).get('DescricaoSituacao', ''),
                        "Texto": evento.get('TextoMovimentacao', '')
                    })
                
                # Ordenar por data (mais recente primeiro)
                processed_data.sort(key=lambda x: x.get('Data', ''), reverse=True)
                
                return processed_data
            except Exception as e:
                logger.error(f"Erro ao processar tramitação da matéria {codigo_materia}: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def get_ultimas_atualizacoes(self, codigo_materia: str) -> List[Dict[str, Any]]:
        """
        Obtém as últimas atualizações da matéria (inclui alterações recentes).
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de atualizações recentes
        """
        logger.info(f"Buscando atualizações recentes da matéria {codigo_materia}")
        
        # Endpoint para atualizações
        endpoint = f"materia/atualizacoes/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Atualizações não encontradas para matéria {codigo_materia}")
            return []
        
        # Processar atualizações
        if not from_cache:
            try:
                atualizacoes = data.get('AtualizacoesMateria', {}).get('Atualizacoes', {}).get('Atualizacao', [])
                
                # Garantir que seja uma lista
                if not isinstance(atualizacoes, list):
                    atualizacoes = [atualizacoes]
                
                # Processar cada atualização
                processed_data = []
                for atualizacao in atualizacoes:
                    processed_data.append({
                        "Data": atualizacao.get('DataAtualizacao', ''),
                        "DescricaoAtualizacao": atualizacao.get('DescricaoAtualizacao', ''),
                        "SituacaoAnterior": atualizacao.get('SituacaoAnterior', {}).get('DescricaoSituacao', ''),
                        "SituacaoAtual": atualizacao.get('SituacaoAtual', {}).get('DescricaoSituacao', ''),
                        "LocalAnterior": atualizacao.get('LocalAnterior', {}).get('NomeLocal', ''),
                        "LocalAtual": atualizacao.get('LocalAtual', {}).get('NomeLocal', '')
                    })
                
                # Ordenar por data (mais recente primeiro)
                processed_data.sort(key=lambda x: x.get('Data', ''), reverse=True)
                
                return processed_data
            except Exception as e:
                logger.error(f"Erro ao processar atualizações da matéria {codigo_materia}: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def get_prazos(self, codigo_materia: str) -> List[Dict[str, Any]]:
        """
        Obtém os prazos relacionados à tramitação.
        Função auxiliar que extrai prazos das movimentações.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de prazos identificados
        """
        # Obter tramitação
        tramitacao = self.get_tramitacao(codigo_materia)
        
        # Procurar por prazos nas movimentações
        prazos = []
        for evento in tramitacao:
            texto = evento.get('Texto', '').lower()
            data = evento.get('Data', '')
            
            # Procurar menções a prazos
            if 'prazo' in texto:
                # Identificar possíveis datas de prazo
                import re
                # Padrão para prazo em dias (ex: "prazo de 10 dias")
                dias_match = re.search(r'prazo\s+(?:de|para|é|:)?\s+(\d+)\s+dias?', texto)
                # Padrão para data específica (ex: "prazo até 15/12/2023")
                data_match = re.search(r'prazo\s+(?:até|para|no dia)\s+(\d{1,2}/\d{1,2}/\d{4}|\d{1,2}/\d{1,2}/\d{2})', texto)
                
                prazo_info = {
                    "Tipo": "Não especificado",
                    "DataInicio": data,
                    "DataFim": "",
                    "DescricaoPrazo": texto,
                    "Local": evento.get('Local', '')
                }
                
                # Se encontrou prazo em dias
                if dias_match:
                    dias = int(dias_match.group(1))
                    
                    # Calcular data de término (aproximada)
                    try:
                        from datetime import datetime, timedelta
                        data_inicio = datetime.strptime(data, "%Y-%m-%d")
                        data_fim = data_inicio + timedelta(days=dias)
                        prazo_info["DataFim"] = data_fim.strftime("%Y-%m-%d")
                        prazo_info["Tipo"] = "Dias"
                        prazo_info["DiasPrevistos"] = dias
                        prazos.append(prazo_info)
                    except:
                        # Se falhar o cálculo de data, apenas registra o prazo
                        prazo_info["Tipo"] = "Dias"
                        prazo_info["DiasPrevistos"] = dias
                        prazos.append(prazo_info)
                
                # Se encontrou data específica
                elif data_match:
                    data_prazo = data_match.group(1)
                    
                    # Padronizar formato da data
                    try:
                        # Converter para o formato YYYY-MM-DD
                        if len(data_prazo.split('/')[-1]) == 2:  # Ano com 2 dígitos
                            dia, mes, ano = data_prazo.split('/')
                            # Assumir que anos menores que 50 são do século 21, maiores são do século 20
                            if int(ano) < 50:
                                ano = f"20{ano}"
                            else:
                                ano = f"19{ano}"
                            data_prazo = f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
                        else:  # Ano com 4 dígitos
                            dia, mes, ano = data_prazo.split('/')
                            data_prazo = f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
                        
                        prazo_info["DataFim"] = data_prazo
                        prazo_info["Tipo"] = "Data Específica"
                        prazos.append(prazo_info)
                    except:
                        # Se falhar a conversão, ainda registra o prazo com data original
                        prazo_info["DataFim"] = data_prazo
                        prazo_info["Tipo"] = "Data Específica"
                        prazos.append(prazo_info)
                
                # Se encontrou menção a prazo, mas não conseguiu extrair detalhes
                else:
                    # Apenas registrar que há um prazo mencionado
                    prazo_info["Tipo"] = "Mencionado"
                    prazos.append(prazo_info)
        
        return prazos