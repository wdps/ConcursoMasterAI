# ==========================================================
#   SCRIPT DE VERIFICAÇÃO DE CSV (PowerShell Nativo) - v2
# ==========================================================

# --- Configurações ---
# A linha abaixo foi corrigida para usar o caminho absoluto
$fileName = Join-Path $PSScriptRoot 'questoes.csv'
$delimiter = ';'
$encoding = 'utf-8' 
# =======================

Write-Host "Iniciando verificação de '$fileName'..." -ForegroundColor Cyan

# 1. Verifica se o arquivo existe
if (-not (Test-Path -Path $fileName)) {
    Write-Host "ERRO: O arquivo '$fileName' não foi encontrado nesta pasta." -ForegroundColor Red
    Write-Host "Verifique se o arquivo 'questoes.csv' está na mesma pasta que este script."
    pause
    exit 1
}

# 2. Carrega a biblioteca .NET para análise de texto
try {
    Add-Type -AssemblyName Microsoft.VisualBasic
    Write-Host "Biblioteca .NET (Microsoft.VisualBasic) carregada."
} catch {
    Write-Host "ERRO: Não foi possível carregar a biblioteca .NET de análise." -ForegroundColor Red
    Write-Host "$($_.Exception.Message)"
    pause
    exit 1
}

$parser = $null
$line_count = 0
$errorFound = $false

try {
    Write-Host "Tentando ler o arquivo com encoding '$encoding'..." -ForegroundColor Cyan

    # 3. Cria o leitor de CSV (TextFieldParser)
    $parser = New-Object Microsoft.VisualBasic.FileIO.TextFieldParser($fileName, [System.Text.Encoding]::GetEncoding($encoding))

    # 4. Configura o leitor (exatamente como o Pandas faria)
    $parser.SetDelimiters($delimiter)
    $parser.HasFieldsEnclosedInQuotes = $true # <--- Importante para ler aspas

    Write-Host "Iniciando análise linha por linha (Delimitador='$delimiter')..."

    # 5. Loop de leitura
    while (!$parser.EndOfData) {

        try {
            # Tenta ler a próxima linha
            $fields = $parser.ReadFields()
            $line_count++

            # Feedback de progresso
            if (($line_count % 100) -eq 0) {
                Write-Host -NoNewline "."
            }

        } catch [Microsoft.VisualBasic.FileIO.MalformedLineException] {
            # 6. ERRO ENCONTRADO!
            # Esta é a exceção específica para um CSV corrompido.
            Write-Host "" # Pula linha
            Write-Host "==================================================================" -ForegroundColor Red
            Write-Host "                       ERRO DE LEITURA DETECTADO                       " -ForegroundColor Red
            Write-Host "==================================================================" -ForegroundColor Red

            # A exceção MalformedLineException nos dá o número da linha exata!
            Write-Host "O arquivo '$fileName' está corrompido."
            Write-Host "Mensagem do Erro: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "LINHA EXATA DO ERRO NO CSV: $($_.Exception.LineNumber)" -ForegroundColor Yellow

            Write-Host "`nPor favor, abra o 'questoes.csv' e corrija a linha $($_.Exception.LineNumber)."
            Write-Host "O erro (baseado no log anterior) é: Uma aspa (`) foi aberta e não foi fechada."
            Write-Host "=================================================================="

            $errorFound = $true
            break # Para o loop
        }
    }

    if (-not $errorFound) {
        Write-Host "`n`n--- SUCESSO ---" -ForegroundColor Green
        Write-Host "O arquivo '$fileName' foi lido completamente."
        Write-Host "Total de $line_count linhas válidas encontradas."
        Write-Host "O arquivo parece estar VÁLIDO e pronto para o deploy."
    }

} catch {
    # Pega outros erros (ex: encoding errado)
    Write-Host "`n--- ERRO INESPERADO ---" -ForegroundColor Red
    Write-Host "Mensagem: $($_.Exception.Message)"
    if ($_.Exception.Message -like "*encoding*") {
        Write-Host "DICA: O encoding '$encoding' pode estar errado. Tente alterar para 'iso-8859-1' no topo do script." -ForegroundColor Yellow
    }
} finally {
    # 7. Limpa o leitor da memória
    if ($parser -ne $null) {
        $parser.Close()
        $parser.Dispose()
    }
}

Write-Host "`nVerificação finalizada."
Write-Host "Pressione Enter para sair..."
Read-Host