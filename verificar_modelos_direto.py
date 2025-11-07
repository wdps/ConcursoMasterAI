# -*- coding: utf-8 -*-
import google.generativeai as genai
import os

print("="*50)
print("Este script vai verificar sua chave Gemini diretamente.")
# Pede a chave direto no terminal
api_key = input("COLE sua GEMINI_API_KEY aqui e aperte Enter: ")
print("="*50)


if not api_key or len(api_key) < 10:
    print("ERRO: A chave parece estar vazia ou é inválida.")
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
        print("Verifique se sua GEMINI_API_KEY está correta.")
            
print("--- Verificação concluída ---")
