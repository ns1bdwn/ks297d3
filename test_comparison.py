# test_comparison.py
"""
Script para testar e comparar a implementação original e a melhorada
para obtenção de dados de PLs, com foco nos relatores.
"""
import logging
import json
import sys
import os
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("comparison_test.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_comparison")

# Importar as duas versões da implementação
# Vamos simular isso criando duas classes baseadas no mesmo código
# mas com as implementações diferentes de get_pl_relatores
try:
    # Adicionar diretório raiz ao path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Importar a implementação original
    from src.intelligence.collectors.senado_api import SenadoAPI as OriginalAPI
    
    # Criar uma classe que estende a original mas usa o método melhorado
    class ImprovedAPI(OriginalAPI):
        """Versão melhorada da API do Senado com tratamento robusto para relatores."""
        
        def get_pl_relatores(self, codigo_materia):
            """
            Versão melhorada do método para obter relatores designados para um PL.
            
            Args:
                codigo_materia: Código da matéria
                
            Returns:
                Lista de relatores com informações detalhadas
            """
            logger.info(f"[IMPROVED] Buscando relatores para matéria {codigo_materia}")
            
            # Endpoint para relatoria
            endpoint = f"materia/relatoria/{codigo_materia}"
            
            # Fazer requisição
            data, from_cache = self._make_request(endpoint)
            
            # Processar resposta
            if not from_cache:
                try:
                    relatoria = data.get('RelatoriaMateria', {})
                    if not relatoria:
                        logger.debug(f"[IMPROVED] Estrutura 'RelatoriaMateria' não encontrada para matéria {codigo_materia}")
                        return []
                        
                    materia_rel = relatoria.get('Materia', {})
                    if not materia_rel:
                        logger.debug(f"[IMPROVED] Estrutura 'Materia' não encontrada em relatoria para matéria {codigo_materia}")
                        return []
                    
                    # Verificar se há relatores na estrutura
                    if 'Relatoria' not in materia_rel:
                        # Se não há estrutura de relatoria, significa que o PL não tem relatores designados
                        logger.info(f"[IMPROVED] PL com código {codigo_materia} não possui relatores designados")
                        return []
                    
                    # Obter relatores
                    relatores_data = materia_rel['Relatoria']
                    
                    # Garantir que seja uma lista
                    if not isinstance(relatores_data, list):
                        if isinstance(relatores_data, dict) and relatores_data:
                            relatores_data = [relatores_data]
                        else:
                            # Se for None ou outro tipo inesperado
                            logger.warning(f"[IMPROVED] Estrutura de relatores inesperada: {type(relatores_data)}")
                            return []
                    
                    # Extrair dados relevantes, com verificações adicionais
                    relatores = []
                    for rel in relatores_data:
                        if not rel:  # Pular itens vazios
                            continue
                            
                        parlamentar = rel.get('Parlamentar', {}) or {}
                        comissao = rel.get('Comissao', {}) or {}
                        
                        # Verificar se temos informações mínimas necessárias
                        nome = parlamentar.get('NomeParlamentar', '')
                        if not nome:
                            # Se não temos o nome do parlamentar, pode ser um registro incompleto
                            continue
                        
                        relatores.append({
                            "Nome": nome,
                            "Partido": parlamentar.get('SiglaPartidoParlamentar', ''),
                            "UF": parlamentar.get('UfParlamentar', ''),
                            "Comissao": comissao.get('NomeComissao', ''),
                            "SiglaComissao": comissao.get('SiglaComissao', ''),
                            "DataDesignacao": rel.get('DataDesignacao', ''),
                            "DataDestituicao": rel.get('DataDestituicao', '')
                        })
                    
                    if not relatores:
                        logger.info(f"[IMPROVED] Nenhum relator válido encontrado para matéria {codigo_materia}")
                    else:
                        logger.info(f"[IMPROVED] Encontrados {len(relatores)} relatores para matéria {codigo_materia}")
                        
                    return relatores
                except Exception as e:
                    logger.error(f"[IMPROVED] Erro ao processar relatores da matéria {codigo_materia}: {str(e)}")
                    import traceback
                    logger.debug(f"[IMPROVED] Traceback: {traceback.format_exc()}")
                    return []
            else:
                # Se veio do cache, retorna diretamente
                return data
        
        def get_pl_by_id(self, sigla, numero, ano):
            """Versão melhorada que trata corretamente PLs sem relatores."""
            logger.info(f"[IMPROVED] Buscando PL {sigla} {numero}/{ano}")
            
            # Obter dados básicos com a implementação original
            pl_data = super().get_pl_by_id(sigla, numero, ano)
            
            # Processar relatores de forma melhorada
            if pl_data and "CodigoMateria" in pl_data:
                codigo_materia = pl_data["CodigoMateria"]
                try:
                    relatores = self.get_pl_relatores(codigo_materia)
                    
                    # Adicionar relatores apenas se houver algum
                    if relatores:
                        pl_data["Relatores"] = relatores
                        logger.info(f"[IMPROVED] Adicionados {len(relatores)} relatores ao PL {sigla} {numero}/{ano}")
                    else:
                        # Remover a chave "Relatores" se ela existir mas estiver vazia
                        if "Relatores" in pl_data:
                            del pl_data["Relatores"]
                        logger.info(f"[IMPROVED] PL {sigla} {numero}/{ano} não possui relatores designados")
                except Exception as e:
                    logger.error(f"[IMPROVED] Erro ao buscar relatores para PL {sigla} {numero}/{ano}: {str(e)}")
            
            return pl_data
        
        def _extract_relatores_from_tramitacao(self, tramitacao):
            """
            Extrai relatores a partir dos dados de tramitação quando o endpoint de relatoria falha.
            Esta função é uma adição na versão melhorada.
            """
            # Simplificada para o teste
            return []
    
    def compare_implementations(sigla, numero, ano):
        """
        Compara as implementações original e melhorada para o mesmo PL.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
        """
        pl_id = f"{sigla} {numero}/{ano}"
        logger.info(f"============= COMPARANDO IMPLEMENTAÇÕES PARA {pl_id} =============")
        
        # Instanciar APIs
        original_api = OriginalAPI()
        improved_api = ImprovedAPI()
        
        # Desativar cache para obter dados frescos
        original_api.set_cache_policy(False)
        improved_api.set_cache_policy(False)
        
        # Testar implementação original
        logger.info("Testando implementação ORIGINAL...")
        try:
            start_time = datetime.now()
            original_result = original_api.get_pl_by_id(sigla, numero, ano)
            end_time = datetime.now()
            original_duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Tempo de execução (original): {original_duration:.2f} segundos")
            
            # Analisar resultado
            if not original_result:
                logger.warning("Implementação original não encontrou o PL")
            else:
                # Verificar se há relatores
                if "Relatores" in original_result:
                    relatores = original_result["Relatores"]
                    if isinstance(relatores, list):
                        logger.info(f"Implementação original encontrou {len(relatores)} relatores")
                        for i, rel in enumerate(relatores):
                            logger.info(f"  Relator {i+1}: {rel.get('Nome', 'N/A')} ({rel.get('Partido', 'N/A')}/{rel.get('UF', 'N/A')})")
                    else:
                        logger.warning(f"Implementação original: Estrutura inesperada em Relatores: {type(relatores)}")
                else:
                    logger.info("Implementação original: Chave 'Relatores' não encontrada no resultado")
        except Exception as e:
            logger.error(f"Erro na implementação original: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            original_result = {"error": str(e)}
        
        # Testar implementação melhorada
        logger.info("\nTestando implementação MELHORADA...")
        try:
            start_time = datetime.now()
            improved_result = improved_api.get_pl_by_id(sigla, numero, ano)
            end_time = datetime.now()
            improved_duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Tempo de execução (melhorada): {improved_duration:.2f} segundos")
            
            # Analisar resultado
            if not improved_result:
                logger.warning("Implementação melhorada não encontrou o PL")
            else:
                # Verificar se há relatores
                if "Relatores" in improved_result:
                    relatores = improved_result["Relatores"]
                    if isinstance(relatores, list):
                        logger.info(f"Implementação melhorada encontrou {len(relatores)} relatores")
                        for i, rel in enumerate(relatores):
                            logger.info(f"  Relator {i+1}: {rel.get('Nome', 'N/A')} ({rel.get('Partido', 'N/A')}/{rel.get('UF', 'N/A')})")
                    else:
                        logger.warning(f"Implementação melhorada: Estrutura inesperada em Relatores: {type(relatores)}")
                else:
                    logger.info("Implementação melhorada: Chave 'Relatores' não está presente no resultado")
        except Exception as e:
            logger.error(f"Erro na implementação melhorada: {e}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
            improved_result = {"error": str(e)}
        
        # Comparar resultados
        logger.info("\n=== COMPARAÇÃO DE RESULTADOS ===")
        
        # Comparar presença de relatores
        original_has_relatores = "Relatores" in original_result
        improved_has_relatores = "Relatores" in improved_result
        
        if original_has_relatores == improved_has_relatores:
            if original_has_relatores:
                orig_rel_count = len(original_result["Relatores"])
                imp_rel_count = len(improved_result["Relatores"])
                
                if orig_rel_count == imp_rel_count:
                    logger.info(f"✅ Ambas implementações encontraram {orig_rel_count} relatores")
                else:
                    logger.warning(f"⚠️ Diferença no número de relatores: Original={orig_rel_count}, Melhorada={imp_rel_count}")
            else:
                logger.info("✅ Ambas implementações não encontraram relatores")
        else:
            logger.warning(f"⚠️ Diferença na presença de relatores: Original={'SIM' if original_has_relatores else 'NÃO'}, Melhorada={'SIM' if improved_has_relatores else 'NÃO'}")
        
        # Comparar campos principais
        main_fields = ["Título", "Autor", "Status", "Data"]
        for field in main_fields:
            if field in original_result and field in improved_result:
                if original_result[field] == improved_result[field]:
                    logger.info(f"✅ Campo '{field}' idêntico em ambas implementações")
                else:
                    logger.warning(f"⚠️ Diferença no campo '{field}'")
                    logger.warning(f"   Original: {original_result[field]}")
                    logger.warning(f"   Melhorada: {improved_result[field]}")
            else:
                if field in original_result:
                    logger.warning(f"⚠️ Campo '{field}' presente apenas na implementação original")
                elif field in improved_result:
                    logger.warning(f"⚠️ Campo '{field}' presente apenas na implementação melhorada")
                else:
                    logger.warning(f"⚠️ Campo '{field}' ausente em ambas implementações")
        
        # Comparar desempenho
        speedup = original_duration / improved_duration if improved_duration > 0 else float('inf')
        if speedup > 1:
            logger.info(f"✅ Implementação melhorada foi {speedup:.2f}x mais rápida")
        elif speedup < 1:
            logger.info(f"⚠️ Implementação melhorada foi {1/speedup:.2f}x mais lenta")
        else:
            logger.info("✅ Ambas implementações tiveram desempenho similar")
        
        # Salvar resultados completos para análise detalhada
        os.makedirs("comparison_results", exist_ok=True)
        
        with open(f"comparison_results/original_{sigla}_{numero}_{ano}.json", "w", encoding='utf-8') as f:
            json.dump(original_result, f, ensure_ascii=False, indent=2)
            
        with open(f"comparison_results/improved_{sigla}_{numero}_{ano}.json", "w", encoding='utf-8') as f:
            json.dump(improved_result, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Resultados completos salvos no diretório 'comparison_results'")
        
        # Conclusão
        logger.info("\n=== CONCLUSÃO ===")
        if not original_has_relatores and not improved_has_relatores:
            logger.info("✅ Diagnóstico: Este PL provavelmente não tem relatores designados no sistema do Senado")
        elif original_has_relatores and improved_has_relatores:
            logger.info("✅ Diagnóstico: Este PL tem relatores e ambas implementações os encontraram corretamente")
        elif improved_has_relatores and not original_has_relatores:
            logger.info("⚠️ Diagnóstico: Este PL tem relatores, mas apenas a implementação melhorada os encontrou")
        else:
            logger.info("⚠️ Diagnóstico: Este PL possivelmente tem relatores, mas apenas a implementação original os encontrou")
        
        logger.info(f"============= FIM DA COMPARAÇÃO PARA {pl_id} =============\n")

    # Executar a comparação para o PL problemático
    if __name__ == "__main__":
        # PL 3405/2023 - Relatado como problemático
        compare_implementations("PL", "3405", "2023")
        
        # PL 2234/2022 - Para comparação
        compare_implementations("PL", "2234", "2022")
        
except Exception as e:
    logger.error(f"Erro ao executar teste comparativo: {e}")
    import traceback
    logger.error(f"Traceback completo: {traceback.format_exc()}")