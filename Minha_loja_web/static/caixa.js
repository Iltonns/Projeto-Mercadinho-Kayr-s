// Aguarda o documento HTML carregar completamente
document.addEventListener('DOMContentLoaded', () => {

    // Seleciona os elementos importantes da página
    const campoBusca = document.getElementById('busca-produto');
    const corpoTabelaCarrinho = document.getElementById('carrinho-itens');
    const spanValorTotal = document.getElementById('valor-total');
    const btnFinalizar = document.getElementById('btn-finalizar-venda');
    const campoValorPago = document.getElementById('valor-pago');
    const spanValorTroco = document.getElementById('valor-troco');
    const selectFormaPagamento = document.getElementById('forma-pagamento');

    let carrinho = []; // Array para guardar os produtos do carrinho

    // Fica "ouvindo" o que é digitado no campo de busca
    campoBusca.addEventListener('keypress', async (event) => {
        if (event.key === 'Enter') {
            event.preventDefault(); // Impede o formulário de ser enviado
            const codigo = campoBusca.value.trim();
            if (codigo) {
                // Chama a API do Flask para buscar o produto
                const response = await fetch(`/api/buscar_produto/${codigo}`);
                if (response.ok) {
                    const produto = await response.json();
                    adicionarAoCarrinho(produto);
                } else {
                    alert('Produto não encontrado!');
                }
                campoBusca.value = ''; // Limpa o campo de busca
            }
        }
    });

    function adicionarAoCarrinho(produto) {
        // Verifica se o produto já está no carrinho
        const itemExistente = carrinho.find(item => item.id === produto.id);

        if (itemExistente) {
            itemExistente.quantidade++;
        } else {
            carrinho.push({ ...produto, quantidade: 1 });
        }
        atualizarCarrinho();
    }
    
    function atualizarCarrinho() {
        corpoTabelaCarrinho.innerHTML = ''; // Limpa a tabela
        let total = 0;
        
        carrinho.forEach((item, index) => {
            const subtotal = item.quantidade * item.preco;
            total += subtotal;

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${item.nome}</td>
                <td>${item.quantidade}</td>
                <td>R$ ${item.preco.toFixed(2)}</td>
                <td>R$ ${subtotal.toFixed(2)}</td>
                <td><button class="btn btn-danger btn-sm" data-index="${index}">Remover</button></td>
            `;
            corpoTabelaCarrinho.appendChild(tr);
        });

        spanValorTotal.textContent = total.toFixed(2);
        calcularTroco();
    }
    
    // Delegação de evento para o botão remover
    corpoTabelaCarrinho.addEventListener('click', (event) => {
        if (event.target.classList.contains('btn-danger')) {
            const index = event.target.dataset.index;
            carrinho.splice(index, 1); // Remove o item do array
            atualizarCarrinho();
        }
    });

    // Lógica de Pagamento
    selectFormaPagamento.addEventListener('change', calcularTroco);
    campoValorPago.addEventListener('input', calcularTroco);
    
    function calcularTroco() {
        const total = parseFloat(spanValorTotal.textContent);
        const pago = parseFloat(campoValorPago.value) || 0;
        
        // Só mostra o campo de valor pago se for dinheiro
        document.getElementById('campo-valor-pago').style.display = selectFormaPagamento.value === 'dinheiro' ? 'block' : 'none';

        let troco = 0;
        if (selectFormaPagamento.value === 'dinheiro' && pago >= total) {
            troco = pago - total;
        }
        spanValorTroco.textContent = troco.toFixed(2);
    }

    // Finalizar a venda
    btnFinalizar.addEventListener('click', async () => {
        if (carrinho.length === 0) {
            alert('Carrinho está vazio!');
            return;
        }

        const dadosVenda = {
            cliente_id: null, // Adicionar um campo para cliente se desejar
            total: parseFloat(spanValorTotal.textContent),
            forma_pagamento: selectFormaPagamento.value,
            valor_pago: parseFloat(campoValorPago.value) || 0,
            troco: parseFloat(spanValorTroco.textContent) || 0,
            itens: carrinho.map(item => ({ id: item.id, qtd: item.quantidade }))
        };

        const response = await fetch('/caixa/finalizar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(dadosVenda),
        });

        if (response.ok) {
            const resultado = await response.json();
            alert(resultado.mensagem);
            carrinho = []; // Limpa o carrinho
            atualizarCarrinho();
        } else {
            alert('Erro ao finalizar a venda.');
        }
    });
});