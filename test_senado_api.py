from src.intelligence.collectors.senado import SenadoAPI
import json
import os

# Configurar diretório de cache para os testes
cache_dir = os.path.join(os.getcwd(), "data", "api_cache", "senado_test")
os.makedirs(cache_dir, exist_ok=True)

# Inicializar API
api = SenadoAPI(cache_dir=cache_dir)

# Testar com o PL 3405/2023 (problema específico)
print("Testando PL 3405/2023...")
pl_details = api.get_additional_pl_details("PL", "3405", "2023")

if pl_details:
    print(f"✅ PL encontrado: {pl_details.get('Título', '')[:100]}...")
    
    # Verificar relatores
    relatores = pl_details.get('Relatores', [])
    if relatores:
        print(f"✅ Relatores: {len(relatores)} encontrados")
        for relator in relatores:
            print(f"  - {relator.get('Nome', '')} ({relator.get('SiglaPartido', '')}/{relator.get('UF', '')})")
    else:
        print("⚠️ Nenhum relator encontrado")
    
    # Verificar tramitação
    tramitacao = pl_details.get('Tramitacao_Detalhada', [])
    if tramitacao:
        print(f"✅ Tramitação: {len(tramitacao)} eventos encontrados")
        for evento in tramitacao[:3]:  # Mostrar apenas os 3 primeiros
            print(f"  - {evento.get('Data', '')}: {evento.get('Situacao', '')}")
    else:
        print("⚠️ Nenhum evento de tramitação encontrado")
    
    # Verificar textos
    texto = pl_details.get('Texto', {})
    if texto and texto.get('UrlTexto'):
        print(f"✅ URL do texto: {texto.get('UrlTexto', '')}")
    else:
        print("⚠️ Nenhum texto encontrado")
    
    # Salvar dados completos em JSON para análise
    output_file = os.path.join(cache_dir, "pl_3405_2023_details.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pl_details, f, ensure_ascii=False, indent=4)
    print(f"✅ Dados completos salvos em: {output_file}")
else:
    print("❌ PL 3405/2023 não encontrado!")