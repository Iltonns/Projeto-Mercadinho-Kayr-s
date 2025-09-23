
# ==============================================================================
# 1. IMPORTS MELHORADOS
# ==============================================================================
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import check_password_hash
import logica_banco as db
import re
import os

# ==============================================================================
# 2. CONFIGURAÇÃO INICIAL DA APLICAÇÃO E EXTENSÕES MELHORADA
# ==============================================================================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_super_segura_aqui_2024')

# Configurações de segurança
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # True em produção com HTTPS
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "warning"

# ==============================================================================
# 3. FUNÇÕES AUXILIARES DE SEGURANÇA
# ==============================================================================
def sanitizar_input(texto):
    """Remove caracteres perigosos"""
    if not texto:
        return ""
    texto = re.sub(r'<[^>]*>', '', texto)
    texto = texto.strip()
    return texto

def validar_email(email):
    """Valida formato de email"""
    if not email:
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validar_senha(senha):
    """Valida força da senha"""
    if len(senha) < 6:
        return False, "Senha deve ter pelo menos 6 caracteres"
    return True, ""

# ==============================================================================
# 4. FUNÇÕES ESSENCIAIS DO FLASK-LOGIN
# ==============================================================================
@login_manager.user_loader
def load_user(user_id):
    """Função ESSENCIAL para o Flask-Login: diz como carregar um usuário a partir do ID."""
    try:
        return db.get_user_by_id(int(user_id))
    except (ValueError, TypeError):
        return None

# ==============================================================================
# 5. MIDDLEWARE E PROCESSADORES DE CONTEXTO
# ==============================================================================
@app.before_request
def before_request():
    """Validações globais antes de cada requisição"""
    # Proteção básica contra dados maliciosos em POST
    if request.method == 'POST':
        for key, value in request.form.items():
            if len(str(value)) > 1000:
                flash('Dados enviados são muito grandes!', 'danger')
                return redirect(url_for('index'))

@app.context_processor
def inject_template_vars():
    """Injeta variáveis em todos os templates"""
    return {
        'current_year': datetime.utcnow().year,
        'current_user': current_user
    }

