# -*- coding: utf-8 -*-
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Carrega seu .env para pegar a chave
load_dotenv()

# Configura a API
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("="*50)
    print("ERRO: GEMINI_API_KEY não encontrada no seu arquivo .env")
    print("Verifique se o arquivo .env está na mesma pasta que este script.")
    print("="*50)
else:
    try:
        genai.configure(api_key=api_key)

        print("--- Verificando modelos Gemini compatíveis... ---")
        
        model_list = []
        for model in genai.list_models():
            # Queremos apenas os modelos que podem "gerar conteúdo"
            if 'generateContent' in model.supported_generation_methods:
                model_list.append(model.name)
        
        if not model_list:
            print("Nenhum modelo compatível com 'generateContent' foi encontrado.")
            print("Verifique se sua chave de API está correta e habilitada no Google AI Studio.")
        else:
            print("Modelos encontrados que você PODE usar:")
            for name in model_list:
                print(f"  -> {name}")
    
    except Exception as e:
        print(f"\nOcorreu um erro ao tentar listar os modelos: {e}")
        print("Verifique se sua GEMINI_API_KEY está correta e tem permissão no Google AI Studio.")
            
print("--- Verificação concluída ---")
