# Arquivo: logica_banco.py
import sqlite3
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --- CLASSE DE BANCO DE DADOS ---
class DatabaseManager:
    """Gerencia a conexão e as operações básicas do banco de dados."""
    def __init__(self, db_name="loja.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row # Permite acessar resultados por nome da coluna
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

# --- SETUP DO BANCO DE DADOS ---
def setup_database():
    """Cria todas as tabelas necessárias se elas não existirem."""
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
        total REAL NOT NULL, forma_pagamento TEXT, valor_pago REAL, troco REAL,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ); """)
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
    # Tabela de Usuários
    db.execute_query("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL ); """)
    db.disconnect()

# --- MODELO DE DADOS (LOGIN) ---
class User(UserMixin):
    """Classe de modelo para o usuário, compatível com Flask-Login."""
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

# --- FUNÇÕES DE USUÁRIOS (LOGIN) ---
def add_user(username, password):
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    db = DatabaseManager()
    db.connect()
    db.execute_query("INSERT INTO usuarios (username, password_hash) VALUES (?, ?)", (username, password_hash))
    db.disconnect()

def get_user_by_id(user_id):
    db = DatabaseManager()
    db.connect()
    user_data = db.fetch_one("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    db.disconnect()
    if user_data:
        # Retorna um OBJETO User, como o Flask-Login espera
        return User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
    return None

def get_user_by_username(username):
    db = DatabaseManager()
    db.connect()
    user_data = db.fetch_one("SELECT * FROM usuarios WHERE username = ?", (username,))
    db.disconnect()
    if user_data:
        # Retorna um OBJETO User, como o Flask-Login espera
        return User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
    return None

# --- FUNÇÕES DE PRODUTOS ---
def listar_produtos():
    db = DatabaseManager()
    db.connect()
    produtos = db.fetch_all("SELECT * FROM produtos ORDER BY nome")
    db.disconnect()
    return produtos
# ... (e todas as outras funções de produto: adicionar, buscar, atualizar, excluir) ...
def adicionar_produto(nome, preco, quantidade, codigo_barras=None):
    db = DatabaseManager(); db.connect()
    cursor = db.execute_query("INSERT INTO produtos (nome, preco, quantidade, codigo_barras) VALUES (?, ?, ?, ?)", (nome, preco, quantidade, codigo_barras))
    produto_id = cursor.lastrowid
    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db.execute_query("INSERT INTO historico_estoque (produto_id, tipo_movimento, quantidade, data_movimento) VALUES (?, 'entrada', ?, ?)", (produto_id, quantidade, data_atual))
    db.disconnect()
def buscar_produto_por_id(id):
    db = DatabaseManager(); db.connect()
    produto = db.fetch_one("SELECT * FROM produtos WHERE id = ?", (id,)); db.disconnect(); return produto
def buscar_produto_por_codigo(codigo):
    db = DatabaseManager(); db.connect()
    produto = db.fetch_one("SELECT * FROM produtos WHERE codigo_barras = ? OR nome LIKE ?", (codigo, f'%{codigo}%')); db.disconnect(); return produto
def atualizar_produto(id, nome, preco, quantidade, codigo_barras):
    db = DatabaseManager(); db.connect()
    db.execute_query("UPDATE produtos SET nome = ?, preco = ?, quantidade = ?, codigo_barras = ? WHERE id = ?", (nome, preco, quantidade, codigo_barras, id)); db.disconnect()
def excluir_produto(id):
    db = DatabaseManager(); db.connect()
    db.execute_query("DELETE FROM produtos WHERE id = ?", (id,)); db.disconnect()

# --- FUNÇÕES DE CLIENTES ---
def listar_clientes():
    db = DatabaseManager()
    db.connect()
    clientes = db.fetch_all("SELECT * FROM clientes ORDER BY nome")
    db.disconnect()
    return clientes
# ... (e todas as outras funções de cliente: adicionar, buscar, atualizar, excluir) ...
def adicionar_cliente(nome, telefone, email):
    db = DatabaseManager(); db.connect()
    db.execute_query("INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)", (nome, telefone, email)); db.disconnect()
def buscar_cliente_por_id(id):
    db = DatabaseManager(); db.connect()
    cliente = db.fetch_one("SELECT * FROM clientes WHERE id = ?", (id,)); db.disconnect(); return cliente
def atualizar_cliente(id, nome, telefone, email):
    db = DatabaseManager(); db.connect()
    db.execute_query("UPDATE clientes SET nome = ?, telefone = ?, email = ? WHERE id = ?", (nome, telefone, email, id)); db.disconnect()
def excluir_cliente(id):
    db = DatabaseManager(); db.connect()
    db.execute_query("DELETE FROM clientes WHERE id = ?", (id,)); db.disconnect()

# --- FUNÇÕES DE VENDAS ---
def registrar_venda_completa(cliente_id, itens_carrinho, total, forma_pagamento, valor_pago, troco):
    db = DatabaseManager()
    db.connect()
    venda_id = None
    try:
        data_venda = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = db.execute_query("INSERT INTO vendas (cliente_id, data_venda, total, forma_pagamento, valor_pago, troco) VALUES (?, ?, ?, ?, ?, ?)", (cliente_id, data_venda, total, forma_pagamento, valor_pago, troco))
        venda_id = cursor.lastrowid
        for item in itens_carrinho:
            produto = buscar_produto_por_id(item['id'])
            db.execute_query("INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)", (venda_id, item['id'], item['qtd'], produto['preco']))
            nova_quantidade = produto['quantidade'] - item['qtd']
            db.execute_query("UPDATE produtos SET quantidade = ? WHERE id = ?", (nova_quantidade, item['id']))
        db.conn.commit()
    except Exception as e:
        db.conn.rollback()
        print(f"Erro ao registrar venda completa: {e}")
    finally:
        db.disconnect()
    return venda_id

# --- FUNÇÕES DE RELATÓRIOS ---
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
        GROUP BY v.id ORDER BY v.data_venda DESC """
    vendas = db.fetch_all(query)
    db.disconnect()
    return vendas

def get_relatorio_estoque():
    return listar_produtos()

def get_relatorio_movimentacao_estoque():
    db = DatabaseManager()
    db.connect()
    query = """
        SELECT h.id, p.nome, h.tipo_movimento, h.quantidade, h.data_movimento
        FROM historico_estoque h JOIN produtos p ON h.produto_id = p.id
        ORDER BY h.data_movimento DESC """
    movimentos = db.fetch_all(query)
    db.disconnect()
    return movimentos