# ==============================================================================
# 6. HANDLERS DE ERRO PROFISSIONAIS
# ==============================================================================
@app.errorhandler(404)
def pagina_nao_encontrada(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def erro_interno(error):
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def acesso_negado(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(400)
def requisicao_ruim(error):
    return render_template('errors/400.html'), 400

@app.errorhandler(Exception)
def handle_general_error(error):
    print(f"Erro não tratado: {str(error)}")
    return render_template('errors/500.html'), 500

# ==============================================================================
# 7. ROTAS DE AUTENTICAÇÃO MELHORADAS
# ==============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Rota de login com validações melhoradas"""
    if current_user.is_authenticated:
        flash('Você já está logado!', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            username = sanitizar_input(request.form.get('username', ''))
            password = request.form.get('password', '')

            if not username or not password:
                flash('Por favor, preencha todos os campos.', 'danger')
                return render_template('login.html')

            usuario = db.get_user_by_username(username)

            if usuario and usuario.verify_password(password):
                login_user(usuario)
                
                # Registrar dados na sessão
                session['usuario_id'] = usuario.id
                session['usuario_nome'] = usuario.username
                
                flash(f'Bem-vindo, {usuario.username}!', 'success')
                
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Usuário ou senha inválidos.', 'danger')

        except Exception as e:
            flash('Erro durante o login. Tente novamente.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Rota de logout - CORRIGIDA"""
    try:
        # Limpar flash messages primeiro
        session.pop('_flashes', None)
        
        username = current_user.username
        logout_user()  # Flask-Login logout
        
        # Limpar completamente a sessão
        session.clear()
        
        # Garantir que a sessão seja realmente limpa
        session.permanent = False
        
        flash(f'Até logo, {username}! Você saiu do sistema.', 'info')
        return redirect(url_for('login'))
        
    except Exception as e:
        print(f"Erro durante logout: {e}")
        # Forçar limpeza em caso de erro
        session.clear()
        return redirect(url_for('login'))
    
@app.after_request
def after_request(response):
    """Limpar flash messages após cada requisição para evitar acumulação"""
    if '_flashes' in session:
        # Manter apenas as flash messages mais recentes
        flashes = session.get('_flashes', [])
        if len(flashes) > 3:  # Limitar a 3 mensagens
            session['_flashes'] = flashes[-3:]
    return response    

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Rota de cadastro com validações robustas"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
            
    if request.method == 'POST':
        try:
            username = sanitizar_input(request.form.get('username', ''))
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            # Validações
            if not username or not password or not confirm_password:
                flash('Por favor, preencha todos os campos.', 'danger')
                return render_template('cadastro.html')

            if len(username) < 3:
                flash('Nome de usuário deve ter pelo menos 3 caracteres.', 'danger')
                return render_template('cadastro.html')

            if password != confirm_password:
                flash('As senhas não coincidem.', 'danger')
                return render_template('cadastro.html')

            senha_valida, msg_erro = validar_senha(password)
            if not senha_valida:
                flash(msg_erro, 'danger')
                return render_template('cadastro.html')

            # Tentar criar usuário
            sucesso, mensagem = db.add_user(username, password)
            
            if sucesso:
                flash('Usuário criado com sucesso! Por favor, faça login.', 'success')
                return redirect(url_for('login'))
            else:
                flash(mensagem, 'danger')

        except Exception as e:
            flash('Erro durante o cadastro. Tente novamente.', 'danger')

    return render_template('cadastro.html')

# ==============================================================================
# 8. ROTAS PRINCIPAIS MELHORADAS
# ==============================================================================
@app.route('/')
def index():
    """Página inicial redireciona para login ou dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard administrativo com estatísticas"""
    try:
        estatisticas = db.get_estatisticas_gerais()
        produtos_recentes = db.listar_produtos()[:5]  # Últimos 5 produtos
        
        return render_template('dashboard.html', 
                             estatisticas=estatisticas,
                             produtos_recentes=produtos_recentes)
    except Exception as e:
        flash('Erro ao carregar dashboard.', 'danger')
        return redirect(url_for('produtos'))

# ==============================================================================
# 9. ROTAS DE PRODUTOS MELHORADAS (CRUD)
# ==============================================================================
@app.route('/produtos')
@login_required
def produtos():
    """Lista de produtos com tratamento de erro"""
    try:
        lista_produtos = db.listar_produtos()
        return render_template('produtos.html', produtos=lista_produtos)
    except Exception as e:
        flash('Erro ao carregar produtos.', 'danger')
        return render_template('produtos.html', produtos=[])

@app.route('/produtos/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_produto():
    """Adicionar produto com validações"""
    if request.method == 'POST':
        try:
            nome = sanitizar_input(request.form.get('nome', ''))
            preco = request.form.get('preco', '')
            quantidade = request.form.get('quantidade', '')
            codigo_barras = sanitizar_input(request.form.get('codigo_barras', ''))

            # Validações
            if not nome or len(nome) < 2:
                flash('Nome do produto deve ter pelo menos 2 caracteres.', 'danger')
                return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)

            try:
                preco_float = float(preco)
                if preco_float <= 0:
                    flash('Preço deve ser maior que zero.', 'danger')
                    return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)
            except (ValueError, TypeError):
                flash('Preço inválido.', 'danger')
                return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)

            try:
                quantidade_int = int(quantidade)
                if quantidade_int < 0:
                    flash('Quantidade não pode ser negativa.', 'danger')
                    return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)
            except (ValueError, TypeError):
                flash('Quantidade inválida.', 'danger')
                return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)

            # Adicionar produto
            sucesso, mensagem = db.adicionar_produto(nome, preco_float, quantidade_int, codigo_barras)
            
            if sucesso:
                flash('Produto adicionado com sucesso!', 'success')
                return redirect(url_for('produtos'))
            else:
                flash(mensagem, 'danger')

        except Exception as e:
            flash('Erro ao adicionar produto. Tente novamente.', 'danger')

    return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)

