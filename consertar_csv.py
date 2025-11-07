# -*- coding: utf-8 -*-
import pandas as pd
import os

ARQUIVO_ORIGINAL = 'questoes_originais.csv' # O de 319 linhas
ARQUIVO_NOVAS_IA = 'novas_questoes_IA.csv' # Todas que eu te dei
ARQUIVO_SAIDA_LIMPO = 'questoes.csv' # O novo arquivo mestre

HEADER_FINAL = [
    'disciplina', 'materia', 'banca', 'dificuldade', 'enunciado',
    'alternativa_a', 'alternativa_b', 'alternativa_c', 'alternativa_d', 'alternativa_e',
    'resposta_correta', 'justificativa', 'dica', 'formula'
]

def reconstruir():
    print(f"--- Iniciando a Reconstrução do Banco de Questões (v2) ---")
    
    # 1. Carregar o arquivo original (13 colunas)
    try:
        df_original = pd.read_csv(ARQUIVO_ORIGINAL, sep=';', quotechar='"', encoding='utf-8-sig')
        print(f"✅ [1/3] Leu '{ARQUIVO_ORIGINAL}' ({len(df_original)} questões).")
    except Exception as e:
        print(f"❌ ERRO: Não foi possível ler o '{ARQUIVO_ORIGINAL}'. Verifique se o arquivo existe. Erro: {e}")
        return

    # 2. Corrigir o original: Adicionar a coluna 'banca'
    if 'banca' not in df_original.columns:
        df_original.insert(2, 'banca', 'Banca Padrão')
        print(f"   -> Coluna 'banca' adicionada ao arquivo original.")
    
    todos_os_dfs = [df_original]

    # 3. Carregar o arquivo com todas as questões da IA (com tolerância a erros)
    try:
        # (CORREÇÃO) Adicionado 'on_bad_lines='skip'' para ignorar linhas corrompidas
        df_novas = pd.read_csv(
            ARQUIVO_NOVAS_IA, 
            sep=';', 
            quotechar='"', 
            encoding='utf-8-sig',
            on_bad_lines='skip' # Ignora linhas com o número errado de colunas
        )
        print(f"✅ [2/3] Leu '{ARQUIVO_NOVAS_IA}' ({len(df_novas)} questões).")
        
        # Verifica se o cabeçalho está correto
        if list(df_novas.columns) != HEADER_FINAL:
             print(f"   -> AVISO: O cabeçalho de '{ARQUIVO_NOVAS_IA}' está diferente do esperado. Tentando corrigir...")
             # Tenta forçar os nomes das colunas com base no esperado
             if len(df_novas.columns) == len(HEADER_FINAL):
                 df_novas.columns = HEADER_FINAL
                 print("   -> Nomes de colunas corrigidos.")
             else:
                 print(f"   -> ERRO: O cabeçalho de '{ARQUIVO_NOVAS_IA}' tem {len(df_novas.columns)} colunas, mas 14 eram esperadas. Pulando este arquivo.")
                 df_novas = pd.DataFrame() # Cria um dataframe vazio para não quebrar a união
                 
        todos_os_dfs.append(df_novas)
        
    except Exception as e:
        print(f"⚠️ AVISO: Não foi possível ler '{ARQUIVO_NOVAS_IA}'. Pulando... Erro: {e}")

    # 4. Juntar todos os arquivos em um só
    df_final = pd.concat(todos_os_dfs, ignore_index=True)
    
    # 5. Garantir que o cabeçalho final está na ordem correta
    df_final = df_final.reindex(columns=HEADER_FINAL)

    # 6. Limpeza Final: Remover duplicatas (baseado no enunciado)
    total_antes = len(df_final)
    df_final.drop_duplicates(subset=['enunciado'], keep='last', inplace=True)
    total_depois = len(df_final)
    print(f"   -> Limpeza: {total_antes - total_depois} questões duplicadas foram removidas.")

    # 7. Salvar o novo arquivo mestre limpo
    try:
        df_final.to_csv(ARQUIVO_SAIDA_LIMPO, sep=';', quotechar='"', index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"🎉 SUCESSO! O arquivo '{ARQUIVO_SAIDA_LIMPO}' foi criado.")
        print(f"Total de questões unificadas: {len(df_final)}")
        print("="*50)
        
    except Exception as e:
        print(f"❌ ERRO ao salvar o arquivo final: {e}")

if __name__ == "__main__":
    reconstruir()
