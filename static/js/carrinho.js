/* =============================================================================
   static/js/carrinho.js - JavaScript para funcionalidades do carrinho

   Funções:
   - Adicionar ao carrinho via AJAX (sem recarregar página)
   - Atualizar contador do carrinho na navbar
   - Toggle de endereço de entrega no checkout
   ============================================================================= */

document.addEventListener('DOMContentLoaded', function() {

    // --- Adicionar ao carrinho via AJAX ---
    document.querySelectorAll('.form-adicionar-carrinho').forEach(function(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(form);
            const btn = form.querySelector('button[type="submit"]');
            const textoOriginal = btn.innerHTML;

            // Feedback visual
            btn.innerHTML = '<span class="loading-spinner"></span> Adicionando...';
            btn.disabled = true;

            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    btn.innerHTML = '<i class="bi bi-check-lg"></i> Adicionado!';
                    btn.classList.remove('btn-primary');
                    btn.classList.add('btn-success');

                    // Atualiza contador na navbar
                    const badge = document.getElementById('carrinho-badge');
                    if (badge) {
                        badge.textContent = data.total_itens;
                        badge.style.display = 'inline';
                    }

                    // Restaura botão após 2 segundos
                    setTimeout(function() {
                        btn.innerHTML = textoOriginal;
                        btn.classList.remove('btn-success');
                        btn.classList.add('btn-primary');
                        btn.disabled = false;
                    }, 2000);
                }
            })
            .catch(function() {
                // Fallback: submete o formulário normalmente
                form.submit();
            });
        });
    });

    // --- Toggle de endereço no checkout ---
    const radioDelivery = document.querySelectorAll('input[name="tipo_entrega"]');
    const enderecoDiv = document.getElementById('endereco-entrega-div');

    if (radioDelivery.length > 0 && enderecoDiv) {
        radioDelivery.forEach(function(radio) {
            radio.addEventListener('change', function() {
                if (this.value === 'delivery') {
                    enderecoDiv.style.display = 'block';
                } else {
                    enderecoDiv.style.display = 'none';
                }
            });
        });
    }
});
