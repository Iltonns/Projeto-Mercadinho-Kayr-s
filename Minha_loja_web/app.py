# Arquivo: app.py
from datetime import datetime
import logica_banco as db 
from flask import jsonify
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'Daniele123'

# --- Configuração do Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redireciona para a rota 'login' se o usuário não estiver logado
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"

# --- Instância do Gerenciador de Banco de Dados ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.get_user_by_username(username)

        # Verifica se o usuário existe e se a senha está correta
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    usuario = db.buscar_usuario_por_id(user_id)
    if usuario:
        return User(usuario['id'], usuario['nome'], usuario['senha_hash'])
    return None

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.utcnow().year}

# --- Rotas Principais ---
@app.route('/')
def index():
    return redirect(url_for('produtos'))

# --- Rotas de PRODUTOS (Já estavam prontas) ---
@app.route('/produtos')
@login_required
def produtos():
    lista_produtos = db.listar_produtos()
    return render_template('produtos.html', produtos=lista_produtos)

@app.route('/produtos/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_produto():
    if request.method == 'POST':
        db.adicionar_produto(request.form['nome'], float(request.form['preco']), int(request.form['quantidade']), request.form.get('codigo_barras'))
        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('produtos'))
    return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)

@app.route('/produtos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    if request.method == 'POST':
        db.atualizar_produto(id, request.form['nome'], float(request.form['preco']), int(request.form['quantidade']), request.form.get('codigo_barras'))
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('produtos'))
    produto_existente = db.buscar_produto_por_id(id)
    return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)

@app.route('/produtos/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_produto(id):
    db.excluir_produto(id)
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('produtos'))

def buscar_produto_por_codigo(codigo):
    """Busca um produto pelo nome ou código de barras."""
    db = db.DatabaseManager()
    db.connect()
    # Busca primeiro pelo código de barras, depois por nome parcial
    produto = db.fetch_one("SELECT * FROM produtos WHERE codigo_barras = ? OR nome LIKE ?", (codigo, f'%{codigo}%'))
    db.disconnect()
    return produto

    # Busca primeiro pelo código de barras, depois por nome parcial
    produto = db.fetch_one("SELECT * FROM produtos WHERE codigo_barras = ? OR nome LIKE ?", (codigo, f'%{codigo}%'))
    db.disconnect()
    return produto

# --- Rotas de CLIENTES (Agora completas) ---
@app.route('/clientes')
@login_required
def clientes():
    lista_clientes = db.listar_clientes()
    return render_template('clientes.html', clientes=lista_clientes)

@app.route('/clientes/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_cliente():
    if request.method == 'POST':
        db.adicionar_cliente(request.form['nome'], request.form['telefone'], request.form.get('email'))
        flash('Cliente adicionado com sucesso!', 'success')
        return redirect(url_for('clientes'))
    return render_template('cliente_formulario.html', titulo="Adicionar Cliente", cliente=None)

@app.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    if request.method == 'POST':
        db.atualizar_cliente(id, request.form['nome'], request.form['telefone'], request.form.get('email'))
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('clientes'))
    cliente_existente = db.buscar_cliente_por_id(id)
    return render_template('cliente_formulario.html', titulo="Editar Cliente", cliente=cliente_existente)

