# -*- coding: utf-8 -*-
import pandas as pd
import json
import random
import os
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, session
from collections import defaultdict
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func # (NOVO) Para usar funções como AVG, SUM, COUNT

load_dotenv() # Carrega variáveis do .env

app = Flask(__name__)

# ---
# --- (ALTERADO) Configuração do Banco de Dados (Pronto para Nuvem) ---
# ---
# Lê as variáveis de ambiente (do Render ou do seu .env local)
DATABASE_URL = os.environ.get('DATABASE_URL')
SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-padrao-local-para-testes-seguros')

if not DATABASE_URL:
    # Para testes locais, podemos apontar para um SQLite, mas o ideal é o Render
    print("AVISO: DATABASE_URL não definida, usando SQLite local 'database.db'")
    DATABASE_URL = 'sqlite:///database.db'
    
# Configura o app
app.secret_key = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o SQLAlchemy
db = SQLAlchemy(app)

# ---
# --- FONTE DE DADOS PRINCIPAL (PANDAS - Inalterado) ---
# ---
try:
    df_questoes = pd.read_csv('questoes.csv', sep=';', quotechar='"')
    df_questoes = df_questoes.fillna('')
    # Usar o índice do DataFrame como 'id' universal da questão
    df_questoes.index.name = 'id'
    print(f"INFO: 'questoes.csv' carregado com sucesso. Total: {len(df_questoes)} questões.")
except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível ler 'questoes.csv'. Erro: {e}")
    df_questoes = pd.DataFrame()
# --- FIM DA FONTE DE DADOS ---

# ---
# --- MAPA DE ÁREAS (Usado pela API /api/areas - Inalterado) ---
# ---
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

# ---
# --- (NOVO) Modelos do Banco de Dados (Substitui o SQL do init-db) ---
# ---
# Isso traduz suas tabelas para Classes Python

class ResultadosSimulados(db.Model):
    __tablename__ = 'resultados_simulados'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False, default=1) # Fixo em 1 por enquanto
    data = db.Column(db.DateTime, server_default=func.now())
    total_questoes = db.Column(db.Integer, nullable=False)
    total_acertos = db.Column(db.Integer, nullable=False)
    percentual_acerto = db.Column(db.Float, nullable=False)
    tipo_simulado = db.Column(db.String(50), default='normal')

class RespostasUsuarios(db.Model):
    __tablename__ = 'respostas_usuarios'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False, default=1)
    questao_id = db.Column(db.Integer, nullable=False)
    acertou = db.Column(db.Boolean, nullable=False)
    data_resposta = db.Column(db.DateTime, server_default=func.now())
    disciplina = db.Column(db.String(100))

class MetasUsuarios(db.Model):
    __tablename__ = 'metas_usuarios'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False, default=1)
    tipo_meta = db.Column(db.String(100), nullable=False)
    valor_meta = db.Column(db.Float, nullable=False)
    valor_atual = db.Column(db.Float, default=0)
    concluida = db.Column(db.Boolean, default=False)

class DesempenhoAreas(db.Model):
    __tablename__ = 'desempenho_areas'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False, default=1)
    area = db.Column(db.String(100), nullable=False)
    total_questoes = db.Column(db.Integer, default=0)
    total_acertos = db.Column(db.Integer, default=0)
    percentual_acerto = db.Column(db.Float, default=0)
    # Adiciona a restrição 'UNIQUE'
    __table_args__ = (db.UniqueConstraint('usuario_id', 'area', name='_usuario_area_uc'),)


# ---
# --- (REMOVIDO) Funções get_db() e close_connection() ---
# O SQLAlchemy gerencia conexões automaticamente.
# ---

# ---
# --- (ALTERADO) Comando init-db agora usa SQLAlchemy ---
# ---
@app.cli.command('init-db')
def init_db_command():
    """Limpa os dados existentes e cria novas tabelas."""
    try:
        print('Limpando tabelas existentes (se houver)...')
        db.drop_all()
        print('Criando novas tabelas...')
        db.create_all()
        print('Banco de dados inicializado com as novas tabelas.')
    except Exception as e:
        print(f"Erro ao inicializar o banco: {e}")
        print("Certifique-se que a DATABASE_URL está correta e o banco acessível.")

# ---
# --- Rota Principal (Inalterada) ---
# ---
@app.route('/')
def index():
    return render_template('index.html')

