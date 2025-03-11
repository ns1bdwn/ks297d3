# src/ui/impact_analysis_view.py
"""
Interface para análise de impacto regulatório de PLs selecionados.
Foco no MVP para análise de PLs para iGaming com dados reais do Senado.
"""
import streamlit as st
import pandas as pd
import os
import sys
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import json
import logging

# Adicionar o diretório raiz ao path para importações relativas
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.intelligence.collectors.senado_api import SenadoAPI
from src.intelligence.analysis.pl_risk_analysis import PLRiskAnalyzer

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("impact_analysis_view")

def render_impact_analysis_view():
    """
    Renderiza a interface para análise de impacto regulatório de PLs.
    """
    st.write("### Análise de Impacto Regulatório")
    
    # Verificar se há PLs selecionados para análise
    if not st.session_state.get("analysis_pls", []):
        st.warning("Nenhum PL selecionado para análise. Por favor, selecione PLs na aba 'PLs Monitorados'.")
        if st.button("Ir para PLs Monitorados"):
            st.session_state.menu_option = "PLs Monitorados"
            st.rerun()
        return
    
    # Inicializar cliente da API do Senado e analisador de risco
    api = SenadoAPI()
    risk_analyzer = PLRiskAnalyzer()
    
    # Botão para forçar atualização dos dados
    col1, col2 = st.columns([1, 3])
    with col1:
        force_refresh = st.button("🔄 Atualizar Dados", help="Buscar dados atualizados na API do Senado")
    with col2:
        st.write("👉 **As análises são baseadas em dados reais da API do Senado Federal**")
    
    # Mostrar PLs selecionados
    st.write(f"#### PLs Selecionados para Análise ({len(st.session_state.analysis_pls)})")
    
    # Carregar detalhes dos PLs selecionados
    pls_details = {}
    risk_analyses = {}
    
    with st.spinner("Buscando dados atualizados e realizando análise de risco..."):
        for pl_id in st.session_state.analysis_pls:
            # Extrair sigla, número e ano do ID do PL
            parts = pl_id.split(" ")
            sigla = parts[0]
            numero_ano = parts[1].split("/")
            numero = numero_ano[0]
            ano = numero_ano[1]
            
            # Buscar detalhes do PL usando a API do Senado
            pl_details = api.get_pl_details(sigla, numero, ano)
            
            # Realizar análise de risco
            risk_analysis = risk_analyzer.analyze_pl_risk(sigla, numero, ano, force_refresh=force_refresh)
            
            if pl_details:
                pls_details[pl_id] = pl_details
                risk_analyses[pl_id] = risk_analysis
    
    # Análise de setor para todos os PLs selecionados
    if len(st.session_state.analysis_pls) > 1:
        st.write("### Análise do Setor")
        
        # Preparar dados para análise de setor
        sector_pls = []
        for pl_id in st.session_state.analysis_pls:
            parts = pl_id.split(" ")
            sigla = parts[0]
            numero_ano = parts[1].split("/")
            numero = numero_ano[0]
            ano = numero_ano[1]
            sector_pls.append({"Sigla": sigla, "Numero": numero, "Ano": ano})
        
        # Realizar análise de setor
        sector_analysis = risk_analyzer.get_sector_risk_overview(sector_pls)
        
        # Mostrar overview do setor
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Risco Médio", f"{sector_analysis['risco_medio']:.1f}%", f"{sector_analysis['nivel_risco_medio']}")
        
        with col2:
            st.metric("PLs de Alto Risco", f"{sector_analysis['distribuicao_risco']['alto_risco']}", 
                    f"{sector_analysis['distribuicao_risco']['alto_risco']/len(sector_pls)*100:.0f}%")
        
        with col3:
            st.metric("PLs Analisados", f"{sector_analysis['numero_pls_analisados']}", "")
        
        # PLs de alto risco
        if sector_analysis['pls_alto_risco']:
            st.subheader("PLs de Alto Risco")
            
            for pl in sector_analysis['pls_alto_risco']:
                st.markdown(f"- **{pl['pl_id']}** ({pl['score']:.1f}%): {pl['titulo'][:100]}...")
        
        # Eventos críticos
        if sector_analysis['proximos_eventos_criticos']:
            st.subheader("Próximos Eventos Críticos")
            
            for event in sector_analysis['proximos_eventos_criticos']:
                st.markdown(f"- **{event['pl_id']}**: {event['evento']} (Probabilidade: {event['probabilidade']})")
                st.caption(f"{event['observacao']}")
        
        st.markdown("---")
    
    # Para cada PL selecionado, mostrar uma análise
    for pl_id, pl_details in pls_details.items():
        # Obter análise de risco correspondente
        risk_analysis = risk_analyses.get(pl_id, {})
        
        # Container para cada PL
        with st.expander(f"{pl_id} - {pl_details.get('Título', '')[:100]}...", expanded=True):
            # Informações básicas
            st.write(f"**Autor:** {pl_details.get('Autor', 'N/A')}")
            st.write(f"**Status:** {pl_details.get('Status', 'N/A')}")
            
            # Link para texto completo
            if pl_details.get('URL'):
                st.write(f"**Texto Completo:** [Acessar]({pl_details.get('URL')})")
            
            # Título completo (ementa)
            st.write("**Ementa:**")
            st.info(pl_details.get('Título', 'N/A'))
            
            # Mostrar análise de risco
            st.write("#### Análise de Risco Regulatório")
            
            # Risco de aprovação
            risk_info = risk_analysis.get('risco_aprovacao', {})
            risk_score = risk_info.get('score', 0)
            risk_level = risk_info.get('nivel', 'N/A')
            
            # Cor baseada no risco
            risk_color = "green"
            if risk_score > 40:
                risk_color = "orange"
            if risk_score > 60:
                risk_color = "red"
            
            # Mostrar medidor de risco
            st.write("**Risco de Aprovação:**")
            st.progress(risk_score/100)
            st.markdown(f"<h3 style='text-align: center; color: {risk_color};'>{risk_score:.1f}% - {risk_level}</h3>", unsafe_allow_html=True)
            
            # Mostrar fatores de risco (sem usar expander aninhado)
            st.write("**Fatores de Risco:**")
            risk_factors = risk_info.get('fatores', [])
            if risk_factors:
                # Criar uma tabela simples
                for factor in risk_factors:
                    st.markdown(f"- **{factor['fator']}:** {factor['descricao']} ({factor['impacto']})")
                    st.caption(f"  *{factor['explicacao']}*")
            else:
                st.info("Nenhum fator de risco identificado.")
            
            # Mostrar tempo estimado
            time_info = risk_analysis.get('tempo_estimado', {})
            time_estimate = time_info.get('estimativa', 'N/A')
            
            st.write(f"**Tempo Estimado para Aprovação:** {time_estimate}")
            
            # Mostrar próximos passos
            st.write("**Próximos Passos Prováveis:**")
            for step in risk_analysis.get('proximos_passos', [])[:3]:
                prob_color = "green"
                if step['probabilidade'] == "Média":
                    prob_color = "orange"
                if step['probabilidade'] == "Alta":
                    prob_color = "red"
                
                st.markdown(f"- {step['passo']} - <span style='color: {prob_color};'>Probabilidade: {step['probabilidade']}</span>", unsafe_allow_html=True)
                st.caption(step['observacao'])
            
            # Mostrar últimos eventos (sem usar expander aninhado)
            if risk_analysis.get('ultimos_eventos'):
                st.write("**Últimos Eventos da Tramitação:**")
                for evento in risk_analysis.get('ultimos_eventos'):
                    st.markdown(f"- **{evento.get('Data', 'N/A')}:** {evento.get('Situacao', 'N/A')} ({evento.get('Local', 'N/A')})")
                    if evento.get('Texto'):
                        st.caption(f"  *{evento.get('Texto')}*")
            
            # Separador
            st.markdown("---")
            
            # Interface para análise de impacto na empresa
            st.write("#### Análise de Impacto na Empresa")
            
            # Verificar se já existe análise salva
            client_id = st.session_state.client_id
            analysis_file = os.path.join("data", "clients", client_id, f"impact_{pl_id.replace(' ', '_').replace('/', '_')}.json")
            
            saved_analysis = {}
            if os.path.exists(analysis_file):
                try:
                    with open(analysis_file, "r", encoding="utf-8") as f:
                        saved_analysis = json.load(f)
                    st.success("Análise de impacto carregada do histórico.")
                except Exception as e:
                    logger.error(f"Erro ao carregar análise: {str(e)}")
            
            # Formulário para análise
            with st.form(f"impact_analysis_{pl_id}"):
                st.subheader("1. Identificação do Problema Regulatório")
                
                problema = st.text_area(
                    "Descrição do problema",
                    value=saved_analysis.get("problema", ""),
                    height=100,
                    placeholder="Descreva o problema regulatório que este PL busca resolver..."
                )
                
                st.subheader("2. Objetivos da Regulação")
                
                objetivos = st.text_area(
                    "Objetivos",
                    value=saved_analysis.get("objetivos", ""),
                    height=100,
                    placeholder="Descreva os principais objetivos desta regulação..."
                )
                
                st.subheader("3. Avaliação de Impacto na Empresa")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    impacto_nivel = st.selectbox(
                        "Nível de Impacto Geral",
                        options=["Alto", "Médio", "Baixo"],
                        index=["Alto", "Médio", "Baixo"].index(saved_analysis.get("impacto_nivel", "Médio"))
                    )
                
                with col2:
                    prazo_adaptacao = st.selectbox(
                        "Prazo para Adaptação",
                        options=["Imediato", "Curto (até 3 meses)", "Médio (3-6 meses)", "Longo (6+ meses)"],
                        index=["Imediato", "Curto (até 3 meses)", "Médio (3-6 meses)", "Longo (6+ meses)"].index(
                            saved_analysis.get("prazo_adaptacao", "Médio (3-6 meses)")
                        )
                    )
                
                # Área de impacto com slider
                st.write("#### Áreas de Impacto")
                
                areas_impacto = {
                    "Operações": st.slider(
                        "Operações",
                        min_value=1,
                        max_value=5,
                        value=saved_analysis.get("areas_impacto", {}).get("Operações", 3),
                        help="1: Impacto mínimo, 5: Impacto crítico"
                    ),
                    "Tecnologia": st.slider(
                        "Tecnologia",
                        min_value=1,
                        max_value=5,
                        value=saved_analysis.get("areas_impacto", {}).get("Tecnologia", 3),
                        help="1: Impacto mínimo, 5: Impacto crítico"
                    ),
                    "Compliance": st.slider(
                        "Compliance",
                        min_value=1,
                        max_value=5,
                        value=saved_analysis.get("areas_impacto", {}).get("Compliance", 3),
                        help="1: Impacto mínimo, 5: Impacto crítico"
                    ),
                    "Financeiro": st.slider(
                        "Financeiro",
                        min_value=1,
                        max_value=5,
                        value=saved_analysis.get("areas_impacto", {}).get("Financeiro", 3),
                        help="1: Impacto mínimo, 5: Impacto crítico"
                    ),
                    "Marketing": st.slider(
                        "Marketing",
                        min_value=1,
                        max_value=5,
                        value=saved_analysis.get("areas_impacto", {}).get("Marketing", 3),
                        help="1: Impacto mínimo, 5: Impacto crítico"
                    )
                }
                
                st.subheader("4. Análise de Custo-Benefício")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Custos Estimados**")
                    
                    custo_implementacao = st.text_input(
                        "Custo de Implementação (R$)",
                        value=saved_analysis.get("custo_implementacao", ""),
                        placeholder="Ex: 100000"
                    )
                    
                    custo_manutencao = st.text_input(
                        "Custo de Manutenção Anual (R$)",
                        value=saved_analysis.get("custo_manutencao", ""),
                        placeholder="Ex: 50000"
                    )
                
                with col2:
                    st.write("**Benefícios Potenciais**")
                    
                    beneficios = st.text_area(
                        "Benefícios",
                        value=saved_analysis.get("beneficios", ""),
                        height=100,
                        placeholder="Descreva os potenciais benefícios para a empresa..."
                    )
                
                st.subheader("5. Ações Recomendadas")
                
                acoes_recomendadas = st.text_area(
                    "Ações Recomendadas",
                    value=saved_analysis.get("acoes_recomendadas", ""),
                    height=150,
                    placeholder="Descreva as ações recomendadas para adequação à regulação..."
                )
                
                # Incorporar risco regulatório na análise
                st.subheader("6. Risco Regulatório")
                
                st.info(f"""
                Segundo a análise automática, este PL tem:
                - Risco de aprovação: {risk_score:.1f}% ({risk_level})
                - Tempo estimado para aprovação: {time_estimate}
                """)
                
                observacoes_risco = st.text_area(
                    "Observações sobre o Risco Regulatório",
                    value=saved_analysis.get("observacoes_risco", ""),
                    height=100,
                    placeholder="Adicione observações sobre o risco regulatório identificado..."
                )
                
                # Botão para salvar análise
                submitted = st.form_submit_button("Salvar Análise", use_container_width=True)
                
                if submitted:
                    # Preparar dados para salvar
                    analysis_data = {
                        "pl_id": pl_id,
                        "data_analise": datetime.now().isoformat(),
                        "problema": problema,
                        "objetivos": objetivos,
                        "impacto_nivel": impacto_nivel,
                        "prazo_adaptacao": prazo_adaptacao,
                        "areas_impacto": areas_impacto,
                        "custo_implementacao": custo_implementacao,
                        "custo_manutencao": custo_manutencao,
                        "beneficios": beneficios,
                        "acoes_recomendadas": acoes_recomendadas,
                        "risco_aprovacao": risk_score,
                        "nivel_risco": risk_level,
                        "tempo_estimado": time_estimate,
                        "observacoes_risco": observacoes_risco
                    }
                    
                    # Salvar análise
                    try:
                        # Garantir que o diretório existe
                        os.makedirs(os.path.dirname(analysis_file), exist_ok=True)
                        
                        with open(analysis_file, "w", encoding="utf-8") as f:
                            json.dump(analysis_data, f, ensure_ascii=False, indent=4)
                        
                        st.success("Análise de impacto salva com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar análise: {str(e)}")
                        logger.error(f"Erro ao salvar análise: {str(e)}")
            
            # Se já tiver análise salva, mostrar visualizações
            if saved_analysis:
                st.write("#### Visualização de Impacto")
                
                # Gráfico de radar para áreas de impacto
                if "areas_impacto" in saved_analysis:
                    areas = list(saved_analysis["areas_impacto"].keys())
                    valores = list(saved_analysis["areas_impacto"].values())
                    
                    # Gráfico de radar
                    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
                    
                    # Número de variáveis
                    N = len(areas)
                    
                    # Ângulos para cada eixo (igualmente espaçados)
                    angles = [n / float(N) * 2 * np.pi for n in range(N)]
                    angles += angles[:1]  # Fechar o gráfico
                    
                    # Valores
                    valores_plot = valores + [valores[0]]  # Repetir o primeiro valor para fechar o gráfico
                    
                    # Desenhar linhas de grade
                    ax.set_xticks(angles[:-1])
                    ax.set_xticklabels(areas)
                    ax.set_yticks([1, 2, 3, 4, 5])
                    ax.set_ylim(0, 5)
                    
                    # Plotar dados
                    ax.plot(angles, valores_plot, linewidth=2, linestyle='solid', color='#366092')
                    ax.fill(angles, valores_plot, alpha=0.25, color='#366092')
                    
                    st.pyplot(fig)
                
                # Resumo de recomendações
                if saved_analysis.get("acoes_recomendadas"):
                    st.write("#### Resumo de Recomendações")
                    st.info(saved_analysis["acoes_recomendadas"])
                
                # Botão para gerar relatório PDF (simulação)
                if st.button("Gerar Relatório PDF"):
                    st.info("Esta funcionalidade seria implementada em uma versão futura.")
                    st.success("Simulação: Relatório PDF gerado com sucesso!")
            
            # Link para remover este PL da lista de análise
            if st.button(f"Remover {pl_id} da Análise", key=f"remove_{pl_id}"):
                st.session_state.analysis_pls.remove(pl_id)
                st.success(f"PL {pl_id} removido da análise.")
                st.rerun()
    
    # Se não houver PLs selecionados após processamento (por exemplo, após remover um)
    if not pls_details:
        st.warning("Nenhum PL disponível para análise. Por favor, selecione PLs na aba 'PLs Monitorados'.")
        if st.button("Ir para PLs Monitorados"):
            st.session_state.menu_option = "PLs Monitorados"
            st.rerun()

# Função para executar diretamente (teste)
if __name__ == "__main__":
    # Configurar sessão para teste
    if "analysis_pls" not in st.session_state:
        st.session_state.analysis_pls = ["PL 2234/2022", "PL 3405/2023"]
    
    if "client_id" not in st.session_state:
        st.session_state.client_id = "test_client"
        
    render_impact_analysis_view()