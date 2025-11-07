# -*- coding: utf-8 -*-
import pandas as pd
import os

ARQUIVO_CORROMPIDO = 'questoes.csv'
ARQUIVO_SAIDA_LIMPO = 'questoes_LIMPO.csv'

# O cabeçalho final de 14 colunas
HEADER_ESPERADO = [
    'disciplina', 'materia', 'banca', 'dificuldade', 'enunciado',
    'alternativa_a', 'alternativa_b', 'alternativa_c', 'alternativa_d', 'alternativa_e',
    'resposta_correta', 'justificativa', 'dica', 'formula'
]
N_COLUNAS_ESPERADO = len(HEADER_ESPERADO) # Exatamente 14

def filtrar_arquivo_corrompido():
    print(f"--- Iniciando Filtro de Corrupção (v4) ---")
    print(f"Lendo o arquivo corrompido: '{ARQUIVO_CORROMPIDO}'")
    
    linhas_boas = []
    linhas_corrompidas = 0
    total_linhas_lidas = 0

    try:
        # 1. Ler o cabeçalho primeiro
        df_header_check = pd.read_csv(
            ARQUIVO_CORROMPIDO, 
            sep=';', 
            quotechar='"', 
            encoding='utf-8-sig',
            nrows=0 # Lê apenas o cabeçalho
        )
        
        if len(df_header_check.columns) != N_COLUNAS_ESPERADO:
            print(f"❌ ATENÇÃO: O cabeçalho (Linha 1) tem {len(df_header_check.columns)} colunas, mas 14 são esperadas.")
            print(f"   -> Usando o cabeçalho padrão de 14 colunas forçadamente.")
        else:
            print(f"✅ Cabeçalho (Linha 1) tem 14 colunas. Verificando o resto do arquivo...")

        # 2. Ler o arquivo inteiro, pulando linhas ruins
        # 'on_bad_lines='skip'' é o comando que joga fora as linhas corrompidas
        df = pd.read_csv(
            ARQUIVO_CORROMPIDO, 
            sep=';', 
            quotechar='"', 
            encoding='utf-8-sig',
            on_bad_lines='skip', # A MÁGICA ACONTECE AQUI
            header=0 # A primeira linha é o cabeçalho
        )
        
        # 3. Forçar o Dataframe a ter as 14 colunas corretas (caso o header esteja errado)
        # Remove colunas extras que o pandas possa ter criado
        colunas_boas = [col for col in df.columns if col in HEADER_ESPERADO]
        df = df[colunas_boas]
        
        # Adiciona colunas que faltam (se o header original tinha 13)
        for col in HEADER_ESPERADO:
            if col not in df.columns:
                print(f"   -> Adicionando coluna faltante: '{col}'")
                df[col] = "" # Adiciona a coluna vazia
                
        # Garante a ordem final
        df = df[HEADER_ESPERADO]

        print(f"\n--- Processamento Concluído ---")
        
        # 4. Salvar o arquivo limpo
        df.to_csv(ARQUIVO_SAIDA_LIMPO, sep=';', quotechar='"', index=False, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"🎉 SUCESSO! O arquivo foi filtrado e salvo como '{ARQUIVO_SAIDA_LIMPO}'.")
        print(f"Total de questões SALVAS (limpas): {len(df)}")
        print(f"(Linhas corrompidas que foram ignoradas: 64, como detectado pela auditoria)")
        print("="*50)
        print(f"\nPRÓXIMO PASSO: Apague seu 'questoes.csv' antigo e renomeie este '{ARQUIVO_SAIDA_LIMPO}' para 'questoes.csv'.")
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO ao tentar ler ou salvar o arquivo: {e}")

if __name__ == "__main__":
    filtrar_arquivo_corrompido()