@app.route('/clientes/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_cliente(id):
    db.excluir_cliente(id)
    flash('Cliente excluído com sucesso!', 'success')
    return redirect(url_for('clientes'))

# --- Rotas de VENDAS (Agora completas) ---
@app.route('/vendas')
@login_required
def vendas():
    vendas_historico = db.get_relatorio_vendas_detalhado()
    return render_template('vendas.html', vendas=vendas_historico)

# A rota de nova venda é complexa, um exemplo simples:
@app.route('/vendas/nova', methods=['GET', 'POST'])
@login_required
def nova_venda():
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        # A lógica para coletar múltiplos produtos de um formulário pode ser complexa.
        # Este é um exemplo simplificado onde pegamos apenas um produto.
        produto_id = request.form.get('produto_id')
        quantidade = int(request.form.get('quantidade', 0))

        if not produto_id or quantidade <= 0:
            flash('Selecione um produto e uma quantidade válida.', 'error')
            return redirect(url_for('nova_venda'))

        produto = db.buscar_produto_por_id(produto_id)
        if quantidade > produto['quantidade']:
             flash(f'Estoque insuficiente para {produto["nome"]}.', 'error')
             return redirect(url_for('nova_venda'))
             
        total = produto['preco'] * quantidade
        carrinho = [{'id': produto_id, 'qtd': quantidade}]
        
        db.registrar_venda(cliente_id, carrinho, total)
        flash('Venda registrada com sucesso!', 'success')
        return redirect(url_for('vendas'))
        
    # Para o GET, carregamos produtos e clientes para preencher os <select> no form
    produtos_disponiveis = db.listar_produtos()
    clientes_cadastrados = db.listar_clientes()
    return render_template('venda_formulario.html', produtos=produtos_disponiveis, clientes=clientes_cadastrados)


# --- Rotas de RELATÓRIOS (Agora completa) ---
@app.route('/relatorios')
@login_required
def relatorios():
    relatorio_estoque = db.get_relatorio_estoque()
    relatorio_movimentacao = db.get_relatorio_movimentacao_estoque()
    return render_template('relatorios.html', 
                           estoque=relatorio_estoque, 
                           movimentacoes=relatorio_movimentacao)

# --- Rotas de PONTO DE VENDA (Agora completa) ---  
@app.route('/caixa')
@login_required
def caixa():
    """ Rota para servir a página principal do Ponto de Venda (Caixa). """
    # Lembre-se que a página do caixa pode precisar de dados, como a lista de produtos e clientes
    produtos_disponiveis = db.listar_produtos()
    clientes_cadastrados = db.listar_clientes()
    return render_template('caixa.html', produtos=produtos_disponiveis, clientes=clientes_cadastrados)

@app.route('/api/buscar_produto/<code>')
@login_required
def api_buscar_produto(code):
    """ API para buscar um produto pelo código. Retorna dados em JSON. """
    produto = db.buscar_produto_por_codigo(code)
    if produto:
        produto_dict = dict(produto)
        return jsonify(produto_dict)
    else:
        return jsonify({'erro': 'Produto não encontrado'}), 404

# Substitua sua rota finalizar_venda por esta em app.py

@app.route('/caixa/finalizar', methods=['POST'])
@login_required
def finalizar_venda():
    """ 
    API que recebe os dados do carrinho do JavaScript, VALIDA, RECALCULA O TOTAL,
    e finaliza a venda. 
    """
    try:
        dados = request.get_json()

        # 1. Validação básica dos dados recebidos
        if not dados or 'itens' not in dados or not dados['itens']:
            return jsonify({'erro': 'Dados da venda inválidos ou carrinho vazio.'}), 400

        itens_carrinho = dados.get('itens')
        total_recalculado = 0

        # 2. Recalcular o total no backend para garantir a integridade
        for item in itens_carrinho:
            produto = db.buscar_produto_por_id(item['id'])
            if not produto:
                return jsonify({'erro': f'Produto com ID {item["id"]} não encontrado.'}), 400
            
            # Verifica se há estoque suficiente
            if item['qtd'] > produto['quantidade']:
                return jsonify({'erro': f'Estoque insuficiente para o produto {produto["nome"]}.'}), 400

            total_recalculado += produto['preco'] * item['qtd']

        # 3. Pegar os dados de pagamento
        cliente_id = dados.get('cliente_id')
        forma_pagamento = dados.get('forma_pagamento', 'N/A')
        valor_pago = dados.get('valor_pago', total_recalculado)
        troco = dados.get('troco', 0)

        # 4. Chamar a função de lógica (que também vamos atualizar)
        db.registrar_venda_completa(
            cliente_id=cliente_id, 
            itens_carrinho=itens_carrinho, 
            total=total_recalculado,
            forma_pagamento=forma_pagamento,
            valor_pago=valor_pago,
            troco=troco
        )
        
        return jsonify({'mensagem': 'Venda finalizada com sucesso!'})

    except Exception as e:
        # Captura qualquer outro erro inesperado
        print(f"Erro ao finalizar venda: {e}")
        return jsonify({'erro': 'Ocorreu um erro interno no servidor.'}), 500
    
# --- Funções de USUÁRIOS (Novas) ---   
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def __repr__(self):
        return f'<User {self.username}>'

def get_user_by_id(user_id):
    db = DatabaseManager()
    db.connect()
    user_data = db.fetch_one("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    db.disconnect()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
    return None

def get_user_by_username(username):
    db = DatabaseManager()
    db.connect()
    user_data = db.fetch_one("SELECT * FROM usuarios WHERE username = ?", (username,))
    db.disconnect()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password_hash'])
    return None

def add_user(username, password):
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    db = DatabaseManager()
    db.connect()
    db.execute_query("INSERT INTO usuarios (username, password_hash) VALUES (?, ?)", (username, password_hash))
    db.disconnect()
    
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            add_user(username, password)
            flash('Usuário criado com sucesso! Faça login.')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Erro ao criar usuário: ' + str(e))
    return render_template('cadastro.html')

# --- Bloco de Execução ---
if __name__ == '__main__':
    db.setup_database()
    app.run(debug=True)