@app.route('/produtos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    """Editar produto existente"""
    produto_existente = db.buscar_produto_por_id(id)
    
    if not produto_existente:
        flash('Produto não encontrado.', 'danger')
        return redirect(url_for('produtos'))

    if request.method == 'POST':
        try:
            nome = sanitizar_input(request.form.get('nome', ''))
            preco = request.form.get('preco', '')
            quantidade = request.form.get('quantidade', '')
            codigo_barras = sanitizar_input(request.form.get('codigo_barras', ''))

            # Validações (iguais à adição)
            if not nome or len(nome) < 2:
                flash('Nome do produto deve ter pelo menos 2 caracteres.', 'danger')
                return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)

            try:
                preco_float = float(preco)
                if preco_float <= 0:
                    flash('Preço deve ser maior que zero.', 'danger')
                    return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)
            except (ValueError, TypeError):
                flash('Preço inválido.', 'danger')
                return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)

            try:
                quantidade_int = int(quantidade)
                if quantidade_int < 0:
                    flash('Quantidade não pode ser negativa.', 'danger')
                    return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)
            except (ValueError, TypeError):
                flash('Quantidade inválida.', 'danger')
                return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)

            # Atualizar produto
            sucesso, mensagem = db.atualizar_produto(id, nome, preco_float, quantidade_int, codigo_barras)
            
            if sucesso:
                flash('Produto atualizado com sucesso!', 'success')
                return redirect(url_for('produtos'))
            else:
                flash(mensagem, 'danger')

        except Exception as e:
            flash('Erro ao atualizar produto. Tente novamente.', 'danger')

    return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)

