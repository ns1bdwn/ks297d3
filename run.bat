@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: Configurações do ambiente
set "PROJECT_ROOT=%~dp0"
set "ENV_NAME=regulatory_suite"
set "RUNTIME_DIR=%PROJECT_ROOT%runtime"
set "CONDA_PATH=%RUNTIME_DIR%\miniconda"
set "CONDA_SCRIPTS=%CONDA_PATH%\Scripts"
set "CONDA_ACTIVATE=%CONDA_SCRIPTS%\activate.bat"
set "ENV_DIR=%RUNTIME_DIR%\env"
set "MODEL_DIR=%PROJECT_ROOT%\data\models"

:: ============================================================
:: VERIFICAÇÃO DE ESTRUTURA DE DIRETÓRIOS
:: ============================================================
echo Verificando estrutura de diretórios do projeto...

:: Estrutura de diretórios principais
set DIRECTORIES=^
src ^
src\maturity ^
src\intelligence ^
src\intelligence\utils ^
src\intelligence\analyzers ^
src\intelligence\collectors ^
src\shared ^
src\ui ^
src\reporting ^
data ^
data\clients ^
data\models ^
data\regulations ^
data\backup

:: Criar diretórios se não existirem
for %%d in (%DIRECTORIES%) do (
    if not exist "%PROJECT_ROOT%%%d" (
        echo Criando diretório %%d...
        mkdir "%PROJECT_ROOT%%%d"
    )
)

:: Criar arquivos __init__.py em diretórios Python se não existirem
for %%d in (src src\maturity src\intelligence src\intelligence\utils src\intelligence\analyzers src\intelligence\collectors src\shared src\ui src\reporting) do (
    if not exist "%PROJECT_ROOT%%%d\__init__.py" (
        echo Criando __init__.py em %%d...
        echo # Módulo %%d > "%PROJECT_ROOT%%%d\__init__.py"
    )
)

echo Verificação de estrutura concluída.
echo.
:: ============================================================

:: Verificar se o Miniconda está instalado
if not exist "%CONDA_ACTIVATE%" (
    echo ERRO: Miniconda não encontrado em %CONDA_PATH%
    echo Por favor, instale o Miniconda manualmente antes de prosseguir.
    pause
    exit /b 1
)

:: Inicializar Conda
call "%CONDA_ACTIVATE%"
if errorlevel 1 (
    echo ERRO: Falha ao inicializar o Conda
    pause
    exit /b 1
)

:MENU
cls
echo ===========================================================
echo           regulatory_suite - Menu de Gerenciamento
echo ===========================================================
echo [1] **Primeira Instalação** (Criar ambiente do zero)
echo [2] **Atualizar Dependências** (Manter ambiente existente)
echo [3] Baixar ou Atualizar Modelos de IA
echo [4] Iniciar o WebApp do Regulatory Suite
echo [5] Verificar Estrutura de Diretórios
echo [6] Sair
echo ===========================================================
set /p escolha="Escolha uma opção: "

if "%escolha%"=="1" goto FIRST_INSTALL
if "%escolha%"=="2" goto UPDATE_ENV
if "%escolha%"=="3" goto DOWNLOAD_OR_UPDATE_MODELS
if "%escolha%"=="4" goto RUN_WEBAPP
if "%escolha%"=="5" goto CHECK_STRUCTURE
if "%escolha%"=="6" goto :EOF

echo Opção inválida! Tente novamente.
timeout /t 2 >nul
goto MENU

:FIRST_INSTALL
echo.
echo **Criando ambiente do zero...**
if exist "%ENV_DIR%" (
    echo ERRO: O ambiente já existe! Se deseja apenas atualizar, escolha a opção 2.
    pause >nul
    goto MENU
)

echo Criando diretório do ambiente...
mkdir "%ENV_DIR%"

echo Criando e configurando ambiente completo...
call conda env create -p "%ENV_DIR%" -f environment.yml
if errorlevel 1 (
    echo ERRO: Falha ao criar ambiente
    echo Verifique o arquivo environment.yml e tente novamente
    pause >nul
    goto MENU
)

echo.
echo ====================================
echo Ambiente criado com sucesso!
echo Todas as dependências foram instaladas.
echo ====================================
echo.
pause >nul
goto MENU

:UPDATE_ENV
echo.
echo **Atualizando dependências...**
if not exist "%ENV_DIR%" (
    echo ERRO: Nenhum ambiente encontrado! Execute a opção 1 primeiro.
    pause >nul
    goto MENU
)

