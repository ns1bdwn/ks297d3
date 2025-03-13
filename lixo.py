# Adicione este código em um script e execute para limpar o cache
import os
import glob

# Diretório padrão de cache
cache_dir = os.path.join(os.getcwd(), "data", "api_cache", "senado")

if os.path.exists(cache_dir):
    # Remover todos os caches relacionados ao PL
    cache_files = glob.glob(os.path.join(cache_dir, "*PL*3405*2023*.json"))
    
    for file in cache_files:
        os.remove(file)
        print(f"Removido: {file}")
    
    print(f"Total de {len(cache_files)} arquivos removidos.")
else:
    print(f"Diretório de cache não encontrado: {cache_dir}")