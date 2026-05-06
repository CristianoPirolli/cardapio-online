/* painel_notifications.js
   Registra o service worker, subscreve Web Push e conecta ao PainelConsumer WebSocket.
   Depende de window.PAINEL_CONFIG injetado pelo template base_painel.html. */

(function () {
    'use strict';

    var config = window.PAINEL_CONFIG || {};
    var restauranteId = config.restauranteId;
    var vapidPublicKey = config.vapidPublicKey;
    var subscribeUrl = config.subscribeUrl || '/api/pedidos/push/subscribe/';
    var wsScheme = location.protocol === 'https:' ? 'wss' : 'ws';
    var wsUrl = wsScheme + '://' + location.host + '/ws/painel/' + restauranteId + '/';

    // -------------------------------------------------------------------------
    // Utilitários
    // -------------------------------------------------------------------------

    function urlBase64ToUint8Array(base64String) {
        var padding = '='.repeat((4 - (base64String.length % 4)) % 4);
        var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        var rawData = atob(base64);
        var outputArray = new Uint8Array(rawData.length);
        for (var i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    function mostrarToast(titulo, corpo, url) {
        var container = document.getElementById('painel-toast-container');
        if (!container) return;

        var id = 'toast-' + Date.now();
        var html = '<div id="' + id + '" class="toast align-items-center text-bg-primary border-0 mb-2" role="alert" aria-live="assertive" aria-atomic="true">'
            + '<div class="d-flex">'
            + '<div class="toast-body fw-semibold">'
            + '<i class="bi bi-bell-fill me-2"></i>' + titulo
            + '<div class="small fw-normal mt-1">' + corpo + '</div>'
            + '</div>'
            + '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>'
            + '</div></div>';

        container.insertAdjacentHTML('beforeend', html);
        var toastEl = document.getElementById(id);
        var toast = new bootstrap.Toast(toastEl, { delay: 8000 });
        toast.show();

        if (url) {
            toastEl.style.cursor = 'pointer';
            toastEl.addEventListener('click', function () { location.href = url; });
        }
    }

    function tocarSom() {
        var audio = document.getElementById('painel-alerta-som');
        if (audio) {
            audio.currentTime = 0;
            audio.play().catch(function () { /* autoplay bloqueado */ });
        }
    }

    function atualizarBadge(delta) {
        var badge = document.getElementById('painel-pedidos-badge');
        if (!badge) return;
        var atual = parseInt(badge.textContent || '0', 10);
        var novo = Math.max(0, atual + delta);
        badge.textContent = novo;
        if (novo > 0) {
            badge.classList.remove('d-none');
        }
    }

    // -------------------------------------------------------------------------
    // WebSocket — notificação instantânea enquanto o painel está aberto
    // -------------------------------------------------------------------------

    var ws = null;
    var reconnectDelay = 3000;

    function conectarWebSocket() {
        if (!restauranteId) return;
        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = function () {
                reconnectDelay = 3000;
            };

            ws.onmessage = function (event) {
                var data = JSON.parse(event.data);
                if (data.type === 'novo_pedido') {
                    tocarSom();
                    mostrarToast(data.title, data.body, data.url);
                    atualizarBadge(1);
                    // Recarrega a lista de pedidos e o dashboard automaticamente
                    var path = location.pathname;
                    if (path === '/painel/' || path === '/painel/pedidos/') {
                        setTimeout(function () { location.reload(); }, 2000);
                    }
                }
            };

            ws.onclose = function (event) {
                if (!event.wasClean) {
                    setTimeout(function () {
                        reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
                        conectarWebSocket();
                    }, reconnectDelay);
                }
            };
        } catch (e) {
            console.error('[Painel WS] Erro ao conectar:', e);
        }
    }

    // -------------------------------------------------------------------------
    // Web Push — notificação quando o navegador está fechado
    // -------------------------------------------------------------------------

    function registrarWebPush() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
        if (!vapidPublicKey) return;
        if (Notification.permission !== 'granted') return;

        navigator.serviceWorker.ready.then(function (registration) {
            registration.pushManager.getSubscription().then(function (existing) {
                if (existing) {
                    salvarSubscription(existing);
                    return;
                }
                registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
                }).then(function (subscription) {
                    salvarSubscription(subscription);
                }).catch(function (e) {
                    console.error('[Painel Push] Erro ao subscrever:', e);
                });
            });
        });
    }

    function salvarSubscription(subscription) {
        var json = subscription.toJSON();
        fetch(subscribeUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                endpoint: json.endpoint,
                keys: json.keys,
                tipo: 'painel',
                restaurante_id: restauranteId,
            }),
        }).catch(function (e) {
            console.error('[Painel Push] Erro ao salvar subscription:', e);
        });
    }

    function getCsrfToken() {
        var cookie = document.cookie.split(';').find(function (c) {
            return c.trim().startsWith('csrftoken=');
        });
        return cookie ? cookie.trim().split('=')[1] : '';
    }

    // -------------------------------------------------------------------------
    // Banner de permissão (UX: nunca pedir antes do usuário interagir)
    // -------------------------------------------------------------------------

    function exibirBannerPermissao() {
        if (!('Notification' in window)) return;
        if (Notification.permission !== 'default') return;

        var banner = document.getElementById('painel-push-banner');
        if (banner) banner.classList.remove('d-none');
    }

    function configurarBotaoBanner() {
        var btn = document.getElementById('painel-push-ativar');
        if (!btn) return;
        btn.addEventListener('click', function () {
            Notification.requestPermission().then(function (perm) {
                var banner = document.getElementById('painel-push-banner');
                if (banner) banner.classList.add('d-none');
                if (perm === 'granted') {
                    registrarWebPush();
                }
            });
        });

        var dismiss = document.getElementById('painel-push-dispensar');
        if (dismiss) {
            dismiss.addEventListener('click', function () {
                var banner = document.getElementById('painel-push-banner');
                if (banner) banner.classList.add('d-none');
            });
        }
    }

    // -------------------------------------------------------------------------
    // Inicialização
    // -------------------------------------------------------------------------

    document.addEventListener('DOMContentLoaded', function () {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').then(function () {
                if (Notification.permission === 'granted') {
                    registrarWebPush();
                }
            }).catch(function (e) {
                console.error('[Painel SW] Erro ao registrar service worker:', e);
            });
        }

        configurarBotaoBanner();
        exibirBannerPermissao();
        conectarWebSocket();
    });

    window.addEventListener('beforeunload', function () {
        if (ws) ws.close();
    });
})();
