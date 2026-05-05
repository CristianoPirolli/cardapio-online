/* pedido_notifications.js
   Registra o service worker e subscreve Web Push para o cliente que está
   acompanhando um pedido. Depende de window.PEDIDO_PUSH_CONFIG injetado
   pelo template acompanhar.html. */

(function () {
    'use strict';

    var config = window.PEDIDO_PUSH_CONFIG || {};
    var pedidoId = config.pedidoId;
    var vapidPublicKey = config.vapidPublicKey;
    var subscribeUrl = config.subscribeUrl || '/api/pedidos/push/subscribe/';

    if (!pedidoId || !vapidPublicKey) return;
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

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

    function getCsrfToken() {
        var cookie = document.cookie.split(';').find(function (c) {
            return c.trim().startsWith('csrftoken=');
        });
        return cookie ? cookie.trim().split('=')[1] : '';
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
                tipo: 'pedido',
                pedido_id: pedidoId,
            }),
        }).catch(function (e) {
            console.error('[Pedido Push] Erro ao salvar subscription:', e);
        });
    }

    function registrarWebPush(registration) {
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
                console.error('[Pedido Push] Erro ao subscrever:', e);
            });
        });
    }

    function configurarBanner(registration) {
        var btn = document.getElementById('pedido-push-ativar');
        var banner = document.getElementById('pedido-push-banner');
        var dismiss = document.getElementById('pedido-push-dispensar');

        if (btn) {
            btn.addEventListener('click', function () {
                Notification.requestPermission().then(function (perm) {
                    if (banner) banner.classList.add('d-none');
                    if (perm === 'granted') {
                        registrarWebPush(registration);
                    }
                });
            });
        }
        if (dismiss) {
            dismiss.addEventListener('click', function () {
                if (banner) banner.classList.add('d-none');
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        navigator.serviceWorker.register('/sw.js').then(function (registration) {
            if (Notification.permission === 'granted') {
                registrarWebPush(registration);
            } else if (Notification.permission === 'default') {
                var banner = document.getElementById('pedido-push-banner');
                if (banner) banner.classList.remove('d-none');
                configurarBanner(registration);
            }
        }).catch(function (e) {
            console.error('[Pedido SW] Erro ao registrar service worker:', e);
        });
    });
})();
