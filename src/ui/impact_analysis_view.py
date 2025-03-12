# src/ui/impact_analysis_view.py
"""
Interface para análise de impacto regulatório de PLs.
Permite visualizar riscos, estimar prazos e entender impactos potenciais.
"""
import streamlit as st
import pandas as pd
import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional

# Adicionar o diretório raiz ao path para importações relativas
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importar componentes necessários
from src.intelligence.utils.predefined_pls import PredefinedPLManager

# Tenta importar o analisador de riscos
try:
    from src.intelligence.analysis.pl_risk_analysis import PLRiskAnalyzer
except ImportError:
    # Fallback para caso de erro de importação
    class PLRiskAnalyzer:
        def __init__(self, data_dir=None):
            self.data_dir = data_dir or os.path.join(os.getcwd(), "data", "risk_analysis")
            os.makedirs(self.data_dir, exist_ok=True)
            
        def analyze_pl_risk(self, sigla, numero, ano, force_refresh=False):
            try:
                # Tentar usar o collector básico para obter dados
                from src.intelligence.collectors.senado_collector import SenadoCollector
                collector = SenadoCollector()
                pl_dados = collector.get_pl_by_id(sigla, numero, ano)
                
                if pl_dados:
                    # Extrai informações básicas do PL para criar análise simples
                    return {
                        "pl_id": f"{sigla} {numero}/{ano}",
                        "timestamp": datetime.now().timestamp(),
                        "data_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "titulo": pl_dados.get("Título", "Título não disponível"),
                        "autor": pl_dados.get("Autor", "Não informado"),
                        "status_atual": {
                            "local": pl_dados.get("Status", "").split(" - ")[1] if " - " in pl_dados.get("Status", "") else "",
                            "situacao": pl_dados.get("Status", "").split(" - ")[0] if " - " in pl_dados.get("Status", "") else pl_dados.get("Status", ""),
                            "data": pl_dados.get("Data", "")
                        },
                        "risco_aprovacao": {
                            "score": 50, 
                            "nivel": "Médio", 
                            "fatores": [
                                {"fator": "Análise simplificada", 
                                 "descricao": "Usando dados básicos do collector", 
                                 "impacto": "Neutro",
                                 "explicacao": "Analisador completo não disponível, usando estimativa básica"}
                            ]
                        },
                        "tempo_estimado": {
                            "estimativa": "6-12 meses", 
                            "fatores": [
                                {"fator": "Estimativa padrão", 
                                 "descricao": "Baseado em tempo médio de tramitação no Congresso", 
                                 "impacto": "Neutro",
                                 "explicacao": "Analisador completo não disponível, usando estimativa padrão"}
                            ]
                        },
                        "proximos_passos": [
                            {"passo": "Análise em comissões", 
                             "probabilidade": "Média", 
                             "observacao": "Processo padrão de tramitação",
                             "contexto": "Análise simplificada, sem avaliação detalhada"
                            },
                            {"passo": "Votação em plenário", 
                             "probabilidade": "Baixa", 
                             "observacao": "Após análise em comissões",
                             "contexto": "Processo padrão de tramitação legislativa"
                            }
                        ],
                        "analise_politica": {
                            "tendencia": "Indefinida", 
                            "contexto_politico": f"PL apresentado por {pl_dados.get('Autor', 'autor não identificado')}. Status atual: {pl_dados.get('Status', 'não disponível')}.", 
                            "impacto_setorial": "Análise completa indisponível. Recomenda-se avaliar o texto completo do PL."
                        },
                        "ultimos_eventos": [],
                        "detalhes_autoria": [
                            {
                                "nome": pl_dados.get("Autor", "Não informado"),
                                "tipo": "Parlamentar" if "Senador" in pl_dados.get("Autor", "") or "Deputado" in pl_dados.get("Autor", "") else "Não identificado",
                                "partido": "",
                                "uf": ""
                            }
                        ]
                    }
            except Exception as e:
                logger.error(f"Erro no fallback: {str(e)}")
                
            # Fallback padrão se tudo falhar
            return {
                "pl_id": f"{sigla} {numero}/{ano}",
                "timestamp": datetime.now().timestamp(),
                "data_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "titulo": "PL não disponível para análise detalhada",
                "autor": "Não disponível",
                "status_atual": {"local": "", "situacao": "Não disponível", "data": ""},
                "risco_aprovacao": {"score": 50, "nivel": "Médio", "fatores": []},
                "tempo_estimado": {"estimativa": "Não disponível", "fatores": []},
                "proximos_passos": [{"passo": "Análise não disponível", "probabilidade": "N/A", "observacao": "Componente de análise não carregado"}],
                "analise_politica": {"tendencia": "Indefinida", "contexto_politico": "Não disponível", "impacto_setorial": "Não disponível"}
            }

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
    st.write("Avalie o impacto potencial de projetos de lei no seu negócio.")
    
    # Inicializar gerenciador de PLs e analisador de riscos
    pl_manager = PredefinedPLManager()
    risk_analyzer = PLRiskAnalyzer()
    
    # Verificar se há PLs selecionados para análise
    if "analysis_pls" not in st.session_state:
        st.session_state.analysis_pls = []
    
    if "current_analysis_pl" not in st.session_state:
        st.session_state.current_analysis_pl = None
    
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = {}
    
    # Verificar se temos PLs para analisar
    if not st.session_state.analysis_pls:
        st.info("Nenhum PL selecionado para análise. Selecione PLs na seção 'PLs Monitorados' ou adicione manualmente.")
        
        # Formulário para adicionar PL manualmente
        st.write("#### Adicionar PL para Análise")
        with st.form("add_pl_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sigla = st.selectbox(
                    "Tipo",
                    options=["PL", "PEC", "PLP", "PDL", "PDS", "MPV"],
                    index=0
                )
            
            with col2:
                numero = st.text_input("Número", placeholder="Ex: 1234")
            
            with col3:
                ano = st.text_input("Ano", placeholder="Ex: 2023")
            
            submit = st.form_submit_button("Adicionar PL", use_container_width=True)
            
            if submit:
                if not numero or not ano:
                    st.error("Número e Ano são obrigatórios.")
                else:
                    pl_id = f"{sigla} {numero}/{ano}"
                    if pl_id not in st.session_state.analysis_pls:
                        st.session_state.analysis_pls.append(pl_id)
                        st.success(f"PL {pl_id} adicionado para análise!")
                        st.rerun()
        
        # Exibir PLs pré-definidos se não houver PLs selecionados
        st.write("#### PLs Monitorados (selecione para análise)")
        pls_df = pl_manager.get_pl_details_dataframe()
        
        if not pls_df.empty:
            # Mostrar PLs pré-definidos com botão para adicionar à análise
            for i, row in pls_df.head(5).iterrows():
                pl_id = row['ID']
                with st.container():
                    col1, col2 = st.columns([9, 1])
                    with col1:
                        st.write(f"**{pl_id}**: {row['Título'][:100]}...")
                    with col2:
                        if st.button("Analisar", key=f"add_{pl_id}"):
                            if pl_id not in st.session_state.analysis_pls:
                                st.session_state.analysis_pls.append(pl_id)
                                st.success(f"PL {pl_id} adicionado para análise!")
                                st.rerun()
            
            if len(pls_df) > 5:
                st.write(f"...e mais {len(pls_df) - 5} PLs (acesse a seção 'PLs Monitorados' para ver todos)")
        else:
            st.info("Nenhum PL pré-definido encontrado. Adicione PLs na seção 'PLs Monitorados'.")
    else:
        # Há PLs para analisar
        st.write(f"#### PLs Selecionados para Análise ({len(st.session_state.analysis_pls)})")
        
        # Interface de duas colunas para análise
        col1, col2 = st.columns([3, 7])
        
        with col1:
            # Lista de PLs selecionados
            st.write("**Selecione um PL para ver detalhes:**")
            
            for pl_id in st.session_state.analysis_pls:
                # Extrair informações do PL
                parts = pl_id.split()
                if len(parts) < 2:
                    continue
                    
                sigla = parts[0]
                numero_ano = parts[1].split("/")
                if len(numero_ano) < 2:
                    continue
                    
                numero, ano = numero_ano[0], numero_ano[1]
                
                # Verificar se já temos resultados para este PL
                has_analysis = pl_id in st.session_state.analysis_results
                
                # Botão para selecionar este PL
                button_label = f"{pl_id}" + (" ✓" if has_analysis else "")
                if st.button(button_label, key=f"select_{pl_id}", use_container_width=True):
                    st.session_state.current_analysis_pl = pl_id
                    
                    # Analisar o PL se ainda não foi analisado
                    if not has_analysis:
                        try:
                            with st.spinner(f"Analisando impacto do {pl_id}..."):
                                analysis = risk_analyzer.analyze_pl_risk(sigla, numero, ano)
                                if analysis and 'error' not in analysis:
                                    st.session_state.analysis_results[pl_id] = analysis
                                    st.success(f"Análise do {pl_id} concluída!")
                                else:
                                    st.error(f"Não foi possível analisar o PL {pl_id}.")
                        except Exception as e:
                            logger.error(f"Erro ao analisar PL {pl_id}: {str(e)}")
                            st.error(f"Erro ao analisar PL {pl_id}: {str(e)}")
            
            # Botão para limpar seleção
            if st.button("Limpar Seleção", use_container_width=True):
                st.session_state.analysis_pls = []
                st.session_state.current_analysis_pl = None
                st.session_state.analysis_results = {}
                st.rerun()
            
            # Botão para análise comparativa se houver mais de um PL
            if len(st.session_state.analysis_pls) > 1 and len(st.session_state.analysis_results) > 1:
                if st.button("Análise Comparativa", use_container_width=True):
                    st.session_state.current_analysis_pl = "comparative"
            
            # Botão para análise setorial se houver mais de 2 PLs analisados
            if len(st.session_state.analysis_results) >= 3:
                if st.button("Visão Setorial", use_container_width=True):
                    st.session_state.current_analysis_pl = "sector"
        
        with col2:
            # Área principal de análise
            if st.session_state.current_analysis_pl == "comparative":
                _render_comparative_analysis()
            elif st.session_state.current_analysis_pl == "sector":
                _render_sector_analysis()
            elif st.session_state.current_analysis_pl in st.session_state.analysis_results:
                _render_pl_analysis(st.session_state.current_analysis_pl)
            else:
                st.info("Selecione um PL à esquerda para ver sua análise de impacto, ou adicione novos PLs para análise.")

