# Arquivo: logica_banco.py
import sqlite3
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseManager:
    # ... (Sua classe DatabaseManager continua exatamente a mesma, sem alterações) ...
    """Gerencia a conexão e as operações básicas do banco de dados."""
    def __init__(self, db_name="loja.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        # Permite acessar resultados por nome de coluna
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def disconnect(self):
        if self.conn:
            self.conn.close()

    def execute_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor
        except sqlite3.Error as e:
            print(f"Erro ao executar a query: {e}")
            self.conn.rollback()
            return None

    def fetch_all(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao buscar dados: {e}")
            return []

    def fetch_one(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Erro ao buscar dado: {e}")
            return None

def setup_database():
    db = DatabaseManager()
    db.connect()
    # Tabela de Produtos
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, preco REAL NOT NULL,
        quantidade INTEGER NOT NULL, codigo_barras TEXT UNIQUE ); """)
    # Tabela de Clientes
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, telefone TEXT, email TEXT ); """)
    # Tabela de Vendas
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, data_venda TEXT NOT NULL,
        total REAL NOT NULL, FOREIGN KEY (cliente_id) REFERENCES clientes (id) ); """)
    # Tabela de Itens da Venda
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS itens_venda (
        id INTEGER PRIMARY KEY AUTOINCREMENT, venda_id INTEGER NOT NULL, produto_id INTEGER NOT NULL,
        quantidade INTEGER NOT NULL, preco_unitario REAL NOT NULL,
        FOREIGN KEY (venda_id) REFERENCES vendas (id), FOREIGN KEY (produto_id) REFERENCES produtos (id) ); """)
    # Tabela de Histórico de Estoque
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS historico_estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER NOT NULL, tipo_movimento TEXT NOT NULL,
        quantidade INTEGER NOT NULL, data_movimento TEXT NOT NULL,
        FOREIGN KEY (produto_id) REFERENCES produtos (id) ); """)
    # Tabela de Usuários (para autenticação) -- MOVA PARA ANTES DO disconnect
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    );
    """)
    db.disconnect()

# --- Funções de PRODUTOS ---
def adicionar_produto(nome, preco, quantidade, codigo_barras=None):
    db = DatabaseManager()
    db.connect()
    cursor = db.execute_query("INSERT INTO produtos (nome, preco, quantidade, codigo_barras) VALUES (?, ?, ?, ?)", (nome, preco, quantidade, codigo_barras))
    produto_id = cursor.lastrowid
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db.execute_query("INSERT INTO historico_estoque (produto_id, tipo_movimento, quantidade, data_movimento) VALUES (?, 'entrada', ?, ?)", (produto_id, quantidade, data_atual))
    db.disconnect()

def listar_produtos():
    db = DatabaseManager()
    db.connect()
    produtos = db.fetch_all("SELECT * FROM produtos ORDER BY nome")
    db.disconnect()
    return produtos

def buscar_produto_por_id(id):
    db = DatabaseManager()
    db.connect()
    produto = db.fetch_one("SELECT * FROM produtos WHERE id = ?", (id,))
    db.disconnect()
    return produto

def buscar_produto_por_codigo(codigo):
    db = DatabaseManager()
    db.connect()
    produto = db.fetch_one(
        "SELECT * FROM produtos WHERE codigo_barras = ? OR nome LIKE ?",
        (codigo, f'%{codigo}%')
    )
    db.disconnect()
    return produto

def atualizar_produto(id, nome, preco, quantidade, codigo_barras):
    db = DatabaseManager()
    db.connect()
    db.execute_query("UPDATE produtos SET nome = ?, preco = ?, quantidade = ?, codigo_barras = ? WHERE id = ?", (nome, preco, quantidade, codigo_barras, id))
    db.disconnect()

def excluir_produto(id):
    db = DatabaseManager()
    db.connect()
    db.execute_query("DELETE FROM produtos WHERE id = ?", (id,))
    db.disconnect()

# --- Funções de CLIENTES ---
def adicionar_cliente(nome, telefone, email):
    db = DatabaseManager()
    db.connect()
    db.execute_query("INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)", (nome, telefone, email))
    db.disconnect()

def listar_clientes():
    db = DatabaseManager()
    db.connect()
    clientes = db.fetch_all("SELECT * FROM clientes ORDER BY nome")
    db.disconnect()
    return clientes