echo Criando backup da versão atual...

:: Garantir que o diretório de backup existe
if not exist "%PROJECT_ROOT%\data\backup" mkdir "%PROJECT_ROOT%\data\backup"

:: Gerar um timestamp sem caracteres inválidos para o nome do arquivo
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set TODAY=%%c-%%b-%%a
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set NOW=%%a-%%b
set TIMESTAMP=%TODAY%_%NOW%

:: Criar os arquivos de backup corretamente
call conda list --export > "%PROJECT_ROOT%\data\backup\env_backup_%TIMESTAMP%.txt"
call pip freeze > "%PROJECT_ROOT%\data\backup\pip_backup_%TIMESTAMP%.txt"

echo Atualizando pacotes Conda e Pip...
call conda activate "%ENV_DIR%"
call conda env update -p "%ENV_DIR%" -f environment.yml --prune
if errorlevel 1 (
    echo ERRO: Falha ao atualizar dependências.
    pause >nul
    goto MENU
)

echo Dependências atualizadas com sucesso!
pause >nul
goto MENU

:DOWNLOAD_OR_UPDATE_MODELS
echo.
echo **Baixando ou Atualizando modelos de IA...**

:: Garantir que o ambiente Conda esteja ativado
call "%CONDA_ACTIVATE%" "%ENV_DIR%"

:: Verificar se a ativação foi bem-sucedida
if errorlevel 1 (
    echo ERRO: Falha ao ativar o ambiente Conda!
    pause >nul
    goto MENU
)

:: Executar o script de download de modelos (caminho atualizado)
python -m src.intelligence.utils.download_models --check
echo.
echo Escolha uma opção:
echo [1] Baixar todos os modelos
echo [2] Baixar modelo específico
echo [3] Verificar atualizações
echo [4] Voltar ao menu principal
set /p model_choice="Opção: "

if "%model_choice%"=="1" (
    python -m src.intelligence.utils.download_models --download-all
) else if "%model_choice%"=="2" (
    set /p model_name="Digite o nome do modelo: "
    python -m src.intelligence.utils.download_models --model !model_name! --update
) else if "%model_choice%"=="3" (
    python -m src.intelligence.utils.download_models --check-updates
) else if "%model_choice%"=="4" (
    goto MENU
) else (
    echo Opção inválida!
)

pause >nul
goto MENU

:RUN_WEBAPP
echo.
echo **Iniciando o WebApp do Regulatory Suite...**
call conda activate "%ENV_DIR%"

:: Executar o Streamlit para abrir o WebApp
streamlit run "%PROJECT_ROOT%\src\ui\app.py"
if errorlevel 1 (
    echo ERRO: Falha ao iniciar o WebApp
    pause >nul
    goto MENU
)

goto MENU

:CHECK_STRUCTURE
echo.
echo **Verificando estrutura do projeto...**

:: Verificar a existência de arquivos críticos
echo Verificando arquivos essenciais...
set CRITICAL_FILES=^
src\shared\config.py ^
src\shared\storage.py ^
src\maturity\assessment.py ^
src\ui\app.py

set MISSING_FILES=0
for %%f in (%CRITICAL_FILES%) do (
    if not exist "%PROJECT_ROOT%%%f" (
        echo AUSENTE: %%f
        set /a MISSING_FILES+=1
    ) else (
        echo OK: %%f
    )
)

if %MISSING_FILES% NEQ 0 (
    echo.
    echo AVISO: !MISSING_FILES! arquivos essenciais estão ausentes.
    echo Por favor, certifique-se de que todos os arquivos necessários existem.
) else (
    echo.
    echo Todos os arquivos essenciais estão presentes!
)

:: Verificar diretórios vazios importantes
echo.
echo Verificando conteúdo de diretórios importantes...
set EMPTY_DIRS=0

for %%d in (src\maturity src\intelligence\utils src\shared src\ui) do (
    dir /b "%PROJECT_ROOT%%%d\*.py" >nul 2>&1
    if errorlevel 1 (
        echo VAZIO: Diretório %%d não contém arquivos Python
        set /a EMPTY_DIRS+=1
    ) else (
        echo OK: Diretório %%d contém arquivos Python
    )
)

if %EMPTY_DIRS% NEQ 0 (
    echo.
    echo AVISO: !EMPTY_DIRS! diretórios importantes parecem vazios.
) else (
    echo.
    echo Todos os diretórios importantes contêm arquivos!
)

echo.
echo Verificação de estrutura concluída.
pause >nul
goto MENU