def _render_pl_analysis(pl_id):
    """
    Renderiza a análise detalhada de um PL.
    
    Args:
        pl_id: ID do PL a ser analisado
    """
    # Obter dados da análise
    analysis = st.session_state.analysis_results.get(pl_id, {})
    
    if not analysis:
        st.error(f"Dados de análise não encontrados para o PL {pl_id}.")
        return
    
    # Dados básicos do PL
    st.write(f"### Análise de Impacto: {pl_id}")
    st.write(f"**{analysis.get('titulo', 'Título não disponível')}**")
    
    # Detalhes em abas
    tab1, tab2, tab3, tab4 = st.tabs(["Visão Geral", "Análise de Risco", "Próximos Passos", "Análise Política"])
    
    with tab1:
        # Visão geral com métricas principais
        st.write("#### Resumo do Impacto")
        
        # Status atual
        status_atual = analysis.get('status_atual', {})
        status_local = status_atual.get('local', 'Não disponível')
        status_situacao = status_atual.get('situacao', 'Não disponível')
        
        st.write(f"**Status Atual:** {status_situacao} ({status_local})")
        st.write(f"**Autor:** {analysis.get('autor', 'Não disponível')}")
        
        # Métricas de risco e tempo
        col1, col2 = st.columns(2)
        
        with col1:
            risco = analysis.get('risco_aprovacao', {})
            risk_score = risco.get('score', 0)
            risk_level = risco.get('nivel', 'Não disponível')
            
            # Cor baseada no nível de risco
            if risk_score >= 70:
                risk_color = "red"
            elif risk_score >= 50:
                risk_color = "orange"
            elif risk_score >= 30:
                risk_color = "#CCCC00"  # Amarelo escuro
            else:
                risk_color = "green"
            
            st.markdown(
                f"<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center;'>"
                f"<div style='font-size: 48px; font-weight: bold; color: {risk_color};'>{risk_score:.0f}%</div>"
                f"<div style='font-size: 20px;'>Risco de Aprovação</div>"
                f"<div style='font-size: 16px;'>Nível: {risk_level}</div>"
                "</div>",
                unsafe_allow_html=True
            )
        
        with col2:
            tempo = analysis.get('tempo_estimado', {})
            estimativa = tempo.get('estimativa', 'Não disponível')
            
            st.markdown(
                f"<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center;'>"
                f"<div style='font-size: 32px; font-weight: bold; color: #366092;'>{estimativa}</div>"
                f"<div style='font-size: 20px;'>Tempo Estimado</div>"
                f"<div style='font-size: 16px;'>para aprovação</div>"
                "</div>",
                unsafe_allow_html=True
            )
        
        # Tendência política
        tendencia = analysis.get('analise_politica', {}).get('tendencia', 'Indefinida')
        tendencia_color = "#366092" if tendencia == "Favorável" else "#ED7D31" if tendencia == "Neutra" else "#A50000"
        
        st.markdown(
            f"<div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-top: 20px;'>"
            f"<div style='font-size: 18px; font-weight: bold;'>Tendência Política: <span style='color: {tendencia_color};'>{tendencia}</span></div>"
            "</div>",
            unsafe_allow_html=True
        )
        
        # Próximos passos críticos
        st.write("#### Próximos Passos Críticos")
        
        proximos_passos = analysis.get('proximos_passos', [])
        if proximos_passos:
            # Mostrar apenas os 2 primeiros passos com alta probabilidade
            passos_alta_prob = [p for p in proximos_passos if p.get('probabilidade') == 'Alta'][:2]
            
            if passos_alta_prob:
                for i, passo in enumerate(passos_alta_prob):
                    st.markdown(
                        f"<div style='background-color: #f8f8f8; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                        f"<div style='font-weight: bold;'>{i+1}. {passo.get('passo')}</div>"
                        f"<div>{passo.get('observacao')}</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
            else:
                # Se não houver passos de alta probabilidade, mostrar os 2 primeiros
                for i, passo in enumerate(proximos_passos[:2]):
                    st.markdown(
                        f"<div style='background-color: #f8f8f8; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                        f"<div style='font-weight: bold;'>{i+1}. {passo.get('passo')} ({passo.get('probabilidade')})</div>"
                        f"<div>{passo.get('observacao')}</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
        else:
            st.info("Não há informações sobre próximos passos.")
        
        # Últimos eventos de tramitação
        st.write("#### Últimos Eventos")
        
        ultimos_eventos = analysis.get('ultimos_eventos', [])
        if ultimos_eventos:
            for evento in ultimos_eventos[:3]:  # Limitar a 3 eventos
                data = evento.get('Data', '')
                local = evento.get('Local', '')
                situacao = evento.get('Situacao', '')
                
                st.markdown(
                    f"<div style='background-color: #f8f8f8; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                    f"<div style='font-size: 14px; color: #666;'>{data}</div>"
                    f"<div style='font-weight: bold;'>{local}</div>"
                    f"<div>{situacao}</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Não há informações sobre eventos de tramitação.")
    
    with tab2:
        # Análise de risco detalhada
        st.write("#### Análise Detalhada de Risco")
        
        risco = analysis.get('risco_aprovacao', {})
        risk_score = risco.get('score', 0)
        risk_level = risco.get('nivel', 'Não disponível')
        risk_factors = risco.get('fatores', [])
        
        # Gráfico de score
        fig, ax = plt.subplots(figsize=(10, 2))
        
        # Escala de cores para o gráfico
        colors = ["green", "#CCCC00", "orange", "red"]
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        
        # Barras de percentil
        for i in range(4):
            ax.axvspan(i*25, (i+1)*25, color=colors[i], alpha=0.3)
        
        # Marcador de posição
        ax.axvline(x=risk_score, color='black', linewidth=3)
        
        # Texto de valor
        ax.text(risk_score, 0.5, f"{risk_score:.0f}%", 
                horizontalalignment='center', verticalalignment='center', 
                fontsize=14, fontweight='bold', color='black')
        
        # Rótulos
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        
        # Remover bordas
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        st.pyplot(fig)
        
        # Fatores que contribuem para o score
        st.write("**Fatores que contribuem para o risco:**")
        
        if risk_factors:
            for fator in risk_factors:
                # Determinar ícone e cor com base no impacto
                impacto = fator.get('impacto', '')
                if "+" in impacto:
                    icon = "⬆️"
                    color = "red"  # Aumenta o risco
                elif "-" in impacto:
                    icon = "⬇️"
                    color = "green"  # Diminui o risco
                else:
                    icon = "⚖️"
                    color = "gray"  # Neutro
                
                st.markdown(
                    f"<div style='display: flex; align-items: flex-start; margin-bottom: 15px;'>"
                    f"<div style='font-size: 24px; margin-right: 10px;'>{icon}</div>"
                    f"<div>"
                    f"<div style='font-weight: bold;'>{fator.get('fator')}</div>"
                    f"<div>{fator.get('descricao')}</div>"
                    f"<div style='color: {color}; font-weight: bold;'>{impacto}</div>"
                    f"<div style='font-size: 14px; font-style: italic;'>{fator.get('explicacao', '')}</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Não há informações sobre fatores de risco.")
        
        # Tempo estimado
        st.write("#### Tempo Estimado para Aprovação")
        
        tempo = analysis.get('tempo_estimado', {})
        estimativa = tempo.get('estimativa', 'Não disponível')
        time_factors = tempo.get('fatores', [])
        
        st.markdown(
            f"<div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>"
            f"<div style='font-size: 24px; font-weight: bold;'>{estimativa}</div>"
            "</div>",
            unsafe_allow_html=True
        )
        
        # Fatores que afetam o tempo
        st.write("**Fatores que afetam o tempo estimado:**")
        
        if time_factors:
            for fator in time_factors:
                st.markdown(
                    f"<div style='background-color: #f8f8f8; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                    f"<div style='font-weight: bold;'>{fator.get('fator')}</div>"
                    f"<div>{fator.get('descricao')}</div>"
                    f"<div style='font-weight: bold;'>Impacto: {fator.get('impacto')}</div>"
                    f"<div style='font-size: 14px; font-style: italic;'>{fator.get('explicacao', '')}</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Não há informações sobre fatores que afetam o tempo.")
    
    with tab3:
        # Próximos passos detalhados
        st.write("#### Próximos Passos Prováveis")
        
        proximos_passos = analysis.get('proximos_passos', [])
        
        if proximos_passos:
            for i, passo in enumerate(proximos_passos):
                # Determinar cor com base na probabilidade
                prob = passo.get('probabilidade', '')
                if prob == 'Alta':
                    color = "red"  # Alta probabilidade
                elif prob == 'Média':
                    color = "orange"  # Média probabilidade
                else:
                    color = "gray"  # Baixa ou indefinida
                
                st.markdown(
                    f"<div style='background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 15px;'>"
                    f"<div style='font-size: 18px; font-weight: bold;'>{i+1}. {passo.get('passo')}</div>"
                    f"<div style='color: {color}; font-weight: bold; margin: 5px 0;'>Probabilidade: {prob}</div>"
                    f"<div style='margin-bottom: 10px;'>{passo.get('observacao')}</div>"
                    f"<div style='font-size: 14px; font-style: italic; background-color: #eef;padding: 10px; border-radius: 5px;'>"
                    f"<strong>Contexto:</strong> {passo.get('contexto', 'Não disponível')}</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Não há informações sobre próximos passos.")
    
    with tab4:
        # Análise política e contexto
        st.write("#### Análise Política e Contexto")
        
        analise_politica = analysis.get('analise_politica', {})
        tendencia = analise_politica.get('tendencia', 'Indefinida')
        contexto_politico = analise_politica.get('contexto_politico', 'Não disponível')
        impacto_setorial = analise_politica.get('impacto_setorial', 'Não disponível')
        
        # Tendência política
        tendencia_color = "#366092" if tendencia == "Favorável" else "#ED7D31" if tendencia == "Neutra" else "#A50000"
        
        st.markdown(
            f"<div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>"
            f"<div style='font-size: 20px; font-weight: bold;'>Tendência Política: <span style='color: {tendencia_color};'>{tendencia}</span></div>"
            "</div>",
            unsafe_allow_html=True
        )
        
        # Contexto político
        st.write("**Contexto Político:**")
        st.markdown(
            f"<div style='background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>"
            f"{contexto_politico}"
            "</div>",
            unsafe_allow_html=True
        )
        
        # Impacto setorial
        st.write("**Impacto Setorial:**")
        st.markdown(
            f"<div style='background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>"
            f"{impacto_setorial}"
            "</div>",
            unsafe_allow_html=True
        )
        
        # Autoria detalhada
        st.write("**Detalhes de Autoria:**")
        
        autores = analysis.get('detalhes_autoria', [])
        if autores:
            for autor in autores:
                nome = autor.get('nome', 'Não informado')
                tipo = autor.get('tipo', '')
                partido = autor.get('partido', '')
                uf = autor.get('uf', '')
                
                info_adicional = ""
                if partido and uf:
                    info_adicional = f" ({partido}/{uf})"
                elif partido:
                    info_adicional = f" ({partido})"
                elif uf:
                    info_adicional = f" ({uf})"
                
                st.markdown(
                    f"<div style='background-color: #f8f8f8; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                    f"<div style='font-weight: bold;'>{nome}{info_adicional}</div>"
                    f"<div>Tipo: {tipo}</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Não há informações detalhadas sobre autoria.")
        
        # Projetos relacionados
        st.write("**Projetos Relacionados:**")
        
        projetos_relacionados = analysis.get('projetos_relacionados', [])
        if projetos_relacionados:
            for projeto in projetos_relacionados:
                pl_id = projeto.get('ID', '')
                titulo = projeto.get('Título', '')
                status = projeto.get('Status', '')
                
                st.markdown(
                    f"<div style='background-color: #f8f8f8; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>"
                    f"<div style='font-weight: bold;'>{pl_id}</div>"
                    f"<div>{titulo[:100]}...</div>"
                    f"<div>Status: {status}</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("Não foram encontrados projetos relacionados.")
    
    # Rodapé com informações da análise
    st.caption(f"Análise atualizada em: {analysis.get('data_atualizacao', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")

def _render_comparative_analysis():
    """
    Renderiza uma análise comparativa entre múltiplos PLs.
    """
    st.write("### Análise Comparativa de PLs")
    
    # Verificar se temos PLs suficientes para comparar
    analyzed_pls = st.session_state.analysis_results
    if len(analyzed_pls) < 2:
        st.warning("É necessário ter pelo menos 2 PLs analisados para fazer uma análise comparativa.")
        return
    
    # Coletar dados para comparação
    comparison_data = []
    
    for pl_id, analysis in analyzed_pls.items():
        # Extrair dados relevantes
        risk_score = analysis.get('risco_aprovacao', {}).get('score', 0)
        tendencia = analysis.get('analise_politica', {}).get('tendencia', 'Indefinida')
        estimativa = analysis.get('tempo_estimado', {}).get('estimativa', 'Não disponível')
        status = analysis.get('status_atual', {}).get('situacao', 'Não disponível')
        titulo = analysis.get('titulo', 'Não disponível')
        
        # Adicionar à lista de comparação
        comparison_data.append({
            'pl_id': pl_id,
            'titulo': titulo,
            'risco': risk_score,
            'tendencia': tendencia,
            'tempo': estimativa,
            'status': status
        })
    
    # Ordenar por risco (maior primeiro)
    comparison_data.sort(key=lambda x: x['risco'], reverse=True)
    
    # Gráfico comparativo de risco
    st.write("#### Comparativo de Risco de Aprovação")
    
    # Dados para o gráfico
    pl_ids = [item['pl_id'] for item in comparison_data]
    risk_scores = [item['risco'] for item in comparison_data]
    
    # Criar gráfico de barras horizontais
    fig, ax = plt.subplots(figsize=(10, max(4, len(pl_ids) * 0.7)))
    
    # Determinar cores com base no score
    colors = []
    for score in risk_scores:
        if score >= 70:
            colors.append("red")
        elif score >= 50:
            colors.append("orange")
        elif score >= 30:
            colors.append("#CCCC00")  # Amarelo escuro
        else:
            colors.append("green")
    
    # Criar barras horizontais
    bars = ax.barh(pl_ids, risk_scores, color=colors)
    
    # Adicionar rótulos nos valores
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 1, bar.get_y() + bar.get_height()/2, f"{width:.0f}%",
                ha='left', va='center', fontweight='bold')
    
    # Personalização
    ax.set_xlim(0, 105)  # Limite um pouco maior para os rótulos
    ax.set_xlabel('Risco de Aprovação (%)')
    ax.set_title('Comparativo de Risco de Aprovação por PL')
    
    # Remover bordas
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Exibir o gráfico
    st.pyplot(fig)
    
    # Tabela comparativa
    st.write("#### Tabela Comparativa")
    
    # Preparar dados para a tabela
    table_data = []
    for item in comparison_data:
        table_data.append({
            'PL': item['pl_id'],
            'Risco': f"{item['risco']:.0f}%",
            'Tendência': item['tendencia'],
            'Tempo Estimado': item['tempo'],
            'Status Atual': item['status']
        })
    
    # Exibir tabela
    st.table(pd.DataFrame(table_data))
    
    # Recomendações baseadas na comparação
    st.write("#### Recomendações Estratégicas")
    
    # PL com maior risco
    maior_risco = comparison_data[0]
    # PL com menor risco
    menor_risco = comparison_data[-1]
    
    # Recomendações gerais
    st.markdown(
        f"<div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>"
        f"<div style='font-weight: bold; font-size: 18px;'>Prioridades de Atenção</div>"
        f"<ul>"
        f"<li><strong>Prioridade Máxima:</strong> {maior_risco['pl_id']} apresenta o maior risco de aprovação ({maior_risco['risco']:.0f}%).</li>"
        f"<li><strong>Monitoramento Secundário:</strong> {menor_risco['pl_id']} apresenta o menor risco ({menor_risco['risco']:.0f}%).</li>"
        f"</ul>"
        f"<div style='font-weight: bold; font-size: 18px; margin-top: 15px;'>Recomendações</div>"
        f"<ul>"
        f"<li>Concentrar recursos de advocacy nos PLs com maior risco de aprovação e potencial impacto negativo.</li>"
        f"<li>Preparar planos de contingência para o cenário de aprovação do {maior_risco['pl_id']}.</li>"
        f"<li>Realizar análises aprofundadas de impacto operacional para os PLs com risco acima de 50%.</li>"
        f"</ul>"
        "</div>",
        unsafe_allow_html=True
    )
    
    # Timeline estimada
    st.write("#### Timeline Estimada")
    st.info("Esta seção apresenta uma estimativa visual do tempo de aprovação dos PLs analisados.")
    
    # Implementação simplificada da timeline
    # Em uma versão real, seria necessário converter as estimativas textuais para datas numéricas
    # e criar uma visualização mais sofisticada
    for item in comparison_data:
        tempo = item['tempo']
        if 'Não aplicável' in tempo:
            continue
            
        # Extrair estimativa numérica (Assumindo formato "X-Y meses")
        estimativa_texto = tempo
        cor = "#366092" if item['risco'] < 50 else "#ED7D31" if item['risco'] < 70 else "#A50000"
        
        st.markdown(
            f"<div style='display: flex; align-items: center; margin-bottom: 10px;'>"
            f"<div style='width: 100px; font-weight: bold;'>{item['pl_id']}</div>"
            f"<div style='flex-grow: 1; background-color: #f0f2f6; height: 30px; border-radius: 5px; position: relative;'>"
            f"<div style='position: absolute; left: 10px; top: 5px; color: {cor}; font-weight: bold;'>{estimativa_texto}</div>"
            f"<div style='position: absolute; top: 0; left: 0; height: 30px; width: 10px; background-color: {cor}; border-radius: 5px 0 0 5px;'></div>"
            f"</div>"
            "</div>",
            unsafe_allow_html=True
        )

def _render_sector_analysis():
    """
    Renderiza uma análise setorial baseada em múltiplos PLs.
    """
    st.write("### Visão Setorial de Risco Regulatório")
    
    # Verificar se temos PLs suficientes para análise setorial
    analyzed_pls = st.session_state.analysis_results
    if len(analyzed_pls) < 3:
        st.warning("É necessário ter pelo menos 3 PLs analisados para gerar uma visão setorial.")
        return
    
    # Coletar dados dos PLs analisados
    pls_data = []
    for pl_id, analysis in analyzed_pls.items():
        pls_data.append({
            "Sigla": pl_id.split()[0],
            "Numero": pl_id.split()[1].split('/')[0],
            "Ano": pl_id.split()[1].split('/')[1]
        })
    
    # Instanciar analisador de risco
    try:
        risk_analyzer = PLRiskAnalyzer()
        
        # Tentar obter visão setorial
        with st.spinner("Gerando visão setorial..."):
            sector_overview = risk_analyzer.get_sector_risk_overview(pls_data)
            
            if sector_overview and 'error' not in sector_overview:
                # Exibir visão geral
                st.write("#### Panorama de Risco Regulatório do Setor")
                
                # Métricas principais
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    risco_medio = sector_overview.get('risco_medio', 0)
                    nivel_risco = sector_overview.get('nivel_risco_medio', 'Não disponível')
                    
                    st.markdown(
                        f"<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center;'>"
                        f"<div style='font-size: 36px; font-weight: bold; color: #366092;'>{risco_medio:.1f}%</div>"
                        f"<div style='font-size: 18px;'>Risco Médio</div>"
                        f"<div style='font-size: 16px;'>Nível: {nivel_risco}</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
                
                with col2:
                    distribuicao = sector_overview.get('distribuicao_risco', {})
                    alto_risco = distribuicao.get('alto_risco', 0)
                    medio_risco = distribuicao.get('medio_risco', 0)
                    baixo_risco = distribuicao.get('baixo_risco', 0)
                    
                    total_pls = alto_risco + medio_risco + baixo_risco
                    
                    st.markdown(
                        f"<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center;'>"
                        f"<div style='font-size: 24px; font-weight: bold;'>{total_pls}</div>"
                        f"<div style='font-size: 18px;'>PLs Analisados</div>"
                        f"<div style='font-size: 14px;'>{alto_risco} Alto | {medio_risco} Médio | {baixo_risco} Baixo</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
                
                with col3:
                    data_atual = sector_overview.get('data_atualizacao', datetime.now().strftime("%Y-%m-%d"))
                    
                    st.markdown(
                        f"<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center;'>"
                        f"<div style='font-size: 24px; font-weight: bold;'>{data_atual}</div>"
                        f"<div style='font-size: 18px;'>Atualização</div>"
                        f"<div style='font-size: 14px;'>Data da análise</div>"
                        "</div>",
                        unsafe_allow_html=True
                    )
                
                # Gráfico de distribuição de risco
                st.write("#### Distribuição de Risco Regulatório")
                
                # Dados para o gráfico
                labels = ['Alto Risco', 'Médio Risco', 'Baixo Risco']
                sizes = [alto_risco, medio_risco, baixo_risco]
                colors = ['red', 'orange', 'green']
                
                # Criar gráfico de pizza
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')  # Para garantir que o gráfico seja circular
                
                # Título
                ax.set_title('Distribuição de PLs por Nível de Risco')
                
                # Exibir o gráfico
                st.pyplot(fig)
                
                # PLs de alto risco
                st.write("#### PLs de Alto Risco")
                
                pls_alto_risco = sector_overview.get('pls_alto_risco', [])
                if pls_alto_risco:
                    for pl in pls_alto_risco:
                        pl_id = pl.get('pl_id', '')
                        titulo = pl.get('titulo', '')[:100] + '...'
                        score = pl.get('score', 0)
                        status = pl.get('status', '')
                        
                        st.markdown(
                            f"<div style='background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 15px;'>"
                            f"<div style='font-weight: bold;'>{pl_id} (Score: {score:.0f}%)</div>"
                            f"<div>{titulo}</div>"
                            f"<div>Status: {status}</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("Não foram identificados PLs de alto risco.")
                
                # Contextos políticos
                st.write("#### Contextos Políticos Relevantes")
                
                contextos_politicos = sector_overview.get('contextos_politicos', [])
                if contextos_politicos:
                    for i, contexto in enumerate(contextos_politicos):
                        st.markdown(
                            f"<div style='background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 15px;'>"
                            f"<div style='font-weight: bold;'>Contexto {i+1}</div>"
                            f"<div>{contexto}</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("Não foram identificados contextos políticos relevantes.")
                
                # Próximos eventos críticos
                st.write("#### Próximos Eventos Críticos")
                
                eventos_criticos = sector_overview.get('proximos_eventos_criticos', [])
                if eventos_criticos:
                    for evento in eventos_criticos:
                        pl_id = evento.get('pl_id', '')
                        evento_nome = evento.get('evento', '')
                        probabilidade = evento.get('probabilidade', '')
                        observacao = evento.get('observacao', '')
                        risco = evento.get('risco', 0)
                        
                        st.markdown(
                            f"<div style='background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 15px;'>"
                            f"<div style='font-weight: bold;'>{pl_id} - {evento_nome}</div>"
                            f"<div style='color: {'red' if probabilidade == 'Alta' else 'orange'}; font-weight: bold;'>Probabilidade: {probabilidade}</div>"
                            f"<div>{observacao}</div>"
                            f"<div>Risco de Aprovação: {risco:.0f}%</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("Não foram identificados eventos críticos iminentes.")
                
                # Recomendações estratégicas
                st.write("#### Recomendações Estratégicas")
                
                # Gerar recomendações baseadas nos dados
                nivel_geral = "alto" if risco_medio >= 60 else "moderado" if risco_medio >= 40 else "baixo"
                num_alto_risco = alto_risco
                
                st.markdown(
                    f"<div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>"
                    f"<div style='font-weight: bold; font-size: 18px;'>Análise Geral</div>"
                    f"<p>O setor apresenta nível <strong>{nivel_geral}</strong> de risco regulatório, com {num_alto_risco} PLs classificados como alto risco.</p>"
                    f"<div style='font-weight: bold; font-size: 18px; margin-top: 15px;'>Ações Recomendadas</div>"
                    f"<ul>"
                    f"<li><strong>Monitoramento Prioritário:</strong> Acompanhar intensivamente os PLs de alto risco, especialmente os que estão em estágio avançado de tramitação.</li>"
                    f"<li><strong>Advocacy Estratégico:</strong> Focar esforços de advocacy nos PLs com maior potencial de impacto no setor.</li>"
                    f"<li><strong>Preparação Operacional:</strong> Desenvolver planos de contingência para adaptação aos cenários regulatórios mais prováveis.</li>"
                    f"<li><strong>Engajamento Setorial:</strong> Articular posicionamentos com associações do setor para amplificar influência.</li>"
                    f"</ul>"
                    "</div>",
                    unsafe_allow_html=True
                )
            else:
                st.error("Não foi possível gerar a visão setorial. Tente novamente ou adicione mais PLs para análise.")
        
    except Exception as e:
        st.error(f"Erro ao gerar visão setorial: {str(e)}")
        st.info("A funcionalidade de análise setorial requer o componente de análise de risco completo.")