def buscar_cliente_por_id(id):
    db = DatabaseManager()
    db.connect()
    cliente = db.fetch_one("SELECT * FROM clientes WHERE id = ?", (id,))
    db.disconnect()
    return cliente

def atualizar_cliente(id, nome, telefone, email):
    db = DatabaseManager()
    db.connect()
    db.execute_query("UPDATE clientes SET nome = ?, telefone = ?, email = ? WHERE id = ?", (nome, telefone, email, id))
    db.disconnect()

def excluir_cliente(id):
    db = DatabaseManager()
    db.connect()
    db.execute_query("DELETE FROM clientes WHERE id = ?", (id,))
    db.disconnect()

# --- Funções de VENDAS ---
def registrar_venda(cliente_id, itens_carrinho, total):
    db = DatabaseManager()
    db.connect()
    try:
        data_venda = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = db.execute_query("INSERT INTO vendas (cliente_id, data_venda, total) VALUES (?, ?, ?)", (cliente_id, data_venda, total))
        venda_id = cursor.lastrowid

        for item in itens_carrinho:
            produto = buscar_produto_por_id(item['id'])
            db.execute_query("INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)", (venda_id, item['id'], item['qtd'], produto['preco']))
            nova_quantidade = produto['quantidade'] - item['qtd']
            db.execute_query("UPDATE produtos SET quantidade = ? WHERE id = ?", (nova_quantidade, item['id']))
    except Exception as e:
        print(f"Erro ao registrar venda: {e}")
    finally:
        db.disconnect()

    return venda_id

def registrar_venda_completa(cliente_id, itens_carrinho, total, forma_pagamento, valor_pago, troco):
    """
    Registra uma venda completa com detalhes de pagamento e atualiza o estoque.
    """
    db = DatabaseManager()
    db.connect()
    try:
        data_venda = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor = db.execute_query(
            "INSERT INTO vendas (cliente_id, data_venda, total, forma_pagamento, valor_pago, troco) VALUES (?, ?, ?, ?, ?, ?)",
            (cliente_id, data_venda, total, forma_pagamento, valor_pago, troco)
        )
        venda_id = cursor.lastrowid

        for item in itens_carrinho:
            produto = buscar_produto_por_id(item['id'])
            db.execute_query(
                "INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (venda_id, item['id'], item['qtd'], produto['preco'])
            )
            
            nova_quantidade = produto['quantidade'] - item['qtd']
            db.execute_query(
                "UPDATE produtos SET quantidade = ? WHERE id = ?",
                (nova_quantidade, item['id'])
            )
        
        db.conn.commit()
    except Exception as e:
        db.conn.rollback()
        print(f"Erro ao registrar venda completa: {e}")
    finally:
        db.disconnect()        

# --- Funções de RELATÓRIOS ---
def get_relatorio_vendas_detalhado():
    db = DatabaseManager()
    db.connect()
    query = """
        SELECT v.id, v.data_venda, v.total, c.nome as cliente_nome,
               GROUP_CONCAT(p.nome || ' (x' || iv.quantidade || ')', '; ') as produtos
        FROM vendas v
        LEFT JOIN clientes c ON v.cliente_id = c.id
        JOIN itens_venda iv ON v.id = iv.venda_id
        JOIN produtos p ON iv.produto_id = p.id
        GROUP BY v.id
        ORDER BY v.data_venda DESC
    """
    vendas = db.fetch_all(query)
    db.disconnect()
    return vendas

def get_relatorio_estoque():
    return listar_produtos() # A função já existe e faz o que precisamos

def get_relatorio_movimentacao_estoque():
    db = DatabaseManager()
    db.connect()
    query = """
        SELECT h.id, p.nome, h.tipo_movimento, h.quantidade, h.data_movimento
        FROM historico_estoque h
        JOIN produtos p ON h.produto_id = p.id
        ORDER BY h.data_movimento DESC
    """
    movimentos = db.fetch_all(query)
    db.disconnect()
    return movimentos

def add_user(username, password):
    db = DatabaseManager()
    db.connect()
    password_hash = generate_password_hash(password)
    db.execute_query(
        "INSERT INTO usuarios (username, password_hash) VALUES (?, ?)",
        (username, password_hash)
    )
    db.disconnect()

def get_user_by_username(username):
    db = DatabaseManager()
    db.connect()
    user_data = db.fetch_one("SELECT * FROM usuarios WHERE username = ?", (username,))
    db.disconnect()
    return user_data