@app.route('/produtos/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_produto(id):
    """Excluir produto com confirmação"""
    try:
        sucesso, mensagem = db.excluir_produto(id)
        
        if sucesso:
            flash('Produto excluído com sucesso!', 'success')
        else:
            flash(mensagem, 'danger')
            
    except Exception as e:
        flash('Erro ao excluir produto.', 'danger')
    
    return redirect(url_for('produtos'))

# ==============================================================================
# 10. ROTAS DE CLIENTES MELHORADAS (CRUD)
# ==============================================================================
@app.route('/clientes')
@login_required
def clientes():
    """Lista de clientes"""
    try:
        lista_clientes = db.listar_clientes()
        return render_template('clientes.html', clientes=lista_clientes)
    except Exception as e:
        flash('Erro ao carregar clientes.', 'danger')
        return render_template('clientes.html', clientes=[])

@app.route('/clientes/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_cliente():
    """Adicionar cliente com validações"""
    if request.method == 'POST':
        try:
            nome = sanitizar_input(request.form.get('nome', ''))
            telefone = sanitizar_input(request.form.get('telefone', ''))
            email = sanitizar_input(request.form.get('email', ''))

            # Validações
            if not nome or len(nome) < 2:
                flash('Nome do cliente deve ter pelo menos 2 caracteres.', 'danger')
                return render_template('cliente_formulario.html', titulo="Adicionar Cliente", cliente=None)

            if email and not validar_email(email):
                flash('Email inválido.', 'danger')
                return render_template('cliente_formulario.html', titulo="Adicionar Cliente", cliente=None)

            sucesso, mensagem = db.adicionar_cliente(nome, telefone, email)
            
            if sucesso:
                flash('Cliente adicionado com sucesso!', 'success')
                return redirect(url_for('clientes'))
            else:
                flash(mensagem, 'danger')

        except Exception as e:
            flash('Erro ao adicionar cliente. Tente novamente.', 'danger')

    return render_template('cliente_formulario.html', titulo="Adicionar Cliente", cliente=None)

@app.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    """Editar cliente existente"""
    cliente_existente = db.buscar_cliente_por_id(id)
    
    if not cliente_existente:
        flash('Cliente não encontrado.', 'danger')
        return redirect(url_for('clientes'))

    if request.method == 'POST':
        try:
            nome = sanitizar_input(request.form.get('nome', ''))
            telefone = sanitizar_input(request.form.get('telefone', ''))
            email = sanitizar_input(request.form.get('email', ''))

            # Validações
            if not nome or len(nome) < 2:
                flash('Nome do cliente deve ter pelo menos 2 caracteres.', 'danger')
                return render_template('cliente_formulario.html', titulo="Editar Cliente", cliente=cliente_existente)

            if email and not validar_email(email):
                flash('Email inválido.', 'danger')
                return render_template('cliente_formulario.html', titulo="Editar Cliente", cliente=cliente_existente)

            sucesso, mensagem = db.atualizar_cliente(id, nome, telefone, email)
            
            if sucesso:
                flash('Cliente atualizado com sucesso!', 'success')
                return redirect(url_for('clientes'))
            else:
                flash(mensagem, 'danger')

        except Exception as e:
            flash('Erro ao atualizar cliente. Tente novamente.', 'danger')

    return render_template('cliente_formulario.html', titulo="Editar Cliente", cliente=cliente_existente)

@app.route('/clientes/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_cliente(id):
    """Excluir cliente"""
    try:
        sucesso, mensagem = db.excluir_cliente(id)
        
        if sucesso:
            flash('Cliente excluído com sucesso!', 'success')
        else:
            flash(mensagem, 'danger')
            
    except Exception as e:
        flash('Erro ao excluir cliente.', 'danger')
    
    return redirect(url_for('clientes'))

# ==============================================================================
# 11. ROTAS DE VENDAS E CAIXA MELHORADAS
# ==============================================================================
@app.route('/vendas')
@login_required
def vendas():
    """Histórico de vendas"""
    try:
        vendas_historico = db.get_relatorio_vendas_detalhado()
        return render_template('vendas.html', vendas=vendas_historico)
    except Exception as e:
        flash('Erro ao carregar histórico de vendas.', 'danger')
        return render_template('vendas.html', vendas=[])

@app.route('/caixa')
@login_required
def caixa():
    """PDV - Ponto de Venda"""
    try:
        produtos_disponiveis = db.listar_produtos()
        clientes_cadastrados = db.listar_clientes()
        return render_template('caixa.html', produtos=produtos_disponiveis, clientes=clientes_cadastrados)
    except Exception as e:
        flash('Erro ao carregar caixa.', 'danger')
        return render_template('caixa.html', produtos=[], clientes=[])

# Rotas API
@app.route('/api/buscar_produto/<code>')
@login_required
def api_buscar_produto(code):
    """API para buscar produto por código ou nome - CORRIGIDA"""
    try:
        print(f"🔍 [DEBUG] Buscando produto por: '{code}'")
        
        code = sanitizar_input(code)
        
        if not code or len(code) < 1:
            return jsonify({'erro': 'Termo de busca inválido'}), 400
        
        # Buscar produto por código
        produto = db.buscar_produto_por_codigo(code)
        
        # Se não encontrou, buscar por nome (busca parcial)
        if not produto:
            produto = db.buscar_produto_por_nome(code)
        
        if produto:
            # Garantir que os dados estão no formato correto
            produto_dict = {
                'id': produto.id if hasattr(produto, 'id') else produto['id'],
                'nome': produto.nome if hasattr(produto, 'nome') else produto['nome'],
                'preco': float(produto.preco if hasattr(produto, 'preco') else produto['preco']),
                'quantidade': produto.quantidade if hasattr(produto, 'quantidade') else produto['quantidade'],
                'codigo_barras': produto.codigo_barras if hasattr(produto, 'codigo_barras') else produto.get('codigo_barras', '')
            }
            return jsonify(produto_dict)
        else:
            return jsonify({'erro': 'Produto não encontrado'}), 404
            
    except Exception as e:
        print(f"Erro na API: {str(e)}")
        return jsonify({'erro': 'Erro interno do servidor'}), 500

# NOVA ROTA PARA AUTCOMPLETE
@app.route('/api/autocomplete_produtos/<termo>')
@login_required
def autocomplete_produtos(termo):
    """API para autocomplete de produtos"""
    try:
        termo = sanitizar_input(termo)
        
        if not termo or len(termo) < 2:
            return jsonify([])
        
        # Buscar produtos que contenham o termo no nome ou código
        produtos = db.buscar_produtos_por_termo(termo)
        
        resultados = []
        for produto in produtos:
            resultados.append({
                'id': produto.id if hasattr(produto, 'id') else produto['id'],
                'nome': produto.nome if hasattr(produto, 'nome') else produto['nome'],
                'preco': float(produto.preco if hasattr(produto, 'preco') else produto['preco']),
                'quantidade': produto.quantidade if hasattr(produto, 'quantidade') else produto['quantidade'],
                'codigo_barras': produto.codigo_barras if hasattr(produto, 'codigo_barras') else produto.get('codigo_barras', '')
            })
        
        return jsonify(resultados)
        
    except Exception as e:
        print(f"Erro no autocomplete: {str(e)}")
        return jsonify([])

@app.route('/caixa/finalizar', methods=['POST'])
@login_required
def finalizar_venda():
    """Finalizar venda via AJAX"""
    try:
        dados = request.get_json()
        print(f"🛒 Dados recebidos: {dados}")
        
        if not dados or 'itens' not in dados or not dados['itens']:
            return jsonify({'sucesso': False, 'erro': 'Carrinho vazio.'}), 400
        
        itens_carrinho = dados.get('itens', [])
        total_recalculado = 0
        itens_validados = []

        for item in itens_carrinho:
            produto_id = item.get('id')
            quantidade = int(item.get('quantidade', 0))
            preco_front = float(item.get('preco', 0))  # enviado pelo front
            subtotal_front = float(item.get('subtotal', 0))  # enviado pelo front
            
            if not produto_id or quantidade <= 0:
                return jsonify({'sucesso': False, 'erro': 'Item inválido no carrinho.'}), 400

            produto = db.buscar_produto_por_id(produto_id)
            if not produto:
                return jsonify({'sucesso': False, 'erro': f'Produto com ID {produto_id} não encontrado.'}), 400
            
            if quantidade > produto.quantidade:
                return jsonify({'sucesso': False, 'erro': f'Estoque insuficiente para {produto.nome}. Disponível: {produto.quantidade}'}), 400
            
            # Preço oficial do banco (segurança contra alteração no front)
            preco_oficial = float(produto.preco)
            subtotal_calculado = preco_oficial * quantidade

            # Comparar com subtotal enviado pelo front (opcional)
            if abs(subtotal_calculado - subtotal_front) > 0.01:
                print(f"⚠️ Divergência detectada no item {produto.nome}: front={subtotal_front}, server={subtotal_calculado}")
            
            itens_validados.append({
                'id': produto.id,
                'nome': produto.nome,
                'quantidade': quantidade,
                'preco': preco_oficial,
                'subtotal': subtotal_calculado
            })

            total_recalculado += subtotal_calculado

        # Registrar venda
        venda_id, mensagem = db.registrar_venda_completa(
            cliente_id=dados.get('cliente_id'),
            itens_carrinho=itens_validados,
            total=total_recalculado,
            forma_pagamento=dados.get('forma_pagamento', 'Dinheiro'),
            valor_pago=dados.get('valor_pago', total_recalculado),
            troco=dados.get('troco', 0)
        )

        if venda_id:
            return jsonify({
                'sucesso': True,
                'mensagem': 'Venda finalizada com sucesso!',
                'venda_id': venda_id
            })
        else:
            return jsonify({'sucesso': False, 'erro': mensagem}), 400

    except Exception as e:
        print(f"❌ Erro ao finalizar venda: {str(e)}")
        return jsonify({'sucesso': False, 'erro': 'Erro interno do servidor.'}), 500


# ==============================================================================
# 12. ROTAS DE RELATÓRIOS
# ==============================================================================
@app.route('/relatorios')
@login_required
def relatorios():
    """Página de relatórios"""
    try:
        relatorio_estoque = db.get_relatorio_estoque()
        relatorio_movimentacao = db.get_relatorio_movimentacao_estoque()
        estatisticas = db.get_estatisticas_gerais()
        
        return render_template('relatorios.html', 
                             estoque=relatorio_estoque, 
                             movimentacoes=relatorio_movimentacao,
                             estatisticas=estatisticas)
    except Exception as e:
        flash('Erro ao carregar relatórios.', 'danger')
        return render_template('relatorios.html', estoque=[], movimentacoes=[], estatisticas={})

# ==============================================================================
# 13. BLOCO DE EXECUÇÃO MELHORADO
# ==============================================================================
if __name__ == '__main__':
    # Configuração inicial do banco
    if db.setup_database():
        print("✅ Banco de dados configurado com sucesso!")
    else:
        print("❌ Erro ao configurar banco de dados!")
    
    # Executar aplicação
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    
    app.run(host=host, port=port, debug=debug_mode)
