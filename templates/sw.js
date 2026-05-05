/* Service Worker — cardapio-online
   Recebe Web Push do servidor e exibe notificação nativa do OS.
   Ao clicar na notificação, abre ou foca a URL informada no payload. */

self.addEventListener('push', function(event) {
    if (!event.data) return;

    var data = event.data.json();
    var options = {
        body: data.body || '',
        icon: '/static/img/icon-192.png',
        badge: '/static/img/badge-72.png',
        data: { url: data.url || '/' },
        requireInteraction: true,
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'Cardápio Online', options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    var targetUrl = event.notification.data.url;

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (var i = 0; i < clientList.length; i++) {
                var c = clientList[i];
                if ('focus' in c) {
                    return c.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
