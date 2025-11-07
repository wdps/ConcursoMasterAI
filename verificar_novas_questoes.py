# -*- coding: utf-8 -*-
import csv
import os

# ATENÇÃO: O nome do arquivo a ser verificado
NOME_ARQUIVO = 'novas questoes.csv'
DELIMITADOR = ';'
    
# Esta é a estrutura "correta" de 14 colunas que o app.py espera
HEADER_ESPERADO = [
    'disciplina', 'materia', 'banca', 'dificuldade', 'enunciado',
    'alternativa_a', 'alternativa_b', 'alternativa_c', 'alternativa_d', 'alternativa_e',
    'resposta_correta', 'justificativa', 'dica', 'formula'
]
N_COLUNAS_ESPERADO = len(HEADER_ESPERADO) # Exatamente 14

def verificar_csv_v3():
    print(f"--- Iniciando auditoria v3 do arquivo '{NOME_ARQUIVO}' ---")

    if not os.path.exists(NOME_ARQUIVO):
        print(f"❌ ERRO CRÍTICO: Arquivo '{NOME_ARQUIVO}' não encontrado nesta pasta.")
        return

    erros_header = []
    erros_linhas = []
    total_linhas_processadas = 0

    try:
        with open(NOME_ARQUIVO, mode='r', encoding='utf-8-sig', newline='') as f:
            # Usar quotechar='"' é essencial para que o leitor ignore ';' dentro das justificativas
            leitor_csv = csv.reader(f, delimiter=DELIMITADOR, quotechar='"')
                
            # 1. Verificar o Cabeçalho (Header)
            try:
                header = next(leitor_csv)
                total_linhas_processadas += 1
            except StopIteration:
                print("❌ ERRO CRÍTICO: O arquivo está completamente vazio.")
                return

            if header == HEADER_ESPERADO:
                print(f"✅ Cabeçalho (Linha 1) está perfeito (14 colunas).")
            else:
                if len(header) != N_COLUNAS_ESPERADO:
                    msg = f"❌ ERRO DE CABEÇALHO: Esperava 14 colunas, mas a Linha 1 tem {len(header)}."
                    print(msg)
                    erros_header.append(msg)
                else:
                    msg = f"⚠️ AVISO DE CABEÇALHO: Os nomes das colunas na Linha 1 estão errados ou fora de ordem, mas o total (14) está correto."
                    print(msg)
                    erros_header.append(msg)

            # 2. Verificar todas as outras linhas
            for numero_linha, linha in enumerate(leitor_csv, start=2):
                total_linhas_processadas += 1
                n_colunas_linha_atual = len(linha)
                    
                if n_colunas_linha_atual != N_COLUNAS_ESPERADO:
                    erro_msg = f"Linha {numero_linha}: Número de colunas incorreto. (Esperado: {N_COLUNAS_ESPERADO}, Encontrado: {n_colunas_linha_atual})"
                    erros_linhas.append(erro_msg)

    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO DURANTE A LEITURA (possível problema de encoding ou caractere inválido): {e}")
        return

    # 3. Relatório Final
    print(f"\n--- Auditoria Concluída ---")
    print(f"Total de linhas lidas: {total_linhas_processadas}")
    
    if not erros_header and not erros_linhas:
        print(f"✅ SUCESSO! O arquivo '{NOME_ARQUIVO}' está 100% correto e não corrompido.")
    else:
        print(f"❌ ATENÇÃO: Foram encontrados problemas de estrutura!")
        if erros_header:
            for erro in erros_header:
                print(f"   -> {erro}")
        if erros_linhas:
            print(f"   -> O arquivo '{NOME_ARQUIVO}' está corrompido. {len(erros_linhas)} linhas de dados estão com o número errado de colunas:")
            # Limita a exibição para os primeiros 20 erros para não lotar o terminal
            for erro in erros_linhas[:20]:
                print(f"      {erro}")
            if len(erros_linhas) > 20:
                print(f"      ...e mais {len(erros_linhas) - 20} outros erros.")
            print("\n   -> CAUSA PROVÁVEL: 'Copiar e Colar' de textos com quebra de linha (Enter) no meio de uma célula.")
    print("---------------------------")

if __name__ == "__main__":
    verificar_csv_v3()
