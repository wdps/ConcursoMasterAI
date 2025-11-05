import sqlite3
import os

def setup_database():
    conn = sqlite3.connect('./data/concursoia.db')
    cursor = conn.cursor()
    
    # Tabela de resultados de simulados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resultados_simulados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            data_realizacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_questoes INTEGER,
            total_acertos INTEGER,
            percentual_acerto REAL,
            areas_selecionadas TEXT,
            tempo_gasto INTEGER
        )
    ''')
    
    # Tabela de desempenho por área
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS desempenho_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            area TEXT,
            total_questoes INTEGER,
            total_acertos INTEGER,
            percentual_acerto REAL,
            ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de metas do usuário
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metas_usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            tipo_meta TEXT,
            valor_meta REAL,
            valor_atual REAL,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_conclusao DATETIME NULL,
            concluida BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Tabela de redações corrigidas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS redacoes_corrigidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            tema TEXT,
            texto_redacao TEXT,
            nota_final INTEGER,
            competencia1 INTEGER,
            competencia2 INTEGER,
            competencia3 INTEGER,
            competencia4 INTEGER,
            competencia5 INTEGER,
            feedback TEXT,
            data_correcao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado com sucesso!")

if __name__ == "__main__":
    setup_database()
