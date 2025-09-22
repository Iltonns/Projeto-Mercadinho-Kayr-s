# ==============================================================================
# 1. IMPORTS
# ==============================================================================
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import check_password_hash
import logica_banco as db

# ==============================================================================
# 2. CONFIGURAÇÃO INICIAL DA APLICAÇÃO E EXTENSÕES
# ==============================================================================
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_pode_ser_qualquer_coisa'

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Rota para redirecionar se não estiver logado
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"

# Em app.py, adicione esta rota junto com as de login/logout


# ==============================================================================
# 3. FUNÇÕES ESSENCIAIS DO FLASK-LOGIN
# ==============================================================================
@login_manager.user_loader
def load_user(user_id):
    """Função ESSENCIAL para o Flask-Login: diz como carregar um usuário a partir do ID."""
    return db.get_user_by_id(int(user_id))

# ==============================================================================
# 4. PROCESSADORES DE CONTEXTO
# ==============================================================================
@app.context_processor
def inject_current_year():
    """Injeta o ano atual em todos os templates para o rodapé."""
    return {'current_year': datetime.utcnow().year}

# ==============================================================================
# 5. ROTAS DA APLICAÇÃO
# ==============================================================================

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = db.get_user_by_username(username)

        if usuario and check_password_hash(usuario.password_hash, password):
            login_user(usuario)
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

# --- ROTAS DE CADASTRO ---
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
            
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
            
        # Verifica se o usuário já existe
        if db.get_user_by_username(username):
            flash('Este nome de usuário já existe. Por favor, escolha outro.', 'error')
            return redirect(url_for('cadastro'))

        # Adiciona o novo usuário
        db.add_user(username, password)
        flash('Usuário criado com sucesso! Por favor, faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('cadastro.html')

# --- ROTA PRINCIPAL / ÍNDICE ---
@app.route('/')
@login_required
def index():
    return redirect(url_for('produtos'))

# --- ROTAS DE PRODUTOS (CRUD) ---
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

# --- ROTAS DE CLIENTES (CRUD) ---
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

# --- ROTAS DE VENDAS E CAIXA (PDV) ---
@app.route('/vendas')
@login_required
def vendas():
    vendas_historico = db.get_relatorio_vendas_detalhado()
    return render_template('vendas.html', vendas=vendas_historico)

@app.route('/caixa')
@login_required
def caixa():
    produtos_disponiveis = db.listar_produtos()
    clientes_cadastrados = db.listar_clientes()
    return render_template('caixa.html', produtos=produtos_disponiveis, clientes=clientes_cadastrados)

@app.route('/vendas/nova', methods=['GET', 'POST'])
@login_required
def nova_venda():
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
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
        
        # Aqui usamos a função de registrar venda simples
        db.registrar_venda_completa(cliente_id, carrinho, total, 'N/A', 0, 0)
        flash('Venda registrada com sucesso!', 'success')
        return redirect(url_for('vendas'))
        
    # Para o GET, carregamos produtos e clientes para preencher os <select> no form
    produtos_disponiveis = db.listar_produtos()
    clientes_cadastrados = db.listar_clientes()
    return render_template('venda_formulario.html', produtos=produtos_disponiveis, clientes=clientes_cadastrados)

# --- ROTAS DE API (PARA JAVASCRIPT) ---
@app.route('/api/buscar_produto/<code>')
@login_required
def api_buscar_produto(code):
    produto = db.buscar_produto_por_codigo(code)
    if produto:
        return jsonify(dict(produto))
    else:
        return jsonify({'erro': 'Produto não encontrado'}), 404

@app.route('/caixa/finalizar', methods=['POST'])
@login_required
def finalizar_venda():
    try:
        dados = request.get_json()
        if not dados or 'itens' not in dados or not dados['itens']:
            return jsonify({'erro': 'Dados da venda inválidos ou carrinho vazio.'}), 400
        
        itens_carrinho = dados.get('itens')
        total_recalculado = 0
        
        for item in itens_carrinho:
            produto = db.buscar_produto_por_id(item['id'])
            if not produto: return jsonify({'erro': f'Produto com ID {item["id"]} não encontrado.'}), 400
            if item['qtd'] > produto['quantidade']: return jsonify({'erro': f'Estoque insuficiente para o produto {produto["nome"]}.'}), 400
            total_recalculado += produto['preco'] * item['qtd']
            
        db.registrar_venda_completa(
            cliente_id=dados.get('cliente_id'), itens_carrinho=itens_carrinho, total=total_recalculado,
            forma_pagamento=dados.get('forma_pagamento', 'N/A'), valor_pago=dados.get('valor_pago', total_recalculado),
            troco=dados.get('troco', 0)
        )
        return jsonify({'mensagem': 'Venda finalizada com sucesso!'})
    except Exception as e:
        print(f"Erro ao finalizar venda: {e}")
        return jsonify({'erro': 'Ocorreu um erro interno no servidor.'}), 500

# --- ROTAS DE RELATÓRIOS ---
@app.route('/relatorios')
@login_required
def relatorios():
    relatorio_estoque = db.get_relatorio_estoque()
    relatorio_movimentacao = db.get_relatorio_movimentacao_estoque()
    return render_template('relatorios.html', estoque=relatorio_estoque, movimentacoes=relatorio_movimentacao)

# ==============================================================================
# 6. BLOCO DE EXECUÇÃO
# ==============================================================================
if __name__ == '__main__':
    db.setup_database()  # Garante que todas as tabelas, incluindo 'usuarios', sejam criadas
    app.run(debug=True)