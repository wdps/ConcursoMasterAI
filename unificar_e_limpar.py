# -*- coding: utf-8 -*-
import pandas as pd
import os

ARQUIVO_PRINCIPAL = 'questoes.csv'
ARQUIVO_NOVAS = 'novas questoes.csv'
ARQUIVO_SAIDA_LIMPO = 'questoes_FINAL.csv'

# O cabeçalho final de 14 colunas
HEADER_ESPERADO = [
    'disciplina', 'materia', 'banca', 'dificuldade', 'enunciado',
    'alternativa_a', 'alternativa_b', 'alternativa_c', 'alternativa_d', 'alternativa_e',
    'resposta_correta', 'justificativa', 'dica', 'formula'
]
N_COLUNAS_ESPERADO = len(HEADER_ESPERADO) # Exatamente 14

def unificar_e_limpar():
    print(f"--- Iniciando Migração e Limpeza (v5) ---")
    
    lista_dfs = [] # Lista para guardar os DataFrames limpos
    
    # 1. Ler e Limpar o ARQUIVO_PRINCIPAL ('questoes.csv')
    if os.path.exists(ARQUIVO_PRINCIPAL):
        print(f"Lendo '{ARQUIVO_PRINCIPAL}' (o corrompido)...")
        try:
            df_principal = pd.read_csv(
                ARQUIVO_PRINCIPAL, 
                sep=';', 
                quotechar='"', 
                encoding='utf-8-sig',
                on_bad_lines='skip', # Ignora as 64 linhas corrompidas
                header=None # Lê tudo como dados brutos
            )
            
            # Filtra apenas linhas com 14 colunas
            df_principal_limpo = df_principal[df_principal.apply(lambda x: x.count(), axis=1) == N_COLUNAS_ESPERADO]
            df_principal_limpo.columns = HEADER_ESPERADO # Define o cabeçalho correto
            lista_dfs.append(df_principal_limpo)
            print(f"✅ '{ARQUIVO_PRINCIPAL}' processado. {len(df_principal_limpo)} linhas boas mantidas.")
            
        except Exception as e:
            print(f"❌ ERRO ao ler '{ARQUIVO_PRINCIPAL}': {e}")
            return
    else:
        print(f"⚠️ AVISO: Arquivo '{ARQUIVO_PRINCIPAL}' não encontrado. Pulando...")

    # 2. Ler e Limpar o ARQUIVO_NOVAS ('novas questoes.csv')
    if os.path.exists(ARQUIVO_NOVAS):
        print(f"Lendo '{ARQUIVO_NOVAS}'...")
        try:
            df_novas = pd.read_csv(
                ARQUIVO_NOVAS, 
                sep=';', 
                quotechar='"', 
                encoding='utf-8-sig',
                on_bad_lines='skip', # Ignora linhas corrompidas (se houver)
                header=None # Lê tudo como dados brutos
            )
            
            # Filtra apenas linhas com 14 colunas
            df_novas_limpo = df_novas[df_novas.apply(lambda x: x.count(), axis=1) == N_COLUNAS_ESPERADO]
            df_novas_limpo.columns = HEADER_ESPERADO # Define o cabeçalho correto
            lista_dfs.append(df_novas_limpo)
            print(f"✅ '{ARQUIVO_NOVAS}' processado. {len(df_novas_limpo)} linhas boas mantidas.")
            
        except Exception as e:
            print(f"❌ ERRO ao ler '{ARQUIVO_NOVAS}': {e}")
            return
    else:
        print(f"❌ ERRO CRÍTICO: O arquivo '{ARQUIVO_NOVAS}' não foi encontrado.")
        return

    # 3. Unificar (Migrar) os arquivos limpos
    if not lista_dfs:
        print("Nenhum dado válido encontrado para migrar.")
        return
        
    df_final = pd.concat(lista_dfs, ignore_index=True)
    
    # 4. Limpeza Final: Remover duplicatas (do cabeçalho e de questões)
    df_final = df_final[df_final['disciplina'] != 'disciplina'] # Remove cabeçalhos duplicados
    df_final.drop_duplicates(subset=['enunciado'], keep='last', inplace=True)
    
    # 5. Salvar o novo arquivo mestre limpo
    try:
        df_final.to_csv(ARQUIVO_SAIDA_LIMPO, sep=';', quotechar='"', index=False, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"🎉 SUCESSO! A migração foi concluída.")
        print(f"Arquivo salvo como: '{ARQUIVO_SAIDA_LIMPO}'")
        print(f"Total de questões no novo arquivo limpo: {len(df_final)}")
        print("="*50)
        print(f"\nPRÓXIMO PASSO (MANUAL):")
        print(f"1. Apague seu 'questoes.csv' antigo (corrompido).")
        print(f"2. Renomeie '{ARQUIVO_SAIDA_LIMPO}' para 'questoes.csv'.")
        
    except Exception as e:
        print(f"❌ ERRO ao salvar o arquivo final: {e}")

if __name__ == "__main__":
    unificar_e_limpar()