# ---
# --- API (Backend) para o JavaScript ---
# ---
@app.route('/api/areas')
def get_areas():
    # Esta rota não usa o banco de dados, inalterada
    try:
        if df_questoes.empty:
            return jsonify({"success": False, "error": "Banco de questões não carregado"}), 500
        
        contagem_disciplinas = df_questoes['disciplina'].value_counts().to_dict()
        areas_agrupadas = []
        
        for area_principal, sub_materias in MAPA_AREAS.items():
            total_questoes_area = 0
            sub_materias_existentes = []
            
            for sub_materia in sub_materias:
                if sub_materia in contagem_disciplinas:
                    total_questoes_area += contagem_disciplinas[sub_materia]
                    sub_materias_existentes.append(sub_materia)
            
            if total_questoes_area > 0 and sub_materias_existentes:
                areas_agrupadas.append({
                    "area_principal": area_principal,
                    "sub_materias": sub_materias_existentes,
                    "total_questoes": int(total_questoes_area)
                })
        
        return jsonify({"success": True, "areas": areas_agrupadas})
        
    except Exception as e:
        print(f"ERRO em /api/areas: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ---
# --- (CORREÇÃO 2 - PARTE A) Rota /api/bancas ---
# ---
@app.route('/api/bancas')
def get_bancas():
    # Esta rota foi modificada para não ler a coluna 'banca', que não existe no seu CSV.
    try:
        if df_questoes.empty:
             return jsonify({"success": False, "error": "Banco de questões não carregado"}), 500
        
        # (CORREÇÃO) Remove a leitura da coluna 'banca'/'Banca_Organizadora' que não existe.
        # Retorna APENAS a banca padrão.
        bancas_reais = [{"banca": "(Banca Padrão)", "total_questoes": len(df_questoes)}]
        
        return jsonify({"success": True, "bancas": bancas_reais})
    except Exception as e:
        print(f"ERRO em /api/bancas: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
# --- FIM DA CORREÇÃO 2 - PARTE A ---


# ---
# --- API DO SIMULADO (Rotas de Sessão Inalteradas) ---
# ---

@app.route('/api/simulado/iniciar', methods=['POST'])
def iniciar_simulado():
    # Esta rota usa Pandas + Sessão
    try:
        data = request.json
        areas_selecionadas = data.get('areas', [])
        banca_selecionada = data.get('banca')
        quantidade_str = data.get('quantidade', '10')

        if not areas_selecionadas:
            return jsonify({"success": False, "error": "Nenhuma área selecionada."}), 400

        questoes_filtradas = df_questoes[df_questoes['disciplina'].isin(areas_selecionadas)]
        
        # --- (CORREÇÃO 2 - PARTE B) ---
        # A linha abaixo foi comentada pois a coluna 'banca' não existe no seu CSV.
        # if banca_selecionada and banca_selecionada != "(Banca Padrão)":
        #     questoes_filtradas = questoes_filtradas[questoes_filtradas['banca'] == banca_selecionada]
        # --- FIM DA CORREÇÃO 2 - PARTE B ---

        if questoes_filtradas.empty:
            return jsonify({"success": False, "error": "Nenhuma questão encontrada para os filtros selecionados."}), 404

        total_encontrado = len(questoes_filtradas)
        quantidade = int(quantidade_str)
        if quantidade > total_encontrado:
            quantidade = total_encontrado
        
        questoes_selecionadas_df = questoes_filtradas.sample(n=quantidade)
        
        questoes_prontas = []
        ids_na_sessao = []
        
        for index, row in questoes_selecionadas_df.iterrows():
            alternativas_obj = {
                'a': row.get('alternativa_a'),
                'b': row.get('alternativa_b'),
                'c': row.get('alternativa_c'),
                'd': row.get('alternativa_d'),
                'e': row.get('alternativa_e')
            }
            
            questao_formatada = {
                "id": int(index),
                "disciplina": row.get('disciplina'),
                "materia": row.get('materia'),
                "dificuldade": row.get('dificuldade'),
                "enunciado": row.get('enunciado'),
                "alternativas": alternativas_obj, 
                "resposta_correta": row.get('resposta_correta'),
                "justificativa": row.get('justificativa'),
                "dica": row.get('dica'),
                "formula": row.get('formula')
            }
            questoes_prontas.append(questao_formatada)
            ids_na_sessao.append(int(index))

        session['simulado_ids'] = ids_na_sessao
        session['simulado_respostas'] = {}
        session['indice_atual'] = 0
        session['tipo_simulado'] = 'normal'
        
        primeira_questao = questoes_prontas[0]
        
        return jsonify({
            "success": True,
            "total_questoes": len(questoes_prontas),
            "indice_atual": 0,
            "questao": primeira_questao,
            "resposta_anterior": None
        })

    except Exception as e:
        print(f"ERRO 500 em /api/simulado/iniciar: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/simulado/questao/<int:indice>')
def get_questao(indice):
    # Esta rota usa Pandas + Sessão, inalterada
    questoes_ids = session.get('simulado_ids')
    if not questoes_ids:
        return jsonify({"success": False, "error": "Simulado não encontrado na sessão."}), 404
        
    total_questoes = len(questoes_ids)
    
    if 0 <= indice < total_questoes:
        session['indice_atual'] = indice
        questao_id = questoes_ids[indice]
        try:
            row = df_questoes.loc[questao_id]
            
            alternativas_obj = {
                'a': row.get('alternativa_a'),
                'b': row.get('alternativa_b'),
                'c': row.get('alternativa_c'),
                'd': row.get('alternativa_d'),
                'e': row.get('alternativa_e')
            }
            
            questao_atual = {
                "id": int(questao_id),
                "disciplina": row.get('disciplina'),
                "materia": row.get('materia'),
                "dificuldade": row.get('dificuldade'),
                "enunciado": row.get('enunciado'),
                "alternativas": alternativas_obj,
                "resposta_correta": row.get('resposta_correta'),
                "justificativa": row.get('justificativa'),
                "dica": row.get('dica'),
                "formula": row.get('formula')
            }
            
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

# ---
# --- (ALTERADO) API DO SIMULADO (Rotas com Banco de Dados) ---
# ---
@app.route('/api/simulado/responder', methods=['POST'])
def responder_questao():
    data = request.json
    questao_id = str(data.get('questao_id'))
    alternativa_escolhida = data.get('alternativa', '').lower()
    
    respostas = session.get('simulado_respostas', {})

    if questao_id in respostas:
        return jsonify({"success": False, "error": "Esta questão já foi respondida."}), 400

    try:
        row = df_questoes.loc[int(questao_id)]
             
        resposta_certa = row.get('resposta_correta', '').lower()
        acertou = (alternativa_escolhida == resposta_certa)

        respostas[questao_id] = {
            "alternativa_escolhida": alternativa_escolhida,
            "acertou": acertou,
            "disciplina": row.get('disciplina') # (NOVO) Salva a disciplina
        }
        session['simulado_respostas'] = respostas
        
        # (ALTERADO) Salva no banco de dados com SQLAlchemy
        try:
            nova_resposta = RespostasUsuarios(
                usuario_id=1, # Fixo por enquanto
                questao_id=int(questao_id),
                acertou=acertou,
                disciplina=row.get('disciplina')
            )
            db.session.add(nova_resposta)
            db.session.commit()
        except Exception as e_db:
            db.session.rollback() # Desfaz em caso de erro
            print(f"Erro ao salvar resposta no BD: {e_db}")
            # Não falha a requisição, mas loga o erro

        return jsonify({
            "success": True,
            "acertou": acertou,
            "resposta_correta": resposta_certa.upper(),
            "justificativa": row.get('justificativa', 'Sem justificativa detalhada.')
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Erro ao verificar resposta: {e}"}), 500

@app.route('/api/simulado/finalizar', methods=['POST'])
def finalizar_simulado():
    questoes_ids = session.get('simulado_ids')
    respostas = session.get('simulado_respostas', {})
    tipo_simulado = session.get('tipo_simulado', 'normal')
    
    if not questoes_ids:
        return jsonify({"success": False, "error": "Nenhum simulado ativo para finalizar."}), 404

    total_questoes = len(questoes_ids)
    total_acertos = 0
    desempenho_disciplina = defaultdict(lambda: {'acertos': 0, 'total': 0})

    try:
        # 1. Calcula acertos (lógica inalterada)
        for questao_id in questoes_ids:
            resposta = respostas.get(str(questao_id))
            if resposta:
                disciplina = resposta.get('disciplina', 'Indefinida')
                desempenho_disciplina[disciplina]['total'] += 1
                if resposta['acertou']:
                    total_acertos += 1
                    desempenho_disciplina[disciplina]['acertos'] += 1
        
        percentual_acerto = round((total_acertos / total_questoes) * 100, 1) if total_questoes > 0 else 0
        
        # (ALTERADO) Salva o resultado no banco com SQLAlchemy
        try:
            # 2. Salva o resultado geral
            novo_resultado = ResultadosSimulados(
                usuario_id=1,
                total_questoes=total_questoes,
                total_acertos=total_acertos,
                percentual_acerto=percentual_acerto,
                tipo_simulado=tipo_simulado
            )
            db.session.add(novo_resultado)
            
            # 3. Atualiza o desempenho por área
            for disciplina, stats in desempenho_disciplina.items():
                area_existente = DesempenhoAreas.query.filter_by(usuario_id=1, area=disciplina).first()
                
                if area_existente:
                    area_existente.total_questoes += stats['total']
                    area_existente.total_acertos += stats['acertos']
                else:
                    area_existente = DesempenhoAreas(
                        usuario_id=1,
                        area=disciplina,
                        total_questoes=stats['total'],
                        total_acertos=stats['acertos']
                    )
                    db.session.add(area_existente)
                
                # Recalcula percentual da área
                if area_existente.total_questoes > 0:
                    area_existente.percentual_acerto = round((area_existente.total_acertos / area_existente.total_questoes) * 100, 1)
            
            # 4. Atualiza metas (simples)
            # (Otimizado: faz updates diretos sem SELECT primeiro)
            db.session.query(MetasUsuarios).filter_by(
                usuario_id=1, tipo_meta='simulados_realizados', concluida=False
            ).update({'valor_atual': MetasUsuarios.valor_atual + 1})
            
            db.session.query(MetasUsuarios).filter_by(
                usuario_id=1, tipo_meta='questoes_resolvidas', concluida=False
            ).update({'valor_atual': MetasUsuarios.valor_atual + total_questoes})

            # Para a média, precisamos calcular primeiro
            media_geral_query = db.session.query(func.avg(ResultadosSimulados.percentual_acerto)).filter_by(usuario_id=1).scalar()
            media_geral = round(media_geral_query or 0, 1)
            
            db.session.query(MetasUsuarios).filter_by(
                usuario_id=1, tipo_meta='percentual_acerto', concluida=False
            ).update({'valor_atual': media_geral})

            db.session.commit()
        
        except Exception as e_db:
            db.session.rollback()
            print(f"Erro ao salvar resultado final no BD: {e_db}")
            # Não falha a requisição, mas loga o erro

    except Exception as e:
        print(f"Erro ao calcular resultado: {e}")
        return jsonify({"success": False, "error": f"Erro ao calcular dados: {e}"}), 500

    # Limpa a sessão (inalterado)
    session.pop('simulado_ids', None)
    session.pop('simulado_respostas', None)
    session.pop('indice_atual', None)
    session.pop('tipo_simulado', None)

    return jsonify({
        "success": True,
        "relatorio": {
            "total_questoes": total_questoes,
            "total_acertos": total_acertos,
            "percentual_acerto": percentual_acerto,
            "nota_final": percentual_acerto # Nota final por enquanto é o percentual
        }
    })

# ============================================================================
# 🎯 (ALTERADO) DASHBOARD SIMPLIFICADO - FOCADO EM METAS
# ============================================================================
@app.route('/api/dashboard/simplificado')
def get_dashboard_simplificado():
    try:
        # (ALTERADO) O SQLAlchemy cuida da conexão/cursor e do fechamento
        
        # Métricas principais (usando 1 como ID de usuário fixo)
        total_simulados = db.session.query(ResultadosSimulados).filter_by(usuario_id=1).count()
        
        media_geral_query = db.session.query(func.avg(ResultadosSimulados.percentual_acerto)).filter_by(usuario_id=1).scalar()
        media_geral = media_geral_query or 0
        
        total_acertos_query = db.session.query(func.sum(ResultadosSimulados.total_acertos)).filter_by(usuario_id=1).scalar()
        total_acertos = total_acertos_query or 0
        
        progresso_geral = min(100, round(media_geral, 1))
        
        # Metas ativas
        metas = MetasUsuarios.query.filter_by(usuario_id=1, concluida=False).limit(3).all()
        
        # Áreas de destaque
        areas = DesempenhoAreas.query.filter_by(usuario_id=1).order_by(DesempenhoAreas.percentual_acerto.desc()).limit(3).all()
                
        return jsonify({
            "success": True,
            "metricas": {
                "total_simulados": total_simulados,
                "media_geral": round(media_geral, 1),
                "total_acertos": total_acertos,
                "progresso_geral": progresso_geral
            },
            "metas": [
                {
                    "tipo": meta.tipo_meta,
                    "valor_meta": meta.valor_meta,
                    "valor_atual": meta.valor_atual,
                    "progresso": min(100, (meta.valor_atual / meta.valor_meta) * 100) if meta.valor_meta > 0 else 0
                } for meta in metas
            ],
            "areas_destaque": [
                {
                    "area": area.area,
                    "percentual": area.percentual_acerto or 0
                } for area in areas
            ]
        })
        
    except Exception as e:
        print(f"Erro no Dashboard: {e}")
        # db.session.rollback() # Não necessário para SELECTs
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/dashboard/criar-meta', methods=['POST'])
def criar_meta():
    try:
        data = request.json
        
        # (ALTERADO) Cria o objeto Meta e adiciona
        nova_meta = MetasUsuarios(
            usuario_id=1,
            tipo_meta=data['tipo'],
            valor_meta=float(data['valor_meta']),
            valor_atual=0
        )
        db.session.add(nova_meta)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Meta criada com sucesso!"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# 🔄 (ALTERADO) SISTEMA DE REVISÃO ESPAÇADA
# ============================================================================
@app.route('/api/simulado/revisao-espacada', methods=['POST'])
def iniciar_revisao_espacada():
    try:
        # (ALTERADO) Pega 10 questões que o usuário errou
        # NOTA: func.random() funciona no SQLite e PostgreSQL.
        query = db.session.query(RespostasUsuarios.questao_id).filter_by(
            usuario_id=1, 
            acertou=False
        ).order_by(func.random()).limit(10)
        
        questao_ids = [row.questao_id for row in query.all()]
        
        if not questao_ids:
            return jsonify({"success": False, "error": "Nenhuma questão para revisão encontrada. Você acertou tudo!"}), 404
        
        # O resto da lógica usa Pandas, inalterado
        questoes_revisao = df_questoes.loc[df_questoes.index.isin(questao_ids)]
        
        if questoes_revisao.empty:
            return jsonify({"success": False, "error": "Questões não encontradas no banco de dados CSV."}), 404
        
        questoes_formatadas = []
        ids_na_sessao = []
        for index, row in questoes_revisao.iterrows():
            questao = {
                "id": int(index),
                "disciplina": row.get('disciplina'),
                "materia": row.get('materia'),
                "dificuldade": row.get('dificuldade'),
                "enunciado": row.get('enunciado'),
                "alternativas": {
                    'a': row.get('alternativa_a'),
                    'b': row.get('alternativa_b'),
                    'c': row.get('alternativa_c'),
                    'd': row.get('alternativa_d'),
                    'e': row.get('alternativa_e')
                },
                "resposta_correta": row.get('resposta_correta'),
                "justificativa": row.get('justificativa'),
                "dica": row.get('dica'),
                "formula": row.get('formula')
            }
            questoes_formatadas.append(questao)
            ids_na_sessao.append(int(index))
        
        # Configurar sessão
        session['simulado_ids'] = ids_na_sessao
        session['simulado_respostas'] = {}
        session['indice_atual'] = 0
        session['tipo_simulado'] = 'revisao_espacada'
        
        return jsonify({
            "success": True,
            "total_questoes": len(questoes_formatadas),
            "questao_atual": questoes_formatadas[0], # (NOVO) Nome da chave corrigido
            "indice_atual": 0
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# 📝 SISTEMA DE REDAÇÃO (Inalterado, não usa banco de dados)
# ============================================================================

# (LISTA COMPLETA INCLUÍDA)
TEMAS_REDACAO_MELHORADOS = [
    {
        "id": 1,
        "titulo": "Os desafios da educação pública brasileira no século XXI",
        "enunciado": "A partir da leitura dos textos motivadores e com base nos conhecimentos construídos ao longo de sua formação, redija texto dissertativo-argumentativo sobre o tema 'Os desafios da educação pública brasileira no século XXI', apresentando proposta de intervenção que respeite os direitos humanos.",
        "textos_base": [
            "Texto 1: 'Segundo dados do INEP, 45% dos jovens brasileiros não concluem o ensino médio na idade adequada. A evasão escolar e a defasagem idade-série são problemas crônicos que afetam principalmente a população de baixa renda.' (Fonte: INEP/MEC)",
            "Texto 2: 'A valorização do professor é essencial para a qualidade da educação. No entanto, o piso salarial nacional dos professores da educação básica ainda está aquém do de outras profissões com nível de formação similar.' (Fonte: DIEESE)",
            "Texto 3: 'Tecnologias educacionais podem potencializar o ensino, mas exigem infraestrutura. A pandemia de COVID-19 expôs a desigualdade digital, onde milhões de alunos da rede pública não tiveram acesso a aulas remotas por falta de internet ou equipamentos.' (Fonte: Cetic.br)"
        ]
    },
    {
        "id": 2, 
        "titulo": "Impactos da inteligência artificial no mercado de trabalho",
        "enunciado": "Com base nos textos de apoio e em seus conhecimentos prévios, escreva uma redação dissertativo-argumentativa sobre o tema 'Impactos da inteligência artificial no mercado de trabalho', propondo soluções para os desafios identificados.",
        "textos_base": [
            "Texto 1: 'Estudo do Fórum Econômico Mundial estima que, até 2025, 85 milhões de empregos podem ser deslocados pela automação, enquanto 97 milhões de novas funções podem emergir, exigindo requalificação massiva.' (Fonte: Fórum Econômico Mundial)",
            "Texto 2: 'A IA não apenas automatiza tarefas repetitivas, mas também começa a realizar atividades complexas, como diagnóstico médico e análise jurídica. O desafio não é competir com a máquina, mas aprender a colaborar com ela.' (Kai-Fu Lee, especialista em IA)",
            "Texto 3: 'A desigualdade pode aumentar se não houver políticas públicas de transição. Trabalhadores com menor qualificação são os mais vulneráveis à automação, enquanto a demanda por especialistas em dados e IA cresce exponencialmente.' (Fonte: OIT)"
        ]
    },
    {
        "id": 3,
        "titulo": "Sustentabilidade e consumo consciente como pilares para o futuro",
        "enunciado": "Considerando os textos motivadores, redija um texto dissertativo-argumentativo sobre o tema 'Sustentabilidade e consumo consciente como pilares para o futuro', apresentando uma proposta de intervenção social.",
        "textos_base": [
            "Texto 1: 'O Brasil é um dos maiores produtores de lixo plástico do mundo, produzindo cerca de 11 milhões de toneladas por ano, mas reciclando efetivamente menos de 2% desse total.' (Fonte: WWF Brasil)",
            "Texto 2: 'A 'economia circular' propõe um modelo onde não existe 'lixo'. Os produtos são desenhados para serem reutilizados, reparados e, em último caso, reciclados, mantendo os materiais em uso pelo maior tempo possível, em oposição ao modelo linear de 'extrair-produzir-descartar'.'",
            "Texto 3: 'Consumidores conscientes estão cada vez mais atentos à origem dos produtos, preferindo marcas com responsabilidade ambiental e social. Esta mudança de comportamento força as empresas a adaptarem suas cadeias de produção.' (Fonte: Pesquisa Akatu)"
        ]
    },
    {
        "id": 4,
        "titulo": "Desafios do sistema de saúde pública no Brasil (SUS)",
        "enunciado": "Com base nos textos de apoio, escreva uma redação sobre o tema 'Desafios do sistema de saúde pública no Brasil (SUS)', apresentando soluções para melhorar o atendimento à população.",
        "textos_base": [
            "Texto 1: 'O Sistema Único de Saúde (SUS) do Brasil é um dos maiores sistemas públicos de saúde do mundo, atendendo gratuitamente mais de 190 milhões de brasileiros. No entanto, sofre com subfinanciamento crônico.' (Fonte: OMS)",
            "Texto 2: 'A fila para procedimentos eletivos (não urgentes), como cirurgias e exames especializados, pode chegar a meses ou anos em diversos estados, agravando condições de saúde que poderiam ser tratadas preventivamente.' (Fonte: Conselho Federal de Medicina)",
            "Texto 3: 'A telemedicina, regulamentada durante a pandemia, surgiu como uma alternativa viável para desafogar o atendimento primário e triar casos, mas sua implementação esbarra na falta de acesso digital por parte da população mais pobre.' (Fonte: Ministério da Saúde)"
        ]
    },
    {
        "id": 5,
        "titulo": "A persistência da violência contra a mulher na sociedade brasileira",
        "enunciado": "A partir da análise dos textos motivadores, elabore uma redação dissertativo-argumentativa sobre o tema 'A persistência da violência contra a mulher na sociedade brasileira', propondo medidas para enfrentar esse problema.",
        "textos_base": [
            "Texto 1: 'Em 2023, o Brasil registrou um caso de feminicídio a cada 6 horas. A maioria dos crimes ocorre dentro de casa e é cometida por parceiros ou ex-parceiros.' (Fonte: Fórum Brasileiro de Segurança Pública)",
            "Texto 2: 'A Lei Maria da Penha (Lei nº 11.340/2006) é considerada pela ONU uma das três legislações mais avançadas do mundo no combate à violência doméstica. Contudo, a sua aplicação efetiva ainda enfrenta barreiras, como a falta de delegacias especializadas e casas-abrigo.'",
            "Texto 3: 'A cultura do machismo estrutural, que normaliza a posse sobre o corpo feminino e minimiza denúncias ('briga de marido e mulher'), é um dos principais fatores que perpetuam o ciclo de violência.' (Rita Segato, antropóloga)"
        ]
    },
    {
        "id": 6,
        "titulo": "Democratização do acesso à internet e o combate à exclusão digital",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre o tema 'Democratização do acesso à internet e o combate à exclusão digital no Brasil', abordando suas causas, consequências e propondo soluções.",
        "textos_base": [
            "Texto 1: 'Cerca de 28 milhões de brasileiros não têm acesso à internet, segundo a pesquisa TIC Domicílios 2023. Nas áreas rurais, esse percentual é significativamente maior, chegando a 45% dos domicílios.' (Fonte: Cetic.br)",
            "Texto 2: 'A exclusão digital não é apenas a falta de conexão; é também a falta de equipamentos adequados (computadores vs. apenas celular) e de letramento digital (saber usar as ferramentas de forma crítica e segura).'",
            "Texto 3: 'Durante a pandemia, o acesso à educação, saúde (telemedicina) e auxílios governamentais (Auxílio Emergencial) dependeu diretamente da conectividade, transformando a internet em um serviço essencial e um direito de cidadania.' (Fonte: Relatório PNAD COVID-19)"
        ]
    },
    {
        "id": 7,
        "titulo": "Mobilidade urbana sustentável: o desafio das metrópoles brasileiras",
        "enunciado": "Considerando os textos a seguir, elabore uma redação sobre o tema 'Mobilidade urbana sustentável: o desafio das metrópoles brasileiras', apresentando propostas de intervenção.",
        "textos_base": [
            "Texto 1: 'O tempo médio de deslocamento casa-trabalho em São Paulo ultrapassa 1 hora e 30 minutos por dia para quem depende de transporte público. Esse tempo perdido impacta a produtividade, a saúde mental e o lazer do cidadão.' (Fonte: Pesquisa Origem-Destino, Metrô-SP)",
            "Texto 2: 'A priorização histórica do transporte individual motorizado (carros e motos) levou ao colapso viário e a altos índices de poluição atmosférica. O setor de transportes é responsável por mais de 70% da emissão de gases de efeito estufa nas grandes cidades.' (Fonte: IPEA)",
            "Texto 3: 'Soluções de mobilidade sustentável incluem a expansão de malhas de metrô e VLT (Veículo Leve sobre Trilhos), a criação de faixas exclusivas de ônibus eficientes e a integração com ciclovias seguras, incentivando a intermodalidade.'"
        ]
    },
    {
        "id": 8,
        "titulo": "Saúde mental da população jovem no pós-pandemia",
        "enunciado": "Com base nos textos motivadores e em seus conhecimentos, redija um texto dissertativo-argumentativo sobre 'Saúde mental da população jovem no pós-pandemia', analisando os desafios para o poder público e a sociedade.",
        "textos_base": [
            "Texto 1: 'A OMS relatou um aumento de 25% na prevalência global de ansiedade e depressão apenas no primeiro ano da pandemia de COVID-19. Os jovens foram um dos grupos mais afetados devido à interrupção da educação e da socialização.' (Fonte: OMS)",
            "Texto 2: 'No Brasil, a demanda por atendimento psicológico na rede pública (CAPS) cresceu, mas a oferta de profissionais ainda é insuficiente. O estigma associado a transtornos mentais impede que muitos jovens busquem ajuda.' (Fonte: Ministério da Saúde)",
            "Texto 3: 'O uso excessivo de redes sociais é apontado como um fator agravante. A exposição a padrões de vida irreais e ao cyberbullying contribui para o aumento de quadros de ansiedade social e dismorfia corporal entre adolescentes.' (Fonte: Sociedade Brasileira de Pediatria)"
        ]
    },
    {
        "id": 9,
        "titulo": "A questão da segurança alimentar e o combate à fome no Brasil",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre o tema 'A questão da segurança alimentar e o combate à fome no Brasil', analisando os paradoxos de um país agroexportador.",
        "textos_base": [
            "Texto 1: 'Em 2023, mais de 30 milhões de brasileiros estavam em situação de insegurança alimentar grave (fome). Paradoxalmente, o Brasil é um dos maiores produtores de alimentos do mundo, batendo recordes de safra de grãos.' (Fonte: Rede PENSSAN)",
            "Texto 2: 'O modelo de agronegócio brasileiro é focado na exportação de commodities (soja, milho, carne) e não na produção de alimentos básicos que compõem a cesta do brasileiro (arroz, feijão, hortaliças), que majoritariamente vêm da agricultura familiar.' (Fonte: CONAB)",
            "Texto 3: 'A fome no Brasil não é um problema de produção, mas de acesso. A desigualdade de renda, o desemprego e a inflação dos alimentos são os principais determinantes da insegurança alimentar.' (Josué de Castro, 'Geografia da Fome')"
        ]
    },
    {
        "id": 10,
        "titulo": "Os limites entre liberdade de expressão e discurso de ódio",
        "enunciado": "A partir dos textos de apoio, redija uma dissertação argumentativa sobre 'Os limites entre liberdade de expressão e discurso de ódio', posicionando-se claramente sobre a necessidade de regulação.",
        "textos_base": [
            "Texto 1: 'A Constituição Federal de 1988 assegura a livre manifestação do pensamento (Art. 5º, IV), mas veda o anonimato. O mesmo artigo (XLI) estabelece que 'a lei punirá qualquer discriminação atentatória dos direitos e liberdades fundamentais'.' (Fonte: Constituição Federal)",
            "Texto 2: 'O 'paradoxo da tolerância', do filósofo Karl Popper, sugere que a tolerância ilimitada pode levar ao desaparecimento da própria tolerância. Se formos tolerantes com os intolerantes, os tolerantes serão destruídos e a tolerância com eles.'",
            "Texto 3: 'O debate sobre a regulação das redes sociais esbarra na definição do que constitui discurso de ódio. Críticos temem que a regulação possa ser usada como censura, enquanto defensores argumentam que a ausência dela permite a proliferação de ataques a minorias e à democracia.'"
        ]
    },
    {
        "id": 11,
        "titulo": "Desafios do sistema prisional brasileiro e a ressocialização",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'Desafios do sistema prisional brasileiro e a falha na ressocialização', propondo intervenções para reverter o quadro atual.",
        "textos_base": [
            "Texto 1: 'O Brasil possui a terceira maior população carcerária do mundo, com mais de 800 mil presos. O déficit de vagas ultrapassa 300 mil, resultando em superlotação extrema, condições insalubres e violações de direitos humanos.' (Fonte: DEPEN)",
            "Texto 2: 'O Supremo Tribunal Federal (STF) reconheceu o 'estado de coisas inconstitucional' do sistema prisional brasileiro, determinando medidas para aliviar a superlotação, mas a situação persiste.' (Decisão: ADPF 347)",
            "Texto 3: 'A taxa de reincidência criminal no Brasil é estimada em 70%. A falha do sistema em prover educação e trabalho dentro dos presídios contribui para que o detento, ao sair, retorne ao crime, muitas vezes cooptado por facções que dominam as unidades.' (Fonte: CNJ)"
        ]
    },
    {
        "id": 12,
        "titulo": "Preservação ambiental e o desenvolvimento econômico da Amazônia",
        "enunciado": "Com base nos textos de apoio, redija uma dissertação sobre o tema 'Preservação ambiental e o desenvolvimento econômico da Amazônia: como conciliar interesses?', apresentando propostas.",
        "textos_base": [
            "Texto 1: 'O desmatamento na Amazônia, impulsionado pela grilagem de terras, garimpo ilegal e pecuária extensiva, atingiu níveis alarmantes na última década, ameaçando o 'ponto de não retorno' da floresta.' (Fonte: INPE)",
            "Texto 2: 'A floresta amazônica é crucial para o regime de chuvas do Brasil (rios voadores) e para o equilíbrio climático global. Sua preservação não é apenas uma pauta ambiental, mas uma necessidade econômica e de segurança hídrica.' (Antônio Nobre, climatologista)",
            "Texto 3: 'A 'bioeconomia' (economia da floresta em pé) surge como alternativa. O manejo sustentável de açaí, castanha, óleos medicinais e o turismo ecológico podem gerar mais renda para a população local do que a pecuária ou a soja, com baixo impacto ambiental.' (Carlos Nobre, cientista)"
        ]
    },
    {
        "id": 13,
        "titulo": "O combate ao analfabetismo funcional no Brasil",
        "enunciado": "Elabore um texto dissertativo-argumentativo sobre o tema 'O combate ao analfabetismo funcional no Brasil', discutindo suas consequências para a cidadania e o desenvolvimento do país.",
        "textos_base": [
            "Texto 1: 'Segundo o Indicador de Alfabetismo Funcional (INAF), 29% da população brasileira entre 15 e 64 anos é considerada analfabeta funcional. São pessoas que, embora saibam ler e escrever frases simples, não conseguem interpretar textos ou aplicar a matemática no cotidiano.' (Fonte: INAF)",
            "Texto 2: 'O analfabeto funcional tem dificuldade em compreender um contrato de trabalho, uma bula de remédio ou uma notícia, tornando-se mais vulnerável a golpes, desinformação (fake news) e ao subemprego.'",
            "Texto 3: 'A raiz do problema está na baixa qualidade da educação básica, que foca na decodificação de letras, mas falha em desenvolver a interpretação crítica e o raciocínio lógico.' (Paulo Freire, 'A importância do ato de ler')"
        ]
    },
    {
        "id": 14,
        "titulo": "Adoção de crianças e adolescentes no Brasil: desafios e burocracia",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre o tema 'Adoção de crianças e adolescentes no Brasil: os desafios da burocracia e do perfil desejado'.",
        "textos_base": [
            "Texto 1: 'Existem hoje no Brasil cerca de 30 mil crianças e adolescentes em abrigos aguardando adoção. Em contrapartida, há mais de 45 mil pretendentes habilitados na fila.' (Fonte: Sistema Nacional de Adoção - SNA/CNJ)",
            "Texto 2: 'O paradoxo se explica pelo 'perfil'. 75% dos pretendentes buscam crianças de até 5 anos, brancas e sem irmãos. No entanto, 70% das crianças aptas à adoção têm mais de 8 anos, são pardas ou negras e possuem irmãos.' (Fonte: SNA/CNJ)",
            "Texto 3: 'A Lei nº 13.509/2017 (Lei da Adoção) buscou agilizar o processo, estabelecendo prazos máximos para a permanência da criança em abrigos. Contudo, a morosidade do Judiciário em destituir o poder familiar ainda é um entrave.'"
        ]
    },
    {
        "id": 15,
        "titulo": "Impacto das redes sociais na formação da identidade jovem",
        "enunciado": "Com base nos textos, escreva uma dissertação sobre o 'Impacto das redes sociais na formação da identidade jovem', analisando os aspectos positivos e negativos dessa influência.",
        "textos_base": [
            "Texto 1: 'Adolescentes passam, em média, mais de 4 horas diárias em redes sociais. Nesse ambiente, a 'cultura do like' e a busca por validação constante moldam a autoestima e a percepção de si mesmo.' (Fonte: Sociedade Brasileira de Pediatria)",
            "Texto 2: 'Por um lado, as redes permitem a conexão com grupos de interesse, a expressão criativa e o ativismo social. Por outro, a exposição a 'filtros' e vidas editadas gera ansiedade, depressão e a Síndrome de FOMO (Fear of Missing Out - Medo de Ficar de Fora).'",
            "Texto 3: 'Os algoritmos criam 'bolhas sociais' (câmaras de eco), onde o jovem deixa de ser exposto ao contraditório, o que pode empobrecer o debate e radicalizar opiniões, dificultando a construção de uma identidade crítica.' (Eli Pariser, 'O Filtro Invisível')"
        ]
    },
    {
        "id": 16,
        "titulo": "Desafios da valorização do professor na sociedade brasileira",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'Desafios da valorização do professor na sociedade brasileira', discutindo a relação entre formação, salário e prestígio social.",
        "textos_base": [
            "Texto 1: 'Nenhum país pode criar um sistema de ensino melhor do que a qualidade de seus professores.' (Relatório McKinsey, 2007). Países com alto desempenho educacional, como Finlândia e Coreia do Sul, possuem políticas rigorosas de formação e alto prestígio social da carreira docente.",
            "Texto 2: 'No Brasil, a carreira de professor da educação básica é marcada por baixos salários iniciais, condições de trabalho muitas vezes precárias (salas lotadas, falta de material) e violência escolar. Isso leva a uma baixa atratividade da carreira para os jovens mais talentosos.' (Fonte: Todos Pela Educação)",
            "Texto 3: 'A 'Síndrome de Burnout' (esgotamento profissional) atinge mais de 40% dos professores da rede pública, segundo pesquisas. A desvalorização não é apenas financeira, mas também simbólica, refletida na falta de respeito por parte de alunos e da sociedade.' (Fonte: Nova Escola)"
        ]
    },
    {
        "id": 17,
        "titulo": "A cultura do cancelamento e seus efeitos no debate público",
        "enunciado": "Elabore uma dissertação sobre 'A cultura do cancelamento e seus efeitos no debate público', discutindo se ela é uma forma de justiça social ou um linchamento virtual.",
        "textos_base": [
            "Texto 1: 'O 'cancelamento' é um fenômeno digital onde uma pessoa ou grupo é 'boicotado' publicamente após uma fala ou atitude considerada ofensiva, racista, machista ou homofóbica. Defensores veem o ato como uma ferramenta de accountability (responsabilização) para grupos historicamente silenciados.'",
            "Texto 2: 'Críticos argumentam que o cancelamento promove um tribunal da internet, sem direito à defesa, baseado em julgamentos apressados e desproporcionais, que não busca a reeducação, mas a punição e a exclusão social do 'cancelado'.'",
            "Texto 3: 'O medo do cancelamento pode levar à autocensura. Indivíduos e artistas podem deixar de expressar opiniões complexas ou controversas por receio da reação da 'multidão digital', empobrecendo o debate público e a nuance.' (Leigh Gilmore, 'Tainted Witness')"
        ]
    },
    {
        "id": 18,
        "titulo": "Transição energética: os desafios do Brasil para uma matriz limpa",
        "enunciado": "Com base nos textos, redija uma redação sobre o tema 'Transição energética: os desafios do Brasil para uma matriz limpa e justa'.",
        "textos_base": [
            "Texto 1: 'O Brasil possui uma das matrizes elétricas mais limpas do mundo, com alta participação de hidrelétricas (cerca de 60%). No entanto, a matriz de transportes é altamente dependente de combustíveis fósseis (gasolina e diesel).' (Fonte: Balanço Energético Nacional)",
            "Texto 2: 'A transição energética global busca substituir fósseis por fontes renováveis (solar, eólica, biomassa) para combater a crise climática. O Brasil tem potencial gigante para ser líder em energia solar e eólica, especialmente no Nordeste.'",
            "Texto 3: 'O desafio da transição é ser 'justa'. A instalação de grandes parques eólicos ou solares não pode ocorrer às custas da remoção de comunidades tradicionais ou sem gerar emprego local. Além disso, o custo dos carros elétricos ainda é proibitivo para a maioria da população.' (Fonte: IEA)"
        ]
    },
    {
        "id": 19,
        "titulo": "Desinformação (Fake News) e seus impactos na democracia",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'Desinformação (Fake News) e seus impactos na democracia brasileira', abordando a responsabilidade das plataformas e o papel da educação midiática.",
        "textos_base": [
            "Texto 1: 'A desinformação não é apenas 'mentira'. É a produção industrial de conteúdo enganoso, muitas vezes usando 'deepfakes' e robôs (bots), com o objetivo de manipular a opinião pública, corroer a confiança nas instituições (imprensa, ciência, Justiça) e influenciar eleições.'",
            "Texto 2: 'As plataformas digitais lucram com o engajamento. Algoritmos tendem a promover conteúdo 'chocante' e polarizado, pois ele gera mais cliques e compartilhamentos, mesmo que seja falso ou discurso de ódio.' (Shoshana Zuboff, 'A Era do Capitalismo de Vigilância')",
            "Texto 3: 'O combate à desinformação passa pela regulação das plataformas, mas fundamentalmente pela 'educação midiática'. É preciso ensinar a população, desde a escola, a checar fontes, identificar vieses e consumir informação de forma crítica.' (Fonte: UNESCO)"
        ]
    },
    {
        "id": 20,
        "titulo": "A questão do etarismo (preconceito etário) no mercado de trabalho",
        "enunciado": "Elabore uma dissertação sobre 'A questão do etarismo (preconceito etário) no mercado de trabalho', discutindo os desafios da inclusão de profissionais mais velhos na era digital.",
        "textos_base": [
            "Texto 1: 'Etarismo é o preconceito ou discriminação com base na idade. No mercado de trabalho, manifesta-se pela ideia de que profissionais acima de 50 anos são 'desatualizados', 'caros' ou 'resistentes à mudança', levando a demissões e dificuldade de recolocação.' (Fonte: OMS)",
            "Texto 2: 'A população brasileira está envelhecendo rapidamente. A Reforma da Previdência exige que se trabalhe por mais tempo, mas o mercado de trabalho expulsa os mais velhos, criando um limbo social.' (Fonte: IBGE)",
            "Texto 3: 'Empresas que promovem a diversidade etária (intergeracional) relatam ganhos de produtividade. A experiência dos mais velhos (soft skills, resiliência) combinada com a agilidade digital dos mais novos tende a criar equipes mais inovadoras.' (Fonte: Harvard Business Review)"
        ]
    },
    {
        "id": 21,
        "titulo": "A importância da doação de órgãos no Brasil",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'A importância da doação de órgãos no Brasil: desafios culturais e logísticos'.",
        "textos_base": [
            "Texto 1: 'Mais de 60 mil pessoas aguardam na fila por um transplante de órgão no Brasil. Muitas morrem antes de conseguir. O país possui um dos maiores programas públicos de transplantes do mundo, mas o principal gargalo é η falta de doadores.' (Fonte: Ministério da Saúde)",
            "Texto 2: 'No Brasil, a doação de órgãos só ocorre com autorização familiar (doação consentida), mesmo que o falecido tenha expressado o desejo em vida. A falta de diálogo sobre o tema em vida leva a altas taxas de recusa familiar (cerca de 40%).'",
            "Texto 3: 'Além da recusa, há desafios logísticos. O diagnóstico de morte encefálica precisa ser rápido e preciso, e o órgão captado precisa ser transportado (muitas vezes por via aérea) e transplantado em poucas horas, exigindo uma estrutura complexa do SUS.'"
        ]
    },
    {
        "id": 22,
        "titulo": "Exploração do trabalho infantil no Brasil",
        "enunciado": "Escreva uma dissertação sobre 'A persistência da exploração do trabalho infantil no Brasil', discutindo as causas e as consequências para o desenvolvimento social.",
        "textos_base": [
            "Texto 1: 'Cerca de 1,8 milhão de crianças e adolescentes (5 a 17 anos) estavam em situação de trabalho infantil no Brasil em 2019, antes da pandemia. A crise sanitária e econômica tende a ter agravado esse número.' (Fonte: IBGE/PNAD)",
            "Texto 2: 'O trabalho infantil perpetua o ciclo da pobreza. A criança que trabalha abandona a escola ou tem baixo rendimento, comprometendo sua qualificação e condenando-a a subempregos na vida adulta.' (Fonte: OIT)",
            "Texto 3: 'Existe uma romantização cultural do trabalho infantil, baseada na ideia de que 'é melhor trabalhar do que roubar' ou 'o trabalho enobrece'. Isso ignora os danos físicos (acidentes) e psicológicos (perda da infância) e viola o Estatuto da Criança e do Adolescente (ECA).' (Prioridade Absoluta - Art. 227, CF)"
        ]
    },
    {
        "id": 23,
        "titulo": "Gentrificação e o direito à moradia nas cidades",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'Gentrificação e o direito à moradia nas grandes cidades brasileiras', analisando o processo e seus impactos sociais.",
        "textos_base": [
            "Texto 1: 'Gentrificação é o processo de 'enobrecimento' de bairros periféricos ou centrais degradados. A chegada de investimentos (reformas, novos comércios, galerias de arte) valoriza os imóveis e o custo de vida, 'expulsando' os moradores originais de baixa renda para áreas ainda mais distantes.'",
            "Texto 2: 'O déficit habitacional no Brasil ultrapassa 6 milhões de moradias. Contudo, estima-se que existam mais de 7 milhões de imóveis vagos, a maioria em áreas centrais com infraestrutura (água, luz, transporte), evidenciando o caráter especulativo do mercado imobiliário.' (Fonte: Fundação João Pinheiro)",
            "Texto 3: 'A Constituição Federal (Art. 6º) garante o direito à moradia. O 'Plano Diretor' das cidades e as 'Zonas Especiais de Interesse Social (ZEIS)' são instrumentos legais para garantir que a população de baixa renda permaneça em áreas centrais, mas são frequentemente subutilizados.'"
        ]
    },
    {
        "id": 24,
        "titulo": "Os desafios da inclusão de pessoas com deficiência (PcD) no mercado de trabalho",
        "enunciado": "Com base nos textos de apoio, redija uma dissertação sobre 'Os desafios da inclusão de pessoas com deficiência (PcD) no mercado de trabalho brasileiro'.",
        "textos_base": [
            "Texto 1: 'A Lei de Cotas (Lei nº 8.213/91) exige que empresas com mais de 100 funcionários preencham de 2% a 5% de seus cargos com beneficiários reabilitados ou pessoas com deficiência. Mais de 30 anos depois, muitas empresas ainda não cumprem a lei.' (Fonte: Ministério do Trabalho)",
            "Texto 2: 'A inclusão enfrenta barreiras atitudinais (capacitismo - preconceito que assume a incapacidade da PcD) e arquitetônicas (falta de rampas, softwares acessíveis, transporte público adaptado).'",
            "Texto 3: 'A inclusão de PcD não é um favor, mas um direito garantido pelo Estatuto da Pessoa com Deficiência (Lei Brasileira de Inclusão). Empresas que investem em acessibilidade relatam melhora no clima organizacional e inovação ao pensar em soluções universais.'"
        ]
    },
    {
        "id": 25,
        "titulo": "O papel do esporte como ferramenta de inclusão social",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'O papel do esporte como ferramenta de inclusão social no Brasil', discutindo seu potencial e seus limites.",
        "textos_base": [
            "Texto 1: 'O esporte é um fenômeno social que ensina disciplina, respeito a regras, trabalho em equipe e resiliência. Para jovens em situação de vulnerabilidade, pode ser a única alternativa ao lazer da rua e ao aliciamento pelo crime.' (Nelson Mandela: 'O esporte tem o poder de mudar o mundo.')",
            "Texto 2: 'Projetos sociais em comunidades carentes que utilizam o esporte (futebol, artes marciais, vôlei) como base relatam melhora significativa na frequência escolar e redução da evasão e da violência local.' (Fonte: ONGs do Terceiro Setor)",
            "Texto 3: 'Apesar do potencial, o investimento público no esporte de base e educacional (nas escolas) ainda é baixo. O foco do investimento costuma ser o esporte de alto rendimento (competição), que atinge uma parcela mínima da população.'"
        ]
    },
    {
        "id": 26,
        "titulo": "Crise hídrica e a necessidade de gestão sustentável da água",
        "enunciado": "Escreva uma dissertação sobre 'Crise hídrica e a necessidade de gestão sustentável da água no Brasil', analisando as causas do problema e as soluções necessárias.",
        "textos_base": [
            "Texto 1: 'Embora o Brasil detenha 12% da água doce superficial do planeta, o país enfrenta crises hídricas recorrentes, como a que afetou o Sudeste em 2014-2015 e a atual na região Sul. A distribuição da água é desigual pelo território.' (Fonte: Agência Nacional de Águas - ANA)",
            "Texto 2: 'O principal vilão do consumo de água no Brasil é o agronegócio (irrigação), responsável por mais de 70% do uso. O desmatamento de nascentes e matas ciliares agrava o problema, reduzindo a recarga dos aquíferos e causando assoreamento dos rios.' (Fonte: ANA)",
            "Texto 3: 'A solução exige ações integradas: investimento em saneamento básico (45% do esgoto no Brasil não é tratado, poluindo os rios), técnicas de irrigação mais eficientes (gotejamento), reuso da água na indústria e combate ao desperdício nas redes de distribuição urbanas (onde 40% da água tratada se perde).'"
        ]
    },
    {
        "id": 27,
        "titulo": "O problema do lixo eletrônico (e-lixo) na sociedade digital",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'O problema do lixo eletrônico (e-lixo) na sociedade digital', abordando os riscos ambientais e as soluções.",
        "textos_base": [
            "Texto 1: 'O mundo gera mais de 50 milhões de toneladas de e-lixo (celulares, computadores, TVs) por ano. O Brasil é o maior produtor da América Latina. Menos de 20% desse lixo é formalmente reciclado globalmente.' (Fonte: ONU)",
            "Texto 2: 'O lixo eletrônico contém metais pesados altamente tóxicos (mercúrio, chumbo, cádmio) que, descartados em lixões comuns, contaminam o solo e os lençóis freáticos, causando graves problemas de saúde pública.'",
            "Texto 3: 'A 'obsolescência programada' (produtos feitos para durar pouco e forçar a compra de novos) é o motor desse problema. A solução passa pela 'logística reversa' (empresas sendo responsáveis por coletar e reciclar o que vendem) e pelo incentivo ao reparo e à economia circular.'"
        ]
    },
    {
        "id": 28,
        "titulo": "A importância da ciência e tecnologia para a soberania nacional",
        "enunciado": "Com base nos textos de apoio, redija uma dissertação sobre 'A importância do investimento em ciência e tecnologia para a soberania nacional'.",
        "textos_base": [
            "Texto 1: 'A 'fuga de cérebros' é um fenômeno onde cientistas e pesquisadores de alta qualificação, formados em universidades públicas brasileiras, deixam o país por falta de investimento, bolsas e infraestrutura em P&D (Pesquisa e Desenvolvimento).' (Fonte: CNPq)",
            "Texto 2: 'Países que não produzem ciência e tecnologia próprias tornam-se dependentes de patentes e equipamentos estrangeiros em áreas estratégicas, como saúde (produção de vacinas e fármacos), defesa e energia.'",
            "Texto 3: 'O investimento público em universidades e institutos de pesquisa (como Fiocruz e Butantan) é essencial. Durante a pandemia de COVID-19, foram esses institutos que garantiram a testagem e a produção de vacinas no Brasil, demonstrando a importância do investimento científico para a segurança nacional.'"
        ]
    },
    {
        "id": 29,
        "titulo": "A questão da população em situação de rua nos centros urbanos",
        "enunciado": "Elabore um texto dissertativo-argumentativo sobre 'A questão da população em situação de rua nos centros urbanos brasileiros', analisando as causas estruturais e as políticas de acolhimento.",
        "textos_base": [
            "Texto 1: 'O número de pessoas em situação de rua no Brasil cresceu exponencialmente nos últimos anos, impulsionado pelo desemprego estrutural, crise habitacional (preço dos aluguéis) e problemas de saúde mental e dependência química.' (Fonte: IPEA)",
            "Texto 2: 'A sociedade muitas vezes adota uma postura de 'aporofobia' (aversão aos pobres), tratando η população de rua como um caso de 'polícia' (higienização urbana) e não como um problema de 'assistência social' e 'saúde pública'.'",
            "Texto 3: 'Políticas de 'Housing First' (Moradia Primeiro), adotadas em vários países, mostram-se mais eficientes que abrigos temporários. Ao garantir uma moradia digna primeiro, o indivíduo consegue estabilidade para tratar a saúde e buscar reinserção no mercado de trabalho.'"
        ]
    },
    {
        "id": 30,
        "titulo": "Preconceito linguístico e a diversidade cultural do Brasil",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'Preconceito linguístico e a diversidade cultural do Brasil', defendendo um ponto de vista sobre o tema.",
        "textos_base": [
            "Texto 1: 'O preconceito linguístico é o julgamento de valor negativo sobre as variedades linguísticas de menor prestígio social, geralmente associadas a classes baixas ou regiões específicas (como o sotaque nordestino ou o 'falar caipira').' (Marcos Bagno, 'Preconceito Linguístico: O que é, Como se faz')",
            "Texto 2: 'A língua é viva e múltipla. Não existe 'falar errado', existe o 'falar diferente' ou o 'falar inadequado' ao contexto. A 'norma culta' é uma das variedades, necessária na escrita formal, mas não é a única forma 'correta' de se expressar.'",
            "Texto 3: 'A escola tem um papel dúbio: ao mesmo tempo que deve ensinar a norma culta (necessária para o acesso ao mercado de trabalho e universidade), não pode fazê-lo desvalorizando ou humilhando o aluno por seu 'falar' de origem, que é parte de sua identidade cultural.'"
        ]
    },
    {
        "id": 31,
        "titulo": "A importância da vacinação para a saúde coletiva",
        "enunciado": "Com base nos textos, escreva uma dissertação sobre 'A importância da vacinação para a saúde coletiva e os riscos dos movimentos antivacina'.",
        "textos_base": [
            "Texto 1: 'As vacinas são um dos maiores avanços da saúde pública, responsáveis pela erradicação da varíola e pelo controle de doenças como poliomielite e sarampo. Elas funcionam através da 'imunidade de rebanho': quanto mais pessoas vacinadas, menor a circulação do vírus, protegendo até quem não pode se vacinar.' (Fonte: OMS)",
            "Texto 2: 'O Brasil, que já foi referência mundial em imunização (PNI), viu sua cobertura vacinal infantil despencar nos últimos anos, caindo de 95% para menos de 70% em algumas vacinas, o que levou ao retorno do sarampo.' (Fonte: Ministério da Saúde)",
            "Texto 3: 'A hesitação vacinal é impulsionada por movimentos antivacina, que disseminam desinformação e teorias da conspiração (fake news) em redes sociais, minando a confiança da população na ciência e colocando a saúde coletiva em risco.' (Fonte: Sociedade Brasileira de Imunizações - SBIm)"
        ]
    },
    {
        "id": 32,
        "titulo": "O desafio da gravidez na adolescência no Brasil",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'O desafio da gravidez na adolescência no Brasil', analisando suas causas sociais e impactos no futuro das jovens.",
        "textos_base": [
            "Texto 1: 'O Brasil ainda apresenta taxas de gravidez na adolescência (10 a 19 anos) acima da média latino-americana. A maioria dos casos não é planejada e ocorre em contextos de vulnerabilidade social e baixa escolaridade.' (Fonte: IBGE)",
            "Texto 2: 'A gravidez precoce é uma das principais causas de evasão escolar feminina. A jovem mãe, muitas vezes sem apoio, abandona os estudos para cuidar do filho, o que limita suas oportunidades no mercado de trabalho e aprofunda o ciclo da pobreza.' (Fonte: UNICEF)",
            "Texto 3: 'A falta de acesso efetivo à informação e a métodos contraceptivos na rede pública, somada a tabus culturais e religiosos que dificultam a implementação da educação sexual nas escolas, contribui diretamente para a manutenção desses índices.'"
        ]
    },
    {
        "id": 33,
        "titulo": "A necessidade de regulamentação do trabalho por aplicativos (Uber, iFood)",
        "enunciado": "Elabore uma dissertação sobre 'A necessidade de regulamentação do trabalho por aplicativos no Brasil', discutindo a precarização das relações de trabalho.",
        "textos_base": [
            "Texto 1: 'Mais de 1,5 milhão de brasileiros têm o trabalho por aplicativos (como Uber e iFood) como principal fonte de renda. As plataformas os classificam como 'parceiros' ou 'autônomos', eximindo-se de vínculos empregatícios.' (Fonte: IPEA)",
            "Texto 2: 'Esses trabalhadores não têm direitos básicos garantidos pela CLT, como férias, 13º salário, limite de jornada ou seguro em caso de acidente. A 'uberização' é criticada por transferir todos os riscos do negócio (manutenção do veículo, combustível, acidentes) para o trabalhador.'",
            "Texto 3: 'O debate sobre a regulamentação busca um meio-termo: como garantir proteção social e previdenciária a esses trabalhadores (evitando a precarização) sem destruir a flexibilidade que é a base do modelo de negócio das plataformas?'"
        ]
    },
    {
        "id": 34,
        "titulo": "O vício em jogos eletrônicos: entre o lazer e a saúde pública",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'O vício em jogos eletrônicos (Gaming Disorder)', analisando os limites entre lazer e o problema de saúde pública.",
        "textos_base": [
            "Texto 1: 'Em 2018, a Organização Mundial da Saúde (OMS) incluiu o 'Gaming Disorder' (Transtorno de Jogo) na Classificação Internacional de Doenças (CID-11). O transtorno é caracterizado pela perda de controle sobre o ato de jogar, priorizando o jogo sobre outras atividades de vida.' (Fonte: OMS)",
            "Texto 2: 'Os jogos modernos, especialmente os online (MMORPGs) e os 'gacha' (baseados em sorte/loot box), são desenhados com mecanismos de recompensa variável (psicologia comportamental) para maximizar o engajamento e, em alguns casos, o gasto financeiro.'",
            "Texto 3: 'Para a maioria da população, os jogos são uma forma saudável de lazer, socialização e desenvolvimento de habilidades cognitivas (raciocínio rápido, estratégia). O desafio é diferenciar o uso intenso, mas saudável, da dependência patológica, que requer tratamento.'"
        ]
    },
    {
        "id": 35,
        "titulo": "A importância do patrimônio histórico-cultural para a identidade nacional",
        "enunciado": "Com base nos textos de apoio, redija uma dissertação sobre 'A importância da preservação do patrimônio histórico-cultural para a memória e identidade nacional'.",
        "textos_base": [
            "Texto 1: 'O patrimônio cultural de um povo (seus museus, igrejas, monumentos e saberes) é o elo material e imaterial entre o passado e o presente. Preservá-lo é preservar a memória coletiva e a identidade nacional.' (Fonte: IPHAN)",
            "Texto 2: 'Incêndios como o do Museu Nacional (2018), que destruiu 90% de um acervo de 20 milhões de itens, expõem o descaso crônico do poder público com o financiamento da preservação. A perda de acervos únicos é irrecuperável.'",
            "Texto 3: 'A educação patrimonial nas escolas é fundamental para que a população reconheça o valor desses bens e se torne agente ativo na sua fiscalização e preservação, entendendo que aquele patrimônio 'pertence' a ela.'"
        ]
    },
    {
        "id": 36,
        "titulo": "O endividamento das famílias brasileiras e a educação financeira",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'O endividamento das families brasileiras e o papel da educação financeira'.",
        "textos_base": [
            "Texto 1: 'Mais de 70% das famílias brasileiras estão endividadas (com cartão de crédito, cheque especial, financiamentos), e cerca de 30% estão inadimplentes (contas em atraso). O 'superendividamento' tornou-se um problema social grave.' (Fonte: Confederação Nacional do Comércio - CNC)",
            "Texto 2: 'As causas são múltiplas: a precarização do trabalho (baixa renda), a inflação (que corrói o poder de compra) e a facilidade de acesso ao crédito 'fácil' (com juros abusivos), especialmente o rotativo do cartão de crédito, um dos mais altos do mundo.'",
            "Texto 3: 'A educação financeira, incluída como tema transversal na Base Nacional Comum Curricular (BNCC), é vista como essencial para ensinar crianças e adultos a planejar orçamentos, poupar e evitar armadilhas de consumo, mas ainda não é realidade na maioria das escolas.'"
        ]
    },
    {
        "id": 37,
        "titulo": "Adoção tardia no Brasil: desafios e preconceitos",
        "enunciado": "Elabore uma dissertação sobre 'Adoção tardia no Brasil: os desafios para a garantia do direito à convivência familiar'.",
        "textos_base": [
            "Texto 1: 'Considera-se 'adoção tardia' a de crianças acima de 3 anos de idade. No Brasil, 90% dos pretendentes buscam crianças de até 3 anos, mas a maioria das crianças nos abrigos já passou dessa idade.' (Fonte: CNJ)",
            "Texto 2: 'O preconceito e o ideal de 'bebê perfeito' fazem com que crianças mais velhas, grupos de irmãos e crianças com problemas de saúde se tornem 'invisíveis' nos abrigos, crescendo institucionalizadas e perdendo o direito básico à convivência familiar.'",
            "Texto 3: 'Muitas crianças mais velhas são devolvidas aos abrigos após a adoção (re-abandono), um processo extremamente traumático. Isso ocorre pela falta de preparo dos adotantes para lidar com os traumas e a história prévia da criança, evidenciando a necessidade de acompanhamento psicológico pós-adoção.'"
        ]
    },
    {
        "id": 38,
        "titulo": "O papel da agricultura familiar na segurança alimentar do Brasil",
        "enunciado": "Com base nos textos, redija uma dissertação sobre 'O papel da agricultura familiar na segurança alimentar do Brasil', contrastando-a com o agronegócio.",
        "textos_base": [
            "Texto 1: 'A agricultura familiar é responsável por cerca de 70% dos alimentos que chegam à mesa dos brasileiros (mandioca, feijão, hortaliças, leite), apesar de ocupar menos de 25% da área agrícola total do país.' (Fonte: Censo Agropecuário/IBGE)",
            "Texto 2: 'Em contraste, o agronegócio utiliza a maior parte das terras para a produção de commodities de exportação (soja, milho, cana, gado), que não compõem a base da dieta nacional e geram menos empregos por hectare.'",
            "Texto 3: 'O fortalecimento da agricultura familiar, através de crédito rural (Pronaf), assistência técnica e programas de compra direta (PAA, PNAE - merenda escolar), é estratégico para garantir a segurança alimentar, a diversidade de alimentos e a geração de renda no campo.'"
        ]
    },
    {
        "id": 39,
        "titulo": "O combate ao tráfico de animais silvestres no Brasil",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'O combate ao tráfico de animais silvestres no Brasil e seus impactos na biodiversidade'.",
        "textos_base": [
            "Texto 1: 'O Brasil, país com a maior biodiversidade do mundo, é uma das principais vítimas do tráfico de animais silvestres. Estima-se que 38 milhões de animais (principalmente aves, como araras e papagaios) sejam retirados ilegalmente da natureza por ano.' (Fonte: RENCTAS)",
            "Texto 2: 'O tráfico de animais é a terceira maior atividade criminosa do mundo, movimentando bilhões de dólares. Para cada animal que chega ao 'consumidor' final, estima-se que nove morrem durante a captura ou transporte precário.'",
            "Texto 3: 'Além da crueldade, a retirada de animais da natureza causa desequilíbrio ecológico (afetando a polinização e a cadeia alimentar) e aumenta o risco de zoonoses (transmissão de doenças de animais para humanos).' (Fonte: WWF)"
        ]
    },
    {
        "id": 40,
        "titulo": "A 'fuga de cérebros' e o desenvolvimento científico nacional",
        "enunciado": "Redija uma dissertação sobre 'A 'fuga de cérebros' e seus impactos no desenvolvimento científico e tecnológico do Brasil'.",
        "textos_base": [
            "Texto 1: 'A 'fuga de cérebros' é a emigração de profissionais altamente qualificados (cientistas, médicos, engenheiros), formados com investimento público em universidades brasileiras, para países com melhores salários, infraestrutura de pesquisa e reconhecimento.' (Fonte: FAPESP)",
            "Texto 2: 'Contingenciamentos e cortes de verbas em Ciência e Tecnologia, baixos valores de bolsas de mestrado e doutorado (congeladas por anos) e a instabilidade política desestimulam a permanência de talentos no país.'",
            "Texto 3: 'Quando o Brasil 'exporta' um cientista, ele perde o potencial de inovação, a criação de patentes e a formação de novas gerações de pesquisadores, aumentando a dependência tecnológica do país em relação ao exterior.' (Relatório CGEE)"
        ]
    },
    {
        "id": 41,
        "titulo": "O desafio do saneamento básico no Brasil",
        "enunciado": "Escreva um texto dissertativo-argumentativo sobre 'O desafio do saneamento básico no Brasil e sua relação com a saúde pública e a desigualdade social'.",
        "textos_base": [
            "Texto 1: 'Quase 100 milhões de brasileiros não têm acesso à coleta de esgoto, e 35 milhões não têm acesso à água tratada. A maior parte dessa população está em áreas periféricas, rurais e na região Norte/Nordeste.' (Fonte: Instituto Trata Brasil)",
            "Texto 2: 'A falta de saneamento é a principal causa de doenças de veiculação hídrica (como diarreia, hepatite A, dengue), que sobrecarregam o SUS e são uma das maiores causas de mortalidade infantil.' (Fonte: OMS)",
            "Texto 3: 'O Novo Marco Legal do Saneamento (2020) busca universalizar o serviço até 2033, abrindo o setor para investimentos privados. Críticos temem o aumento de tarifas, enquanto defensores veem a medida como a única forma de acelerar o investimento necessário.'"
        ]
    },
    {
        "id": 42,
        "titulo": "A influência da publicidade infantil no consumismo",
        "enunciado": "Redija uma dissertação sobre 'A influência da publicidade infantil no consumismo e os desafios de sua regulação'.",
        "textos_base": [
            "Texto 1: 'A publicidade direcionada à criança utiliza recursos lúdicos (personagens, cores, trilhas sonoras) para criar um vínculo afetivo com o produto. A criança, por não ter senso crítico desenvolvido, não diferencia entretenimento de persuasão.' (Fonte: Instituto Alana)",
            "Texto 2: 'O Conselho Nacional dos Direitos da Criança e do Adolescente (CONANDA) considera abusiva a publicidade infantil. No entanto, não há uma lei federal clara, apenas a autorregulamentação do setor (CONAR), que é considerada branda.'",
            "Texto 3: 'A exposição excessiva à publicidade está ligada ao aumento da obesidade infantil (anúncios de ultraprocessados), estresse familiar (criança pedindo produtos) e erotização precoce. (Fonte: Sociedade Brasileira de Pediatria)'"
        ]
    },
    {
        "id": 43,
        "titulo": "Caminhos para combater o racismo estrutural no Brasil",
        "enunciado": "Elabore um texto dissertativo-argumentativo sobre 'Caminhos para combater o racismo estrutural no Brasil', analisando como o preconceito se manifesta e propondo ações.",
        "textos_base": [
            "Texto 1: 'O racismo estrutural é a formalização de práticas discriminatórias que se manifestam nas instituições, na cultura e nas relações sociais, colocando a população negra em desvantagem. Não é apenas um ato individual, mas um sistema de opressão.' (Silvio Almeida, 'Racismo Estrutural')",
            "Texto 2: 'Pessoas negras têm salários menores, menor acesso a cargos de liderança, maior taxa de desemprego e são as maiores vítimas de violência policial, mesmo sendo a maioria da população. Isso evidencia a estrutura.' (Fonte: IBGE/PNAD)",
            "Texto 3: 'O combate exige mais do que a criminalização do ato racista. Exige políticas afirmativas, como as cotas raciais em universidades e concursos, para corrigir desigualdades históricas e garantir a representatividade em espaços de poder.'"
        ]
    },
    {
        "id": 44,
        "titulo": "O estigma associado às doenças mentais na sociedade brasileira",
        "enunciado": "Redija uma dissertação sobre 'O estigma associado às doenças mentais na sociedade brasileira e a necessidade de ampliar o debate sobre saúde mental'.",
        "textos_base": [
            "Texto 1: 'A psicofobia (preconceito contra pessoas com transtornos mentais) é uma barreira significativa para o tratamento. O estigma faz com que o indivíduo tenha vergonha de buscar ajuda, por medo de ser rotulado como 'louco', 'fraco' ou 'preguiçoso'.'",
            "Texto 2: 'Transtornos como depressão e ansiedade são problemas de saúde reais, com causas biológicas e sociais, e não 'falta de Deus' ou 'falta do que fazer'. O Brasil é considerado o país mais ansioso do mundo pela OMS.' (Fonte: OMS)",
            "Texto 3: 'A Reforma Psiquiátrica (Lei 10.216/2001) buscou substituir o modelo de internação (manicômios) pelo atendimento comunitário (CAPS - Centros de Atenção Psicossocial), mas a rede ainda é insuficiente para a demanda nacional.'"
        ]
    },
    {
        "id": 45,
        "titulo": "Violência urbana e a falha das políticas de segurança pública",
        "enunciado": "Redija um texto dissertativo-argumentativo sobre 'Violência urbana e a falha das políticas de segurança pública no Brasil', discutindo o modelo de 'guerra às drogas'.",
        "textos_base": [
            "Texto 1: 'O Brasil, embora não esteja em guerra declarada, possui taxas de homicídio superiores às de muitos países em conflito armado. A maioria das vítimas é jovem, negra e moradora de periferias.' (Fonte: Fórum Brasileiro de Segurança Pública)",
            "Texto 2: 'A política de 'Guerra às Drogas', focada no confronto policial ostensivo em territórios de varejo, tem se mostrado ineficaz em reduzir o poder do tráfico, mas altamente letal para a população civil e para os próprios policiais, enxugando gelo com sangue.'",
            "Texto 3: 'Especialistas em segurança defendem a mudança do foco do confronto para a inteligência: investigação financeira para desarticular os 'barões' do tráfico, e não o confronto com o 'soldado' na favela. Além de investir em prevenção social (educação e emprego) nas áreas vulneráveis.'"
        ]
    }
]


@app.route('/api/redacao/temas-melhorados')
def get_temas_melhorados():
    return jsonify({"success": True, "temas": TEMAS_REDACAO_MELHORADOS})

def gerar_correcao_simulada():
    '''(NOVO) Correção simulada quando Gemini não está disponível'''
    nota = random.randint(500, 900)
    return {
        "nota_final": nota,
        "competencias": [
            {"nome": "Domínio da norma padrão", "nota": round(nota * 0.2), "comentario": "(Simulado) Bom domínio da norma culta com poucos desvios."},
            {"nome": "Compreensão do tema", "nota": round(nota * 0.2), "comentario": "(Simulado) Tema compreendido adequadamente dentro dos limites."},
            {"nome": "Argumentação", "nota": round(nota * 0.2), "comentario": "(Simulado) Argumentos consistentes e bem fundamentados."},
            {"nome": "Coesão textual", "nota": round(nota * 0.2), "comentario": "(Simulado) Texto coeso com boa progressão argumentativa."},
            {"nome": "Proposta de intervenção", "nota": round(nota * 0.2), "comentario": "(Simulado) Proposta concreta, detalhada e respeitando direitos humanos."}
        ],
        "pontos_fortes": ["(Simulado) Estrutura organizada", "Argumentação clara", "Proposta viável"],
        "pontos_fracos": ["(Simulado) Poderia usar mais exemplos concretos", "Repertório sociocultural pode ser ampliado"],
        "sugestoes_melhoria": ["(Simulado) Ampliar o repertório de citações", "Desenvolver mais os exemplos práticos"]
    }

@app.route('/api/redacao/corrigir-gemini-real', methods=['POST'])
def corrigir_redacao_gemini_real():
    try:
        data = request.json
        tema = data.get('tema')
        texto = data.get('texto')
        enunciado = data.get('enunciado')
        
        if not tema or not texto:
            return jsonify({"success": False, "error": "Tema e texto são obrigatórios"}), 400
        
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        
        # (NOVO) Verifica se a chave existe e não é a placeholder
        if GEMINI_API_KEY and GEMINI_API_KEY != 'sua_chave_gemini_aqui':
            genai.configure(api_key=GEMINI_API_KEY)
            
            prompt = f'''
            Aja como um corretor de redação do ENEM. Seja rigoroso e técnico.
            Corrija esta redação com base nos critérios do ENEM.

            TEMA: {tema}
            ENUNCIADO (Contexto): {enunciado}
            
            REDAÇÃO DO ALUNO:
            ---
            {texto}
            ---

            AVALIE CADA UMA DAS 5 COMPETÊNCIAS DO ENEM, atribuindo uma nota de 0 a 200 para cada uma.
            1. Domínio da norma padrão (Gramática, ortografia, pontuação).
            2. Compreensão do tema e estrutura dissertativo-argumentativa (Não fugir do tema, tese clara, introdução, desenvolvimento, conclusão).
            3. Argumentação e repertório (Defesa do ponto de vista com argumentos sólidos, fatos, citações, dados).
            4. Coesão textual (Uso correto de conectivos, parágrafos bem estruturados).
            5. Proposta de intervenção (Proposta detalhada com Agente, Ação, Modo/Meio, Efeito e Detalhamento).

            RETORNE ESTRITAMENTE UM OBJETO JSON, sem nenhum texto antes ou depois. O JSON deve ter o seguinte formato:
            {{
                "nota_final": 0-1000 (soma das 5 competências),
                "competencias": [
                    {{"nome": "Competência 1: Domínio da norma padrão", "nota": 0-200, "comentario": "Seu comentário técnico sobre esta competência."}},
                    {{"nome": "Competência 2: Compreensão do tema", "nota": 0-200, "comentario": "Seu comentário técnico sobre esta competência."}},
                    {{"nome": "Competência 3: Argumentação e repertório", "nota": 0-200, "comentario": "Seu comentário técnico sobre esta competência."}},
                    {{"nome": "Competência 4: Coesão textual", "nota": 0-200, "comentario": "Seu comentário técnico sobre esta competência."}},
                    {{"nome": "Competência 5: Proposta de intervenção", "nota": 0-200, "comentario": "Seu comentário técnico sobre esta competência."}}
                ],
                "pontos_fortes": ["Liste 3 pontos fortes principais em formato de string"],
                "pontos_fracos": ["Liste 3 pontos fracos principais em formato de string"],
                "sugestoes_melhoria": ["Liste 3 sugestões de melhoria práticas em formato de string"]
            }}
            '''
            
            # --- (CORREÇÃO 1) Modelo do Gemini ---
            # O modelo 'gemini-1.5-pro-latest' falhou no log. Mudando para o '1.0-pro'.
            model = genai.GenerativeModel('gemini-1.0-pro')
            # --- FIM DA CORREÇÃO 1 ---

            response = model.generate_content(prompt)
            
            # Limpa a resposta do Gemini para garantir que é um JSON
            json_text = response.text.strip().replace('```json', '').replace('```', '')
            
            try:
                correcao = json.loads(json_text)
            except json.JSONDecodeError:
                print("Erro ao decodificar JSON do Gemini. Usando mock.")
                correcao = gerar_correcao_simulada()
        else:
            print("Chave Gemini não configurada. Usando mock.")
            correcao = gerar_correcao_simulada()
        
        return jsonify({"success": True, "correcao": correcao})
        
    except Exception as e:
        print(f"ERRO 500 em /corrigir-gemini-real: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---
# --- ROTAS ANTIGAS (MANTIDAS APENAS SE NECESSÁRIO, MAS SUBSTITUÍDAS) ---
# ---
@app.route('/api/redacao/temas')
def get_temas_redacao_antigo():
    # Esta rota foi substituída por /api/redacao/temas-melhorados
    return get_temas_melhorados()

@app.route('/api/redacao/corrigir-gemini', methods=['POST'])
def corrigir_gemini_antigo():
    # Esta rota foi substituída por /api/redacao/corrigir-gemini-real
    return corrigir_redacao_gemini_real()
    
@app.route('/api/dashboard/estatisticas-areas')
def get_estatisticas_areas_antigo():
    # Esta rota foi substituída por /api/dashboard/simplificado
    return get_dashboard_simplificado()

# --- FIM DO ARQUIVO ---
if __name__ == '__main__':
    # (NOVO) O app.run() agora só é usado para testes locais
    # O Gunicorn (servidor de produção) será usado pelo Render
    app.run(debug=True)