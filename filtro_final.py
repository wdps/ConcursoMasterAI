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
    
    linhas_boas = 0
    linhas_corrompidas_detectadas = 0

    try:
        # Usar 'header=None' para ler o arquivo como dados brutos, sem confiar no cabeçalho
        # 'on_bad_lines='warn'' irá nos avisar sobre as linhas puladas
        df = pd.read_csv(
            ARQUIVO_CORROMPIDO, 
            sep=';', 
            quotechar='"', 
            encoding='utf-8-sig',
            on_bad_lines='warn', # Avisa sobre linhas ruins
            header=None # Lê tudo como dados brutos
        )
        
        total_linhas_lidas = len(df)
        print(f"Total de linhas lidas (brutas): {total_linhas_lidas}")

        # Filtrar o DataFrame para manter apenas linhas com 14 colunas
        df_limpo = df[df.apply(lambda x: x.count(), axis=1) == N_COLUNAS_ESPERADO]
        
        linhas_boas = len(df_limpo)
        linhas_corrompidas_detectadas = total_linhas_lidas - linhas_boas

        # Definir o cabeçalho correto no DataFrame limpo
        df_limpo.columns = HEADER_ESPERADO
        
        # Remover duplicatas (caso o cabeçalho "disciplina;materia..." tenha sido lido como dado)
        df_limpo = df_limpo[df_limpo['disciplina'] != 'disciplina']
        
        # Limpeza Final: Remover duplicatas reais (baseado no enunciado)
        df_limpo.drop_duplicates(subset=['enunciado'], keep='last', inplace=True)
        
        print(f"\n--- Processamento Concluído ---")
        
        # Salvar o arquivo limpo
        df_limpo.to_csv(ARQUIVO_SAIDA_LIMPO, sep=';', quotechar='"', index=False, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"🎉 SUCESSO! O arquivo foi filtrado e salvo como '{ARQUIVO_SAIDA_LIMPO}'.")
        print(f"Total de questões SALVAS (limpas): {len(df_limpo)}")
        print(f"Total de linhas CORROMPIDAS (ignoradas): {linhas_corrompidas_detectadas}")
        print("="*50)
        print(f"\nPRÓXIMO PASSO (MANUAL):")
        print(f"1. Apague seu 'questoes.csv' antigo (corrompido).")
        print(f"2. Renomeie '{ARQUIVO_SAIDA_LIMPO}' para 'questoes.csv'.")
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO ao tentar ler ou salvar o arquivo: {e}")

if __name__ == "__main__":
    filtrar_arquivo_corrompido()
