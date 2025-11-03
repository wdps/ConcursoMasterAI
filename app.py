# -*- coding: utf-8 -*-
import sqlite3
import json
import random
from flask import Flask, render_template, jsonify, request, session
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "chave-secreta-concursoia-2024"
DATABASE = 'database.db'

MAPA_AREAS = {
    "Língua Portuguesa": ["Língua Portuguesa"],
    "Exatas e Raciocínio Lógico": ["Matemática", "Raciocínio Lógico", "Matemática Financeira"],
    "Conhecimentos Jurídicos": ["Direito Administrativo", "Direito Constitucional"],
    "Conhecimentos Bancários e Vendas": ["Conhecimentos Bancários", "Vendas e Negociação", "Atualidades do Mercado Financeiro"],
    "Psicologia Clínica e Saúde": ["Psicologia", "Psicologia (Saúde)"],
    "Gestão de Pessoas": ["Psicologia (Gestão)"],
    "Informática": ["Informática"],
    "Atualidades Gerais": ["Atualidades"]
}

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    return conn

def setup_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        disciplina TEXT NOT NULL,
        materia TEXT NOT NULL,
        dificuldade TEXT,
        enunciado TEXT NOT NULL,
        alternativas TEXT NOT NULL,
        resposta_correta TEXT NOT NULL,
        justificativa TEXT,
        dica TEXT,
        formula TEXT,
        banca TEXT
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_questoes INTEGER NOT NULL,
        total_acertos INTEGER NOT NULL,
        percentual REAL NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS desempenho_materia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resultado_id INTEGER NOT NULL,
        materia TEXT NOT NULL,
        acertos INTEGER NOT NULL,
        total INTEGER NOT NULL,
        FOREIGN KEY (resultado_id) REFERENCES resultados (id)
    );
    """)
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/areas')
def get_areas():
    try:
        conn = get_db()
        cursor = conn.cursor()
        areas_com_contagem = []
        
        for area_nome, disciplinas_lista in MAPA_AREAS.items():
            if not disciplinas_lista:
                continue
                
            placeholders = ','.join('?' * len(disciplinas_lista))
            query = "SELECT COUNT(*) as total FROM questoes WHERE disciplina IN ({})".format(placeholders)
            cursor.execute(query, disciplinas_lista)
            row = cursor.fetchone()
            total_questoes = row['total'] if row else 0
            
            if total_questoes > 0:
                areas_com_contagem.append({
                    "nome_area": area_nome,
                    "disciplinas_incluidas": disciplinas_lista,
                    "total_questoes": total_questoes
                })
                
        conn.close()
        areas_com_contagem.sort(key=lambda x: x['total_questoes'], reverse=True)
        return jsonify({"success": True, "areas": areas_com_contagem})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/bancas')
def get_bancas():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT banca, COUNT(*) as total_questoes FROM questoes WHERE banca IS NOT NULL AND banca != '' GROUP BY banca ORDER BY total_questoes DESC")
        bancas_list = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({"success": True, "bancas": bancas_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/simulado/iniciar', methods=['POST'])
def iniciar_simulado():
    try:
        data = request.json
        areas_selecionadas = data.get('areas', [])
        banca_selecionada = data.get('banca', '')
        quantidade_str = data.get('quantidade', '10')

        if not areas_selecionadas:
            return jsonify({"success": False, "error": "Nenhuma área selecionada."}), 400

        disciplinas_para_buscar = []
        for area_nome in areas_selecionadas:
            if area_nome in MAPA_AREAS:
                disciplinas_para_buscar.extend(MAPA_AREAS[area_nome])
        
        disciplinas_unicas = list(set(disciplinas_para_buscar))
        
        if not disciplinas_unicas:
            return jsonify({"success": False, "error": "Nenhuma disciplina correspondente às áreas selecionadas."}), 400

        conn = get_db()
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(disciplinas_unicas))
        query_parts = ["SELECT * FROM questoes WHERE disciplina IN ({})".format(placeholders)]
        query_params = disciplinas_unicas
        
        if banca_selecionada and banca_selecionada != 'todas':
            query_parts.append("AND banca = ?")
            query_params.append(banca_selecionada)
        
        if quantidade_str == "295":
            query = " ".join(query_parts)
            cursor.execute(query, query_params)
            questoes_raw = cursor.fetchall()
            random.shuffle(questoes_raw)
        else:
            limite = int(quantidade_str)
            query = " ".join(query_parts) + " ORDER BY RANDOM() LIMIT ?"
            query_params.append(limite)
            cursor.execute(query, query_params)
            questoes_raw = cursor.fetchall()
        
        conn.close()
        
        if not questoes_raw:
             return jsonify({"success": False, "error": "Nenhuma questão encontrada para os filtros selecionados."}), 404

        questoes = []
        for q in questoes_raw:
            questao_dict = dict(q)
            questao_dict['alternativas'] = json.loads(q['alternativas'])
            questoes.append(questao_dict)

        session['simulado_ids'] = [q['id'] for q in questoes]
        session['simulado_respostas'] = {} 
        session['indice_atual'] = 0
        
        primeira_questao = questoes[0]
        
        return jsonify({
            "success": True,
            "total_questoes": len(questoes),
            "indice_atual": 0,
            "questao": primeira_questao,
            "resposta_anterior": None
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/simulado/questao/<int:indice>')
def get_questao(indice):
    questoes_ids = session.get('simulado_ids')
    if not questoes_ids:
        return jsonify({"success": False, "error": "Simulado não encontrado na sessão."}), 404
        
    total_questoes = len(questoes_ids)
    
    if 0 <= indice < total_questoes:
        session['indice_atual'] = indice
        questao_id = questoes_ids[indice]
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questoes WHERE id = ?", (questao_id,))
            q_raw = cursor.fetchone()
            conn.close()
            
            if not q_raw:
                return jsonify({"success": False, "error": "Questão não encontrada no DB."}), 404
            
            questao_atual = dict(q_raw)
            questao_atual['alternativas'] = json.loads(q_raw['alternativas'])
            resposta_anterior = session.get('simulado_respostas', {}).get(str(questao_atual['id']))
            
            return jsonify({
                "success": True,
                "total_questoes": total_questoes,
                "indice_atual": indice,
                "questao": questao_atual,
                "resposta_anterior": resposta_anterior
            })
        except Exception as e:
             return jsonify({"success": False, "error": f"Erro ao buscar questão: {e}"}), 500
    else:
        return jsonify({"success": False, "error": "Índice da questão fora dos limites."}), 404

@app.route('/api/simulado/responder', methods=['POST'])
def responder_questao():
    data = request.json
    questao_id = str(data.get('questao_id')) 
    alternativa_escolhida = data.get('alternativa', '').lower()
    
    questoes_ids = session.get('simulado_ids')
    respostas = session.get('simulado_respostas', {})

    if not questoes_ids:
        return jsonify({"success": False, "error": "Simulado não encontrado."}), 404
        
    if questao_id in respostas:
        return jsonify({"success": False, "error": "Esta questão já foi respondida."}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM questoes WHERE id = ?", (int(questao_id),))
        q_raw = cursor.fetchone()
        conn.close()
        
        if not q_raw:
             return jsonify({"success": False, "error": "ID da questão não encontrado no DB."}), 404
             
        questao_correta = dict(q_raw)
        resposta_certa = questao_correta['resposta_correta'].lower()
        acertou = (alternativa_escolhida == resposta_certa)

        respostas[questao_id] = {
            "alternativa_escolhida": alternativa_escolhida,
            "acertou": acertou
        }
        session['simulado_respostas'] = respostas
        
        return jsonify({
            "success": True,
            "acertou": acertou,
            "resposta_correta": resposta_certa.upper(),
            "justificativa": questao_correta.get('justificativa', 'Sem justificativa detalhada.')
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Erro ao verificar resposta: {e}"}), 500

@app.route('/api/simulado/finalizar', methods=['POST'])
def finalizar_simulado():
    questoes_ids = session.get('simulado_ids')
    respostas = session.get('simulado_respostas', {})
    
    if not questoes_ids:
        return jsonify({"success": False, "error": "Nenhum simulado ativo para finalizar."}), 404

    total_questoes = len(questoes_ids)
    total_acertos = 0
    desempenho_por_materia = defaultdict(lambda: {'acertos': 0, 'total': 0})

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(questoes_ids))
        query = "SELECT id, materia FROM questoes WHERE id IN ({})".format(placeholders)
        
        id_map = {id_val: i for i, id_val in enumerate(questoes_ids)}
        ordered_params = sorted(questoes_ids, key=lambda x: id_map[x])
        
        cursor.execute(query, ordered_params)
        questoes_raw = cursor.fetchall()
        questoes = [dict(q) for q in questoes_raw]

        for q in questoes:
            materia = q['materia']
            desempenho_por_materia[materia]['total'] += 1
            
            resposta = respostas.get(str(q['id']))
            if resposta and resposta['acertou']:
                total_acertos += 1
                desempenho_por_materia[materia]['acertos'] += 1

        percentual_acerto = round((total_acertos / total_questoes) * 100, 2) if total_questoes > 0 else 0

        cursor.execute("INSERT INTO resultados (total_questoes, total_acertos, percentual) VALUES (?, ?, ?)", 
                       (total_questoes, total_acertos, percentual_acerto))
        
        resultado_id = cursor.lastrowid

        for materia, stats in desempenho_por_materia.items():
            cursor.execute("INSERT INTO desempenho_materia (resultado_id, materia, acertos, total) VALUES (?, ?, ?, ?)",
                           (resultado_id, materia, stats['acertos'], stats['total']))

        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Erro ao salvar resultado: {e}")
        session.pop('simulado_ids', None)
        session.pop('simulado_respostas', None)
        session.pop('indice_atual', None)
        return jsonify({"success": False, "error": f"Erro ao salvar dados no banco: {e}"}), 500

    session.pop('simulado_ids', None)
    session.pop('simulado_respostas', None)
    session.pop('indice_atual', None)

    return jsonify({
        "success": True,
        "relatorio": {
            "total_questoes": total_questoes,
            "total_acertos": total_acertos,
            "percentual_acerto": percentual_acerto,
            "nota_final": percentual_acerto
        }
    })

@app.route('/api/redacao/temas')
def get_temas_redacao():
    temas = [
        {"id": 1, "titulo": "Os desafios da educação pública brasileira no século XXI"},
        {"id": 2, "titulo": "Impactos da inteligência artificial no mercado de trabalho"},
        {"id": 3, "titulo": "Crise hídrica e gestão sustentável dos recursos naturais"},
        {"id": 4, "titulo": "Violência urbana e políticas de segurança pública"},
        {"id": 5, "titulo": "Desafios do sistema de saúde pública no Brasil"},
        {"id": 6, "titulo": "A importância da preservação da Amazônia para o equilíbrio climático"},
        {"id": 7, "titulo": "Os efeitos das fake news na democracia brasileira"},
        {"id": 8, "titulo": "Mobilidade urbana e qualidade de vida nas grandes cidades"},
        {"id": 9, "titulo": "Desigualdade social e seus impactos no acesso à educação"},
        {"id": 10, "titulo": "Tecnologia e privacidade: os limites da exposição digital"},
        {"id": 11, "titulo": "Esporte como ferramenta de inclusão social"},
        {"id": 12, "titulo": "Desafios da alimentação saudável na sociedade contemporânea"},
        {"id": 13, "titulo": "Representatividade racial nos espaços de poder"},
        {"id": 14, "titulo": "Sustentabilidade e consumo consciente"},
        {"id": 15, "titulo": "Os impactos da pandemia COVID-19 na educação brasileira"},
        {"id": 16, "titulo": "Envelhecimento populacional e previdência social"},
        {"id": 17, "titulo": "Democratização do acesso à cultura no Brasil"},
        {"id": 18, "titulo": "Desafios da inclusão de pessoas com deficiência no mercado de trabalho"},
        {"id": 19, "titulo": "Violência doméstica durante o isolamento social"},
        {"id": 20, "titulo": "Importância do investimento em ciência e tecnologia"},
        {"id": 21, "titulo": "Crise habitacional e direito à moradia"},
        {"id": 22, "titulo": "Preconceito linguístico na sociedade brasileira"},
        {"id": 23, "titulo": "Desafios da produção agrícola sustentável"},
        {"id": 24, "titulo": "Saúde mental no ambiente de trabalho"},
        {"id": 25, "titulo": "Terceirização e direitos trabalhistas"},
        {"id": 26, "titulo": "Desafios da educação à distância no Brasil"},
        {"id": 27, "titulo": "Protagonismo juvenil na política nacional"},
        {"id": 28, "titulo": "Impactos do agrotóxico na saúde e meio ambiente"},
        {"id": 29, "titulo": "Democratização do acesso à internet no Brasil"},
        {"id": 30, "titulo": "Desafios da gestão do lixo urbano"},
        {"id": 31, "titulo": "Importância da vacinação para a saúde pública"},
        {"id": 32, "titulo": "Bullying e suas consequências no ambiente escolar"},
        {"id": 33, "titulo": "Desafios da mobilidade elétrica no Brasil"},
        {"id": 34, "titulo": "Cultura do cancelamento nas redes sociais"},
        {"id": 35, "titulo": "Desafios da educação sexual nas escolas"},
        {"id": 36, "titulo": "Impactos do turismo no desenvolvimento regional"},
        {"id": 37, "titulo": "Desafios da preservação do patrimônio histórico"},
        {"id": 38, "titulo": "Trabalho escravo contemporâneo no Brasil"},
        {"id": 39, "titulo": "Desafios do sistema prisional brasileiro"},
        {"id": 40, "titulo": "Importância do aleitamento materno"},
        {"id": 41, "titulo": "Desafios da erradicação do trabalho infantil"},
        {"id": 42, "titulo": "Impactos das queimadas no bioma Pantanal"},
        {"id": 43, "titulo": "Desafios da mobilidade para pessoas com deficiência"},
        {"id": 44, "titulo": "Importância da doação de órgãos"},
        {"id": 45, "titulo": "Desafios da produção cultural independente"},
        {"id": 46, "titulo": "Impactos dos aplicativos de transporte na economia"},
        {"id": 47, "titulo": "Desafios da proteção aos refugiados no Brasil"},
        {"id": 48, "titulo": "Importância da educação financeira nas escolas"},
        {"id": 49, "titulo": "Desafios do envelhecimento com dignidade"},
        {"id": 50, "titulo": "Impactos do desmatamento na biodiversidade"},
        {"id": 51, "titulo": "Desafios da segurança no trânsito brasileiro"},
        {"id": 52, "titulo": "Importância do esporte para o desenvolvimento infantil"},
        {"id": 53, "titulo": "Desafios da valorização dos profissionais da educação"},
        {"id": 54, "titulo": "Impactos da mineração em terras indígenas"},
        {"id": 55, "titulo": "Desafios do combate à evasão escolar"},
        {"id": 56, "titulo": "Importância da preservação dos oceanos"},
        {"id": 57, "titulo": "Desafios da agricultura familiar no Brasil"},
        {"id": 58, "titulo": "Impactos da automação nos empregos tradicionais"},
        {"id": 59, "titulo": "Desafios do acesso à justiça para populações vulneráveis"},
        {"id": 60, "titulo": "Importância do voluntariado para a sociedade"},
        {"id": 61, "titulo": "Desafios da produção de energia limpa no Brasil"},
        {"id": 62, "titulo": "Impactos da globalização na cultura brasileira"},
        {"id": 63, "titulo": "Desafios do ensino profissionalizante no Brasil"},
        {"id": 64, "titulo": "Importância da amamentação para o desenvolvimento infantil"},
        {"id": 65, "titulo": "Desafios da segurança alimentar nas periferias"},
        {"id": 66, "titulo": "Impactos da poluição sonora nas grandes cidades"},
        {"id": 67, "titulo": "Desafios da educação no campo"},
        {"id": 68, "titulo": "Importância do brincar para o desenvolvimento infantil"},
        {"id": 69, "titulo": "Desafios do combate à depressão na adolescência"},
        {"id": 70, "titulo": "Impactos do plástico nos ecossistemas marinhos"},
        {"id": 71, "titulo": "Desafios da inclusão digital da terceira idade"},
        {"id": 72, "titulo": "Importância da educação ambiental nas escolas"},
        {"id": 73, "titulo": "Desafios do transporte público nas metrópoles"},
        {"id": 74, "titulo": "Impactos da inteligência artificial na educação"},
        {"id": 75, "titulo": "Desafios da preservação das línguas indígenas"},
        {"id": 76, "titulo": "Importância da atividade física para a saúde mental"},
        {"id": 77, "titulo": "Desafios do saneamento básico no Brasil"},
        {"id": 78, "titulo": "Impactos da indústria da moda no meio ambiente"},
        {"id": 79, "titulo": "Desafios da educação para o trânsito"},
        {"id": 80, "titulo": "Importância da preservação dos rios urbanos"},
        {"id": 81, "titulo": "Desafios do combate à corrupção no Brasil"},
        {"id": 82, "titulo": "Impactos dos games no desenvolvimento cognitivo"},
        {"id": 83, "titulo": "Desafios da medicina preventiva no SUS"},
        {"id": 84, "titulo": "Importância da leitura na formação crítica"},
        {"id": 85, "titulo": "Desafios da mobilidade rural"},
        {"id": 86, "titulo": "Impactos do home office na sociedade"},
        {"id": 87, "titulo": "Desafios da preservação da fauna silvestre"},
        {"id": 88, "titulo": "Importância do teatro na educação"},
        {"id": 89, "titulo": "Desafios da reciclagem no Brasil"},
        {"id": 90, "titulo": "Impactos da música na saúde mental"},
        {"id": 91, "titulo": "Desafios do acesso à universidade pública"},
        {"id": 92, "titulo": "Importância do cooperativismo para o desenvolvimento"},
        {"id": 93, "titulo": "Desafios da segurança cibernética no Brasil"},
        {"id": 94, "titulo": "Impactos do veganismo no meio ambiente"},
        {"id": 95, "titulo": "Desafios da educação patrimonial"},
        {"id": 96, "titulo": "Importância dos museus para a cultura nacional"},
        {"id": 97, "titulo": "Desafios do combate ao assédio moral"},
        {"id": 98, "titulo": "Impactos da moda sustentável"},
        {"id": 99, "titulo": "Desafios da educação para relações étnico-raciais"},
        {"id": 100, "titulo": "Importância da filosofia na formação cidadã"}
    ]
    return jsonify({"success": True, "temas": temas})

@app.route('/api/redacao/corrigir-gemini', methods=['POST'])
def corrigir_gemini():
    data = request.json
    tema = data.get('tema')
    texto = data.get('texto')
    
    if not tema or not texto:
        return jsonify({"success": False, "error": "Tema e texto são obrigatórios."}), 400

    try:
        nota_simulada = random.randint(60, 95) 
        
        correcao_data = {
            "nota_final": nota_simulada,
            "analise_competencias": [
                {"competencia": "Competência 1: Domínio da norma culta", "nota": round(nota_simulada * 0.18), "comentario": "Bom domínio da norma padrão, com poucos desvios gramaticais."},
                {"competencia": "Competência 2: Compreensão do tema e estrutura", "nota": round(nota_simulada * 0.20), "comentario": "Tema compreendido adequadamente com estrutura dissertativa clara."},
                {"competencia": "Competência 3: Argumentação e repertório", "nota": round(nota_simulada * 0.19), "comentario": "Argumentos consistentes, poderia usar mais repertório sociocultural."},
                {"competencia": "Competência 4: Coesão e coerência", "nota": round(nota_simulada * 0.20), "comentario": "Texto coeso com boa progressão argumentativa."},
                {"competencia": "Competência 5: Proposta de intervenção", "nota": round(nota_simulada * 0.23), "comentario": "Proposta concreta e detalhada, respeitando os direitos humanos."}
            ],
            "pontos_fortes": ["Estrutura organizada", "Argumentação clara", "Proposta de intervenção completa"],
            "pontos_fracos": ["Poderia usar mais exemplos concretos", "Repertório sociocultural limitado"],
            "sugestoes_melhoria": ["Ampliar o repertório de citações", "Desenvolver mais os exemplos"],
            "dicas_concursos": ["Mantenha a estrutura dissertativa", "Use conectivos variados", "Revise a concordância verbal"]
        }
        
        return jsonify({"success": True, "correcao": correcao_data})
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Erro ao processar correção: {e}"}), 500

@app.route('/api/dashboard/estatisticas-areas')
def get_dashboard_stats_areas():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Estatísticas gerais
        cursor.execute("SELECT COUNT(*) FROM questoes")
        total_questoes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM resultados")
        total_simulados_feitos = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(percentual) FROM resultados")
        media_geral_percentual = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(total_acertos) FROM resultados")
        total_acertos_geral = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(total_questoes) FROM resultados")
        total_questoes_geral = cursor.fetchone()[0] or 0
        
        # Melhor desempenho
        cursor.execute("SELECT data, percentual FROM resultados ORDER BY percentual DESC LIMIT 1")
        melhor_desempenho_row = cursor.fetchone()
        melhor_desempenho = dict(melhor_desempenho_row) if melhor_desempenho_row else None
        
        # Estatísticas por área (SIMPLIFICADO - sem matérias individuais)
        desempenho_por_area = []
        
        for area_nome, disciplinas in MAPA_AREAS.items():
            if not disciplinas:
                continue
                
            # Total de questões na área
            placeholders = ','.join('?' * len(disciplinas))
            query_total = "SELECT COUNT(*) as total FROM questoes WHERE disciplina IN ({})".format(placeholders)
            cursor.execute(query_total, disciplinas)
            total_questoes_area = cursor.fetchone()[0]
            
            # Desempenho na área
            query_desempenho = """
                SELECT 
                    COALESCE(SUM(dm.acertos), 0) as acertos,
                    COALESCE(SUM(dm.total), 0) as total_respondidas
                FROM desempenho_materia dm
                WHERE dm.materia IN ({})
            """.format(placeholders)
            cursor.execute(query_desempenho, disciplinas)
            result = cursor.fetchone()
            
            total_acertos_area = result['acertos'] if result else 0
            total_respondidas_area = result['total_respondidas'] if result else 0
            
            if total_respondidas_area > 0:
                percentual = round((total_acertos_area / total_respondidas_area) * 100, 2)
            else:
                percentual = 0
                
            desempenho_por_area.append({
                "area": area_nome,
                "total_questoes": total_questoes_area,
                "total_acertos": total_acertos_area,
                "total_respondidas": total_respondidas_area,
                "percentual": percentual
            })
        
        # Histórico recente (após remover desempenho por matéria)
        cursor.execute("SELECT id, data, total_questoes, total_acertos, percentual FROM resultados ORDER BY data DESC LIMIT 5")
        historico_recente = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "stats_gerais": {
                "total_questoes_banco": total_questoes,
                "total_simulados_feitos": total_simulados_feitos,
                "media_geral_percentual": round(media_geral_percentual, 2),
                "total_acertos_geral": total_acertos_geral,
                "total_questoes_geral": total_questoes_geral,
                "melhor_desempenho": melhor_desempenho
            },
            "desempenho_por_area": desempenho_por_area,
            "historico_recente": historico_recente
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    setup_db()
    app.run(debug=True, port=5000)
