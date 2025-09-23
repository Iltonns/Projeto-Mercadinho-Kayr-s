# Arquivo: logica_banco.py
import sqlite3
import re
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --- VALIDAÇÕES E SEGURANÇA ---
def validar_email(email):
    """Valida formato de email"""
    if not email:
        return True  # Email opcional
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validar_senha(senha):
    """Valida força da senha"""
    if len(senha) < 6:
        return False, "Senha deve ter pelo menos 6 caracteres"
    return True, ""

def sanitizar_input(texto):
    """Remove caracteres perigosos e espaços extras"""
    if not texto:
        return ""
    # Remove tags HTML e espaços extras
    texto = re.sub(r'<[^>]*>', '', texto)
    texto = texto.strip()
    return texto

def validar_preco(preco):
    """Valida formato de preço"""
    try:
        preco_float = float(preco)
        return preco_float > 0, preco_float
    except (ValueError, TypeError):
        return False, None

def validar_quantidade(quantidade):
    """Valida quantidade"""
    try:
        qtd_int = int(quantidade)
        return qtd_int >= 0, qtd_int
    except (ValueError, TypeError):
        return False, None

# --- CLASSE DE BANCO DE DADOS MELHORADA ---
class DatabaseManager:
    """Gerencia a conexão e as operações básicas do banco de dados com tratamento de erros."""
    
    def __init__(self, db_name="loja.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        """Estabelece conexão com o banco"""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.conn.row_factory = sqlite3.Row  # Permite acessar resultados por nome da coluna
            self.cursor = self.conn.cursor()
            return True
        except sqlite3.Error as e:
            print(f"❌ Erro ao conectar com o banco: {e}")
            return False

    def disconnect(self):
        """Fecha conexão com o banco"""
        if self.conn:
            self.conn.close()

    def execute_query(self, query, params=()):
        """Executa query com tratamento de erro"""
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor
        except sqlite3.Error as e:
            print(f"❌ Erro ao executar query: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            if self.conn:
                self.conn.rollback()
            return None

    def fetch_all(self, query, params=()):
        """Busca todos os resultados com tratamento de erro"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"❌ Erro ao buscar dados: {e}")
            return []

    def fetch_one(self, query, params=()):
        """Busca um resultado com tratamento de erro"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            print(f"❌ Erro ao buscar dado: {e}")
            return None

# --- SETUP DO BANCO DE DADOS MELHORADO ---
def setup_database():
    """Cria todas as tabelas necessárias se elas não existirem."""
    db = DatabaseManager()
    
    if not db.connect():
        print("❌ Falha ao conectar com o banco durante setup")
        return False
    
    try:
        # Tabela de Produtos
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome TEXT NOT NULL, 
            preco REAL NOT NULL CHECK(preco > 0),
            quantidade INTEGER NOT NULL CHECK(quantidade >= 0), 
            codigo_barras TEXT UNIQUE,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Tabela de Clientes
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome TEXT NOT NULL, 
            telefone TEXT, 
            email TEXT CHECK(email LIKE '%@%' OR email IS NULL)
        )""")
        
        # Tabela de Vendas
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            cliente_id INTEGER, 
            data_venda TEXT NOT NULL,
            total REAL NOT NULL CHECK(total >= 0), 
            forma_pagamento TEXT, 
            valor_pago REAL CHECK(valor_pago >= 0),
            troco REAL CHECK(troco >= 0),
            FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE SET NULL
        )""")
        
        # Tabela de Itens da Venda
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS itens_venda (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            venda_id INTEGER NOT NULL, 
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL CHECK(quantidade > 0), 
            preco_unitario REAL NOT NULL CHECK(preco_unitario > 0),
            FOREIGN KEY (venda_id) REFERENCES vendas (id) ON DELETE CASCADE,
            FOREIGN KEY (produto_id) REFERENCES produtos (id) ON DELETE RESTRICT
        )""")
        
        # Tabela de Histórico de Estoque
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS historico_estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            produto_id INTEGER NOT NULL, 
            tipo_movimento TEXT NOT NULL CHECK(tipo_movimento IN ('entrada', 'saida')),
            quantidade INTEGER NOT NULL CHECK(quantidade > 0), 
            data_movimento TEXT NOT NULL,
            FOREIGN KEY (produto_id) REFERENCES produtos (id) ON DELETE CASCADE
        )""")
        
        # Tabela de Usuários
        db.execute_query("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE CHECK(length(username) >= 3),
            password_hash TEXT NOT NULL,
            data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        
        print("✅ Banco de dados configurado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante setup do banco: {e}")
        return False
    finally:
        db.disconnect()

# --- MODELO DE DADOS (LOGIN) ---
class User(UserMixin):
    """Classe de modelo para o usuário, compatível com Flask-Login."""
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
    
    def verify_password(self, password):
        """Verifica se a senha está correta"""
        return check_password_hash(self.password_hash, password)

# --- FUNÇÕES DE USUÁRIOS (LOGIN) MELHORADAS ---
def add_user(username, password):
    """Adiciona usuário com validações"""
    username = sanitizar_input(username)
    
    if not username or len(username) < 3:
        return False, "Nome de usuário deve ter pelo menos 3 caracteres"
    
    senha_valida, msg_erro = validar_senha(password)
    if not senha_valida:
        return False, msg_erro
    
    # Verificar se usuário já existe
    if get_user_by_username(username):
        return False, "Nome de usuário já existe"
    
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    db = DatabaseManager()
    
    if not db.connect():
        return False, "Erro de conexão com o banco"
    
    try:
        cursor = db.execute_query(
            "INSERT INTO usuarios (username, password_hash) VALUES (?, ?)", 
            (username, password_hash)
        )
        
        if cursor:
            return True, "Usuário criado com sucesso"
        else:
            return False, "Erro ao criar usuário"
            
    except Exception as e:
        return False, f"Erro ao criar usuário: {str(e)}"
    finally:
        db.disconnect()

def get_user_by_id(user_id):
    """Busca usuário por ID"""
    db = DatabaseManager()
    
    if not db.connect():
        return None
        
    user_data = db.fetch_one("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    db.disconnect()
    
    if user_data:
        return User(
            id=user_data['id'], 
            username=user_data['username'], 
            password_hash=user_data['password_hash']
        )
    return None

def get_user_by_username(username):
    """Busca usuário por username"""
    db = DatabaseManager()
    
    if not db.connect():
        return None
        
    user_data = db.fetch_one("SELECT * FROM usuarios WHERE username = ?", (username,))
    db.disconnect()
    
    if user_data:
        return User(
            id=user_data['id'], 
            username=user_data['username'], 
            password_hash=user_data['password_hash']
        )
    return None

# --- FUNÇÕES DE PRODUTOS MELHORADAS ---
def listar_produtos():
    """Lista todos os produtos com tratamento de erro"""
    db = DatabaseManager()
    
    if not db.connect():
        return []
        
    produtos = db.fetch_all("SELECT * FROM produtos ORDER BY nome")
    db.disconnect()
    return produtos

def adicionar_produto(nome, preco, quantidade, codigo_barras=None):
    """Adiciona produto com validações"""
    nome = sanitizar_input(nome)
    codigo_barras = sanitizar_input(codigo_barras) if codigo_barras else None
    
    if not nome or len(nome) < 2:
        return False, "Nome do produto deve ter pelo menos 2 caracteres"
    
    preco_valido, preco_float = validar_preco(preco)
    if not preco_valido:
        return False, "Preço inválido"
    
    qtd_valida, qtd_int = validar_quantidade(quantidade)
    if not qtd_valida:
        return False, "Quantidade inválida"
    
    db = DatabaseManager()
    
    if not db.connect():
        return False, "Erro de conexão com o banco"
    
    try:
        # Verificar se código de barras já existe
        if codigo_barras:
            existente = db.fetch_one(
                "SELECT id FROM produtos WHERE codigo_barras = ?", 
                (codigo_barras,)
            )
            if existente:
                return False, "Código de barras já existe"
        
        cursor = db.execute_query(
            "INSERT INTO produtos (nome, preco, quantidade, codigo_barras) VALUES (?, ?, ?, ?)", 
            (nome, preco_float, qtd_int, codigo_barras)
        )
        
        if cursor:
            produto_id = cursor.lastrowid
            data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Registrar no histórico
            db.execute_query(
                "INSERT INTO historico_estoque (produto_id, tipo_movimento, quantidade, data_movimento) VALUES (?, 'entrada', ?, ?)", 
                (produto_id, qtd_int, data_atual)
            )
            
            return True, "Produto adicionado com sucesso"
        else:
            return False, "Erro ao adicionar produto"
            
    except Exception as e:
        return False, f"Erro ao adicionar produto: {str(e)}"
    finally:
        db.disconnect()

def buscar_produto_por_id(id):
    """Busca produto por ID"""
    db = DatabaseManager()
    
    if not db.connect():
        return None
        
    produto = db.fetch_one("SELECT * FROM produtos WHERE id = ?", (id,))
    db.disconnect()
    return produto

def buscar_produto_por_codigo(codigo):
    """Busca produto por código ou nome"""
    codigo = sanitizar_input(codigo)
    db = DatabaseManager()
    
    if not db.connect():
        return None
        
    produto = db.fetch_one(
        "SELECT * FROM produtos WHERE LOWER(codigo_barras) = LOWER(?) OR LOWER(nome) LIKE LOWER(?)", 
        (codigo, f'%{codigo}%')
    )
    db.disconnect()
    return produto

def atualizar_produto(id, nome, preco, quantidade, codigo_barras=None):
    """Atualiza produto com validações"""
    nome = sanitizar_input(nome)
    codigo_barras = sanitizar_input(codigo_barras) if codigo_barras else None
    
    if not nome or len(nome) < 2:
        return False, "Nome do produto deve ter pelo menos 2 caracteres"
    
    preco_valido, preco_float = validar_preco(preco)
    if not preco_valido:
        return False, "Preço inválido"
    
    qtd_valida, qtd_int = validar_quantidade(quantidade)
    if not qtd_valida:
        return False, "Quantidade inválida"
    
    db = DatabaseManager()
    
    if not db.connect():
        return False, "Erro de conexão com o banco"
    
    try:
        # Verificar se código de barras já existe em outro produto
        if codigo_barras:
            existente = db.fetch_one(
                "SELECT id FROM produtos WHERE codigo_barras = ? AND id != ?", 
                (codigo_barras, id)
            )
            if existente:
                return False, "Código de barras já existe em outro produto"
        
        cursor = db.execute_query(
            "UPDATE produtos SET nome = ?, preco = ?, quantidade = ?, codigo_barras = ?, data_atualizacao = CURRENT_TIMESTAMP WHERE id = ?", 
            (nome, preco_float, qtd_int, codigo_barras, id)
        )
        
        if cursor:
            return True, "Produto atualizado com sucesso"
        else:
            return False, "Erro ao atualizar produto"
            
    except Exception as e:
        return False, f"Erro ao atualizar produto: {str(e)}"
    finally:
        db.disconnect()

def excluir_produto(id):
    """Exclui produto com tratamento de erro"""
    db = DatabaseManager()
    
    if not db.connect():
        return False, "Erro de conexão com o banco"
    
    try:
        # Verificar se produto existe
        produto = db.fetch_one("SELECT id FROM produtos WHERE id = ?", (id,))
        if not produto:
            return False, "Produto não encontrado"
        
        cursor = db.execute_query("DELETE FROM produtos WHERE id = ?", (id,))
        
        if cursor:
            return True, "Produto excluído com sucesso"
        else:
            return False, "Erro ao excluir produto"
            
    except Exception as e:
        return False, f"Erro ao excluir produto: {str(e)}"
    finally:
        db.disconnect()

# --- FUNÇÕES DE CLIENTES MELHORADAS ---
def listar_clientes():
    """Lista todos os clientes"""
    db = DatabaseManager()
    
    if not db.connect():
        return []
        
    clientes = db.fetch_all("SELECT * FROM clientes ORDER BY nome")
    db.disconnect()
    return clientes

def adicionar_cliente(nome, telefone, email):
    """Adiciona cliente com validações"""
    nome = sanitizar_input(nome)
    telefone = sanitizar_input(telefone) if telefone else None
    email = sanitizar_input(email) if email else None
    
    if not nome or len(nome) < 2:
        return False, "Nome do cliente deve ter pelo menos 2 caracteres"
    
    if email and not validar_email(email):
        return False, "Email inválido"
    
    db = DatabaseManager()
    
    if not db.connect():
        return False, "Erro de conexão com o banco"
    
    try:
        cursor = db.execute_query(
            "INSERT INTO clientes (nome, telefone, email) VALUES (?, ?, ?)", 
            (nome, telefone, email)
        )
        
        if cursor:
            return True, "Cliente adicionado com sucesso"
        else:
            return False, "Erro ao adicionar cliente"
            
    except Exception as e:
        return False, f"Erro ao adicionar cliente: {str(e)}"
    finally:
        db.disconnect()

def buscar_cliente_por_id(id):
    """Busca cliente por ID"""
    db = DatabaseManager()
    
    if not db.connect():
        return None
        
    cliente = db.fetch_one("SELECT * FROM clientes WHERE id = ?", (id,))
    db.disconnect()
    return cliente

def atualizar_cliente(id, nome, telefone, email):
    """Atualiza cliente com validações"""
    nome = sanitizar_input(nome)
    telefone = sanitizar_input(telefone) if telefone else None
    email = sanitizar_input(email) if email else None
    
    if not nome or len(nome) < 2:
        return False, "Nome do cliente deve ter pelo menos 2 caracteres"
    
    if email and not validar_email(email):
        return False, "Email inválido"
    
    db = DatabaseManager()
    
    if not db.connect():
        return False, "Erro de conexão com o banco"
    
    try:
        cursor = db.execute_query(
            "UPDATE clientes SET nome = ?, telefone = ?, email = ? WHERE id = ?", 
            (nome, telefone, email, id)
        )
        
        if cursor:
            return True, "Cliente atualizado com sucesso"
        else:
            return False, "Erro ao atualizar cliente"
            
    except Exception as e:
        return False, f"Erro ao atualizar cliente: {str(e)}"
    finally:
        db.disconnect()

def excluir_cliente(id):
    """Exclui cliente com tratamento de erro"""
    db = DatabaseManager()
    
    if not db.connect():
        return False, "Erro de conexão com o banco"
    
    try:
        # Verificar se cliente existe
        cliente = db.fetch_one("SELECT id FROM clientes WHERE id = ?", (id,))
        if not cliente:
            return False, "Cliente não encontrado"
        
        cursor = db.execute_query("DELETE FROM clientes WHERE id = ?", (id,))
        
        if cursor:
            return True, "Cliente excluído com sucesso"
        else:
            return False, "Erro ao excluir cliente"
            
    except Exception as e:
        return False, f"Erro ao excluir cliente: {str(e)}"
    finally:
        db.disconnect()

# --- FUNÇÕES DE VENDAS MELHORADAS ---
def registrar_venda_completa(cliente_id, itens_carrinho, total, forma_pagamento, valor_pago, troco):
    """Registra venda completa com transação segura"""
    if not itens_carrinho:
        return None, "Carrinho vazio"
    
    if total <= 0:
        return None, "Total inválido"
    
    db = DatabaseManager()
    
    if not db.connect():
        return None, "Erro de conexão com o banco"
    
    venda_id = None
    try:
        data_venda = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Iniciar transação
        cursor = db.execute_query(
            "INSERT INTO vendas (cliente_id, data_venda, total, forma_pagamento, valor_pago, troco) VALUES (?, ?, ?, ?, ?, ?)", 
            (cliente_id, data_venda, total, forma_pagamento, valor_pago, troco)
        )
        
        if not cursor:
            db.conn.rollback()
            return None, "Erro ao registrar venda"
        
        venda_id = cursor.lastrowid
        
        # Registrar itens da venda e atualizar estoque
        for item in itens_carrinho:
            produto = buscar_produto_por_id(item['id'])
            if not produto:
                db.conn.rollback()
                return None, f"Produto ID {item['id']} não encontrado"
            
            if produto['quantidade'] < item['qtd']:
                db.conn.rollback()
                return None, f"Estoque insuficiente para {produto['nome']}"
            
            # Registrar item da venda
            cursor_item = db.execute_query(
                "INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)", 
                (venda_id, item['id'], item['qtd'], produto['preco'])
            )
            
            if not cursor_item:
                db.conn.rollback()
                return None, "Erro ao registrar item da venda"
            
            # Atualizar estoque
            nova_quantidade = produto['quantidade'] - item['qtd']
            cursor_estoque = db.execute_query(
                "UPDATE produtos SET quantidade = ?, data_atualizacao = CURRENT_TIMESTAMP WHERE id = ?", 
                (nova_quantidade, item['id'])
            )
            
            if not cursor_estoque:
                db.conn.rollback()
                return None, "Erro ao atualizar estoque"
            
            # Registrar saída no histórico
            db.execute_query(
                "INSERT INTO historico_estoque (produto_id, tipo_movimento, quantidade, data_movimento) VALUES (?, 'saida', ?, ?)", 
                (item['id'], item['qtd'], data_venda)
            )
        
        db.conn.commit()
        return venda_id, "Venda registrada com sucesso"
        
    except Exception as e:
        if db.conn:
            db.conn.rollback()
        return None, f"Erro ao registrar venda: {str(e)}"
    finally:
        db.disconnect()

# --- FUNÇÕES DE RELATÓRIOS MELHORADAS ---
def get_relatorio_vendas_detalhado():
    """Relatório detalhado de vendas"""
    db = DatabaseManager()
    
    if not db.connect():
        return []
    
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
    """Relatório de estoque"""
    return listar_produtos()

def get_relatorio_movimentacao_estoque():
    """Relatório de movimentação de estoque"""
    db = DatabaseManager()
    
    if not db.connect():
        return []
    
    query = """
        SELECT h.id, p.nome, h.tipo_movimento, h.quantidade, h.data_movimento
        FROM historico_estoque h 
        JOIN produtos p ON h.produto_id = p.id
        ORDER BY h.data_movimento DESC 
    """
    movimentos = db.fetch_all(query)
    db.disconnect()
    return movimentos

# --- NOVAS FUNÇÕES ADICIONAIS ---
def get_estatisticas_gerais():
    """Retorna estatísticas gerais do sistema"""
    db = DatabaseManager()
    
    if not db.connect():
        return {}
    
    try:
        # Total de produtos
        total_produtos = db.fetch_one("SELECT COUNT(*) as total FROM produtos")['total']
        
        # Produtos em estoque
        produtos_estoque = db.fetch_one("SELECT COUNT(*) as total FROM produtos WHERE quantidade > 0")['total']
        
        # Produtos sem estoque
        produtos_sem_estoque = db.fetch_one("SELECT COUNT(*) as total FROM produtos WHERE quantidade = 0")['total']
        
        # Valor total do estoque
        valor_estoque = db.fetch_one("SELECT SUM(preco * quantidade) as total FROM produtos")['total'] or 0
        
        # Total de vendas
        total_vendas = db.fetch_one("SELECT COUNT(*) as total FROM vendas")['total']
        
        # Valor total vendido
        valor_total_vendas = db.fetch_one("SELECT SUM(total) as total FROM vendas")['total'] or 0
        
        return {
            'total_produtos': total_produtos,
            'produtos_estoque': produtos_estoque,
            'produtos_sem_estoque': produtos_sem_estoque,
            'valor_estoque': round(valor_estoque, 2),
            'total_vendas': total_vendas,
            'valor_total_vendas': round(valor_total_vendas, 2)
        }
        
    except Exception as e:
        print(f"❌ Erro ao buscar estatísticas: {e}")
        return {}
    finally:
        db.disconnect()