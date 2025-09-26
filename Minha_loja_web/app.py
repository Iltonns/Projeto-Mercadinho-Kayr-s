# ==============================================================================
# 1. IMPORTS MELHORADOS
# ==============================================================================
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import check_password_hash
import logica_banco as db
import re
import os
import io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

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
    """Rota de logout CORRIGIDA"""
    try:
        # 1. Primeiro obtemos o username ANTES de fazer logout
        username = current_user.username
        
        # 2. Fazemos logout do Flask-Login
        logout_user()
        
        # 3. Limpamos completamente a sessão
        session.clear()
        
        # 4. Mensagem única de flash
        flash(f'Até logo, {username}! Você foi desconectado com sucesso.', 'info')
        
        # 5. Redirecionamento claro
        return redirect(url_for('login'))
        
    except Exception as e:
        # Em caso de erro, força o redirect sem flash para evitar duplicação
        return redirect(url_for('login'))

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
# 9. ROTAS DE PRODUTOS MELHORADAS (CRUD) - CORRIGIDAS
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
# 9.1 ROTAS DE BUSCA DE PRODUTOS - NOVAS E CORRIGIDAS
# ==============================================================================
@app.route('/buscar_produto_caixa', methods=['POST'])
@login_required
def buscar_produto_caixa():
    """Busca de produtos para o caixa - CORRIGIDA"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Dados inválidos'})
        
        codigo = sanitizar_input(data.get('codigo', ''))
        
        if not codigo:
            return jsonify({'success': False, 'message': 'Código ou nome do produto é obrigatório'})
        
        # Buscar produto por código ou nome
        produto = db.buscar_produto_por_codigo(codigo)
        if not produto:
            # Tentar buscar por nome se não encontrar por código
            produtos = db.listar_produtos()
            for prod in produtos:
                if codigo.lower() in prod['nome'].lower():
                    produto = prod
                    break
        
        if produto:
            return jsonify({
                'success': True,
                'produto': {
                    'id': produto['id'],
                    'nome': produto['nome'],
                    'preco': produto['preco'],
                    'quantidade': produto['quantidade'],
                    'codigo': produto.get('codigo_barras', '')
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Produto não encontrado'})
            
    except Exception as e:
        print(f"Erro na busca: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@app.route('/buscar_produto_estoque', methods=['POST'])
@login_required
def buscar_produto_estoque():
    """Busca de produtos para o estoque - CORRIGIDA"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Dados inválidos'})
        
        codigo = sanitizar_input(data.get('codigo', ''))
        
        if not codigo:
            return jsonify({'success': False, 'message': 'Código ou nome do produto é obrigatório'})
        
        # Buscar produto por código ou nome
        produto = db.buscar_produto_por_codigo(codigo)
        if not produto:
            # Tentar buscar por nome se não encontrar por código
            produtos = db.listar_produtos()
            for prod in produtos:
                if codigo.lower() in prod['nome'].lower():
                    produto = prod
                    break
        
        if produto:
            return jsonify({
                'success': True,
                'produto': {
                    'id': produto['id'],
                    'nome': produto['nome'],
                    'preco': produto['preco'],
                    'quantidade': produto['quantidade'],
                    'codigo': produto.get('codigo_barras', '')
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Produto não encontrado'})
            
    except Exception as e:
        print(f"Erro na busca: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

# ==============================================================================
# 9.2 ROTA DE ATUALIZAÇÃO DE PRODUTOS - CORRIGIDA
# ==============================================================================
@app.route('/atualizar_produto', methods=['POST'])
@login_required
def atualizar_produto():
    """Atualizar produto - CORRIGIDA"""
    try:
        produto_id = request.form.get('produto_id')
        nome = sanitizar_input(request.form.get('nome', ''))
        preco = request.form.get('preco', '')
        quantidade = request.form.get('quantidade', '')
        codigo = sanitizar_input(request.form.get('codigo_barras', ''))
        
        if not produto_id:
            flash('ID do produto é obrigatório', 'error')
            return redirect('/estoque')
        
        # Validações
        if not nome or len(nome) < 2:
            flash('Nome do produto deve ter pelo menos 2 caracteres.', 'error')
            return redirect('/estoque')

        try:
            preco_float = float(preco)
            if preco_float <= 0:
                flash('Preço deve ser maior que zero.', 'error')
                return redirect('/estoque')
        except (ValueError, TypeError):
            flash('Preço inválido.', 'error')
            return redirect('/estoque')

        try:
            quantidade_int = int(quantidade)
            if quantidade_int < 0:
                flash('Quantidade não pode ser negativa.', 'error')
                return redirect('/estoque')
        except (ValueError, TypeError):
            flash('Quantidade inválida.', 'error')
            return redirect('/estoque')

        # Atualizar produto
        sucesso, mensagem = db.atualizar_produto(int(produto_id), nome, preco_float, quantidade_int, codigo)
        
        if sucesso:
            flash('Produto atualizado com sucesso!', 'success')
        else:
            flash(mensagem, 'error')
        
        return redirect('/estoque')
        
    except Exception as e:
        flash(f'Erro ao atualizar produto: {str(e)}', 'error')
        return redirect('/estoque')

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

# Na rota /api/buscar_produto/<code> - CORRIGIDA
@app.route('/api/buscar_produto/<code>')
@login_required
def api_buscar_produto(code):
    """API para buscar produto por código - CORRIGIDA"""
    try:
        code = sanitizar_input(code)
        produto = db.buscar_produto_por_codigo(code)
        if produto:
            # CORREÇÃO: Já está convertido para dict na função
            return jsonify(produto)
        else:
            return jsonify({'erro': 'Produto não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': 'Erro interno do servidor'}), 500

# Na rota /dashboard - CORRIGIDA
@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard administrativo com estatísticas - CORRIGIDA"""
    try:
        estatisticas = db.get_estatisticas_gerais()
        produtos_recentes = db.listar_produtos()[:5]  # ← Agora funciona corretamente
        
        return render_template('dashboard.html', 
                             estatisticas=estatisticas,
                             produtos_recentes=produtos_recentes)
    except Exception as e:
        flash('Erro ao carregar dashboard.', 'danger')
        return redirect(url_for('produtos'))

@app.route('/caixa/finalizar', methods=['POST'])
@login_required
def finalizar_venda():
    """Finalizar venda via AJAX"""
    try:
        dados = request.get_json()
        
        if not dados or 'itens' not in dados or not dados['itens']:
            return jsonify({'erro': 'Dados da venda inválidos ou carrinho vazio.'}), 400
        
        itens_carrinho = dados.get('itens', [])
        total_recalculado = 0
        
        # Validar cada item do carrinho
        for item in itens_carrinho:
            produto = db.buscar_produto_por_id(item['id'])
            if not produto:
                return jsonify({'erro': f'Produto com ID {item["id"]} não encontrado.'}), 400
            
            if item['qtd'] > produto['quantidade']:
                return jsonify({'erro': f'Estoque insuficiente para {produto["nome"]}.'}), 400
            
            total_recalculado += produto['preco'] * item['qtd']
        
        # Registrar venda
        venda_id, mensagem = db.registrar_venda_completa(
            cliente_id=dados.get('cliente_id'),
            itens_carrinho=itens_carrinho,
            total=total_recalculado,
            forma_pagamento=dados.get('forma_pagamento', 'Dinheiro'),
            valor_pago=dados.get('valor_pago', total_recalculado),
            troco=dados.get('troco', 0)
        )
        
        if venda_id:
            return jsonify({
                'mensagem': 'Venda finalizada com sucesso!',
                'venda_id': venda_id
            })
        else:
            return jsonify({'erro': mensagem}), 400
            
    except Exception as e:
        print(f"Erro ao finalizar venda: {e}")
        return jsonify({'erro': 'Ocorreu um erro interno no servidor.'}), 500

# ==============================================================================
# 12. ROTAS DE RELATÓRIOS E EXPORTAÇÃO - NOVAS E CORRIGIDAS
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

@app.route('/exportar_excel')
@login_required
def exportar_excel():
    """Exportar relatórios para Excel - NOVA FUNÇÃO"""
    try:
        # Buscar dados
        produtos = db.listar_produtos()
        vendas = db.get_relatorio_vendas_detalhado()
        
        # Converter para DataFrame
        df_produtos = pd.DataFrame(produtos)
        df_vendas = pd.DataFrame(vendas)
        
        # Criar arquivo Excel em memória
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_produtos.to_excel(writer, sheet_name='Produtos', index=False)
            df_vendas.to_excel(writer, sheet_name='Vendas', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio_loja_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        flash(f'Erro ao exportar Excel: {str(e)}', 'error')
        return redirect('/relatorios')

@app.route('/exportar_pdf')
@login_required
def exportar_pdf():
    """Exportar relatórios para PDF - NOVA FUNÇÃO"""
    try:
        # Buscar dados
        produtos = db.listar_produtos()
        vendas = db.get_relatorio_vendas_detalhado()
        
        # Criar PDF em memória
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        
        # Título
        elements.append(Paragraph("Relatório da Loja - Mercadinho Kayr's", styles['Title']))
        elements.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Paragraph(" ", styles['Normal']))
        
        # Tabela de produtos
        if produtos:
            elements.append(Paragraph("Produtos em Estoque", styles['Heading2']))
            data = [['ID', 'Nome', 'Preço', 'Quantidade', 'Código']]
            for produto in produtos:
                data.append([
                    str(produto['id']),
                    produto['nome'],
                    f"R$ {produto['preco']:.2f}",
                    str(produto['quantidade']),
                    produto.get('codigo_barras', 'N/A')
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            elements.append(Paragraph(" ", styles['Normal']))
        
        # Tabela de vendas
        if vendas:
            elements.append(Paragraph("Histórico de Vendas", styles['Heading2']))
            data = [['ID', 'Data', 'Produto', 'Quantidade', 'Total']]
            for venda in vendas:
                data.append([
                    str(venda['id']),
                    venda['data_venda'],
                    venda['produto_nome'],
                    str(venda['quantidade']),
                    f"R$ {venda['total']:.2f}"
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'relatorio_loja_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        flash(f'Erro ao exportar PDF: {str(e)}', 'error')
        return redirect('/relatorios')

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