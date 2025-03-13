#!/usr/bin/env python
"""
DEBUG DIRETO DA API DO SENADO
Script que acessa DIRETAMENTE a API do Senado e imprime os resultados 
sem depender de nenhum código existente do projeto.
"""
import requests
import xmltodict
import json
import re
from datetime import datetime

# Constantes
BASE_URL = "https://legis.senado.leg.br/dadosabertos"
OUTPUT_DIR = "debug_results"
import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

def salvar_arquivo(nome, conteudo):
    """Salva conteúdo em um arquivo para análise posterior"""
    caminho = f"{OUTPUT_DIR}/{nome}"
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    print(f"Arquivo salvo: {caminho}")
    return caminho

def formatar_json(data):
    """Formata um dicionário como JSON indentado"""
    return json.dumps(data, indent=2, ensure_ascii=False)

def fazer_requisicao(endpoint, params=None):
    """Faz uma requisição à API do Senado e retorna o resultado como dicionário"""
    url = f"{BASE_URL}/{endpoint}"
    print(f"\n>>> Requisitando: {url}")
    if params:
        print(f">>> Parâmetros: {params}")
    
    try:
        response = requests.get(url, params=params)
        print(f">>> Status: {response.status_code}")
        print(f">>> Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            if 'xml' in response.headers.get('Content-Type', '').lower():
                return xmltodict.parse(response.content)
            else:
                return response.json()
        else:
            print(f"!!! ERRO {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"!!! EXCEÇÃO: {str(e)}")
        return None

def analisar_pl(sigla, numero, ano):
    """Realiza uma análise completa de um PL usando a API do Senado"""
    pl_id = f"{sigla} {numero}/{ano}"
    print(f"\n====== ANÁLISE DIRETA DO PL {pl_id} ======")
    
    # PASSO 1: Obter dados básicos do PL
    print("\n=== PASSO 1: Dados Básicos do PL ===")
    endpoint = f"materia/{sigla}/{numero}/{ano}"
    dados_basicos = fazer_requisicao(endpoint)
    
    if not dados_basicos:
        print(f"!!! FALHA: Não foi possível obter dados básicos do {pl_id}")
        return
    
    # Salvar para debug
    salvar_arquivo(f"{sigla}_{numero}_{ano}_basicos.json", formatar_json(dados_basicos))
    
    # Extrair Código da Matéria
    try:
        materia = dados_basicos.get('DetalheMateria', {}).get('Materia', {})
        codigo_materia = materia.get('IdentificacaoMateria', {}).get('CodigoMateria')
        
        if not codigo_materia:
            print("!!! ERRO: Código da matéria não encontrado nos dados básicos")
            return
            
        print(f">>> Código da matéria: {codigo_materia}")
        
        # Extrair outros dados úteis
        titulo = materia.get('DadosBasicosMateria', {}).get('EmentaMateria', '')
        print(f">>> Título: {titulo[:100]}...")
        
        autor = materia.get('Autoria', {}).get('Autor', {}).get('NomeAutor', '') if isinstance(materia.get('Autoria', {}).get('Autor', {}), dict) else "Múltiplos autores"
        print(f">>> Autor: {autor}")
        
    except Exception as e:
        print(f"!!! ERRO ao processar dados básicos: {str(e)}")
        return
    
    # PASSO 2: Tentar encontrar relatores na API via endpoint "relatoria"
    print("\n=== PASSO 2: Tentativa com endpoint 'relatoria' ===")
    endpoint_relatoria = f"materia/relatoria/{codigo_materia}"
    dados_relatoria = fazer_requisicao(endpoint_relatoria)
    
    if dados_relatoria:
        salvar_arquivo(f"{sigla}_{numero}_{ano}_relatoria.json", formatar_json(dados_relatoria))
        print(">>> Dados de relatoria obtidos (verificar arquivo salvo)")
    else:
        print("!!! Endpoint 'relatoria' falhou ou não existe")
    
    # PASSO 3: Obter movimentações (este é o caminho correto segundo a documentação)
    print("\n=== PASSO 3: Obtendo movimentações (método recomendado) ===")
    endpoint_movimentacoes = f"materia/movimentacoes/{codigo_materia}"
    dados_movimentacoes = fazer_requisicao(endpoint_movimentacoes)
    
    if not dados_movimentacoes:
        print("!!! FALHA: Não foi possível obter movimentações")
        return
        
    salvar_arquivo(f"{sigla}_{numero}_{ano}_movimentacoes.json", formatar_json(dados_movimentacoes))
    
    # Extrair e processar movimentações
    try:
        movimentacoes = dados_movimentacoes.get('MovimentacaoMateria', {}).get('Movimentacoes', {}).get('Movimentacao', [])
        
        # Garantir que seja uma lista
        if not isinstance(movimentacoes, list):
            movimentacoes = [movimentacoes]
            
        print(f">>> Encontradas {len(movimentacoes)} movimentações")
        
        # Procurar menções a relatores nas movimentações
        encontrou_relator = False
        relatores_encontrados = []
        
        for i, evento in enumerate(movimentacoes):
            texto = evento.get('TextoMovimentacao', '').lower()
            data = evento.get('DataMovimentacao', '')
            local = evento.get('Local', {}).get('NomeLocal', '')
            
            if 'relator' in texto:
                print(f"\n>>> MENÇÃO A RELATOR na movimentação {i+1} ({data}):")
                print(f">>> Local: {local}")
                print(f">>> Texto: {texto[:150]}...")
                encontrou_relator = True
                
                # Tentar extrair nome do relator com regex
                padroes = [
                    r"[Dd]esignad[oa] [Rr]elator[,]?\s+[oa]?\s+[Ss]enador[a]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                    r"[Dd]esignad[oa] [Rr]elator[,]?\s+[Ss]en[.]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                    r"[Rr]elator[:]?\s+[Ss]enador[a]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                    r"[Rr]elator[:]?\s+[Ss]en[.]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                    r"[Ss]enador[a]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)\s+(?:para|como)\s+relator"
                ]
                
                nome_relator = None
                for padrao in padroes:
                    match = re.search(padrao, texto)
                    if match:
                        nome_relator = match.group(1)
                        break
                
                if nome_relator:
                    print(f">>> EXTRAÍDO: Nome do relator = {nome_relator}")
                    
                    # Extrair partido/UF se disponível
                    partido_uf_pattern = r"\(([A-Z]+)[\/\-]([A-Z]{2})\)"
                    partido_uf_match = re.search(partido_uf_pattern, texto)
                    
                    partido = ""
                    uf = ""
                    if partido_uf_match:
                        partido = partido_uf_match.group(1)
                        uf = partido_uf_match.group(2)
                        print(f">>> EXTRAÍDO: Partido/UF = {partido}/{uf}")
                    
                    relator_info = {
                        "Nome": nome_relator,
                        "Partido": partido,
                        "UF": uf,
                        "Comissao": local,
                        "DataDesignacao": data,
                        "Fonte": "Extraído da movimentação"
                    }
                    
                    relatores_encontrados.append(relator_info)
        
        if not encontrou_relator:
            print("!!! Nenhuma menção a relator encontrada nas movimentações")
        else:
            print(f"\n>>> RESULTADO: {len(relatores_encontrados)} relatores extraídos das movimentações")
            for i, rel in enumerate(relatores_encontrados):
                print(f"\n>>> Relator {i+1}: {rel['Nome']}")
                print(f">>> Partido/UF: {rel['Partido']}/{rel['UF'] if rel['Partido'] and rel['UF'] else 'Não disponível'}")
                print(f">>> Comissão: {rel['Comissao']}")
                print(f">>> Data: {rel['DataDesignacao']}")
            
            # Salvar relatores encontrados
            salvar_arquivo(f"{sigla}_{numero}_{ano}_relatores.json", formatar_json(relatores_encontrados))
            
    except Exception as e:
        print(f"!!! ERRO ao processar movimentações: {str(e)}")
    
    # PASSO 4: Obter situação atual
    print("\n=== PASSO 4: Situação Atual ===")
    endpoint_situacao = f"materia/situacaoatual/{codigo_materia}"
    dados_situacao = fazer_requisicao(endpoint_situacao)
    
    if dados_situacao:
        salvar_arquivo(f"{sigla}_{numero}_{ano}_situacao.json", formatar_json(dados_situacao))
        
        try:
            situacao = dados_situacao.get('SituacaoAtualMateria', {}).get('Materia', {})
            local = situacao.get('Local', {}).get('NomeLocal', '')
            status = situacao.get('Situacao', {}).get('DescricaoSituacao', '')
            
            print(f">>> Local atual: {local}")
            print(f">>> Status: {status}")
        except Exception as e:
            print(f"!!! ERRO ao processar situação: {str(e)}")
    
    print("\n====== ANÁLISE CONCLUÍDA ======")
    print(f"Todos os resultados foram salvos em arquivos no diretório: {OUTPUT_DIR}")
    
    # RESUMO FINAL
    print("\n=== RESUMO DA ANÁLISE ===")
    print(f"PL: {pl_id}")
    print(f"Título: {titulo[:100]}...")
    print(f"Autor: {autor}")
    print(f"Código: {codigo_materia}")
    
    if relatores_encontrados:
        print(f"Relatores encontrados: {len(relatores_encontrados)}")
        for rel in relatores_encontrados:
            print(f" - {rel['Nome']} ({rel['Partido']}/{rel['UF']})")
    else:
        print("Relatores: Nenhum relator encontrado")

if __name__ == "__main__":
    # Analisar o PL 3405/2023
    analisar_pl("PL", "3405", "2023")
    
    # Se quiser analisar outro PL para comparação, descomente a linha abaixo
    # analisar_pl("PL", "2234", "2022")