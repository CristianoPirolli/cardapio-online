# Sistema de Notificações — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar notificações em tempo real para restaurante (novo pedido via WebSocket + Web Push) e cliente (Web Push de status + WhatsApp em entrega/pronto_retirada).

**Architecture:** Django Signals disparam um `NotificationService` centralizado. Para o restaurante: novo `PainelConsumer` WebSocket (painel aberto) + `WebPushService` via `pywebpush`/VAPID (navegador fechado). Para o cliente: Web Push de status + `WhatsAppAdapter` pluggável disparado em `entrega`/`pronto_retirada`. A infraestrutura Django Channels + Daphne já está em produção.

**Tech Stack:** Django 4.2, Django Channels 4, pywebpush, Bootstrap 5 (toast), Service Worker API, JavaScript ES6

---

## Mapa de Arquivos

### Criar
- `apps/pedidos/whatsapp.py` — `WhatsAppAdapter` interface + `LogWhatsAppAdapter` + `get_whatsapp_adapter()`
- `apps/pedidos/notifications.py` — `WebPushService` + `NotificationService`
- `apps/pedidos/signals.py` — signal `post_save` do `Pedido`
- `apps/pedidos/push_views.py` — endpoint `POST /api/push/subscribe/`
- `apps/pedidos/tests/test_notifications.py` — testes de serviços
- `apps/pedidos/tests/test_push_api.py` — testes do endpoint
- `apps/pedidos/tests/test_painel_consumer.py` — testes do WebSocket
- `templates/sw.js` — service worker (servido em `/sw.js`)
- `static/js/painel_notifications.js` — frontend do painel (WebSocket + Push)
- `static/js/pedido_notifications.js` — frontend do cliente (Push)
- `static/sounds/new_order.mp3` — som de alerta (asset manual)

### Modificar
- `requirements.txt` — adiciona `pywebpush`
- `config/settings.py` — VAPID keys + WHATSAPP_ADAPTER + SITE_URL
- `config/context_processors.py` — expõe `vapid_public_key` nos templates
- `config/urls.py` — rota `/sw.js`
- `config/routing.py` — rota WebSocket `ws/painel/<id>/`
- `apps/pedidos/models.py` — `PushSubscription` model + `Pedido.__init__`
- `apps/pedidos/consumers.py` — adiciona `PainelConsumer`
- `apps/pedidos/api_urls.py` — endpoint push subscribe
- `templates/painel/base_painel.html` — inclui `painel_notifications.js` + config JS
- `templates/pedidos/acompanhar.html` — inclui `pedido_notifications.js` + config JS

---

## Task 1: Dependência e Configurações

**Files:**
- Modify: `requirements.txt`
- Modify: `config/settings.py`

- [ ] **Step 1: Adicionar pywebpush ao requirements.txt**

Abrir `requirements.txt` e adicionar a linha após `requests==2.32.5`:

```
pywebpush==2.0.0
```

- [ ] **Step 2: Instalar a dependência**

```bash
pip install pywebpush==2.0.0
```

Expected: instalação sem erros. Dependências transitivas (`cryptography`, `http_ece`) são instaladas automaticamente.

- [ ] **Step 3: Gerar as VAPID keys**

```bash
python -c "
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
import base64

key = ec.generate_private_key(ec.SECP256R1(), default_backend())
priv_bytes = key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
pub_bytes = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
print('VAPID_PRIVATE_KEY=' + base64.urlsafe_b64encode(priv_bytes).decode().rstrip('='))
print('VAPID_PUBLIC_KEY=' + base64.urlsafe_b64encode(pub_bytes).decode().rstrip('='))
"
```

Expected: duas linhas com as chaves. Copiar os valores para o arquivo `.env`.

- [ ] **Step 4: Adicionar configurações em settings.py**

Adicionar ao final do arquivo `config/settings.py`, antes do bloco `Login/Logout URLs`:

```python
# ---------------------------------------------------------------------------
# Web Push (VAPID)
# ---------------------------------------------------------------------------
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_ADMIN_EMAIL = os.getenv('VAPID_ADMIN_EMAIL', 'admin@meusistema.com')

# ---------------------------------------------------------------------------
# WhatsApp Adapter
# ---------------------------------------------------------------------------
# Em desenvolvimento usa LogWhatsAppAdapter (só loga, não envia).
# Em produção, trocar pelo adapter do provedor desejado.
WHATSAPP_ADAPTER = os.getenv(
    'WHATSAPP_ADAPTER',
    'apps.pedidos.whatsapp.LogWhatsAppAdapter',
)
```

Verificar que `SITE_URL` já existe no settings (linha ~271): `SITE_URL = os.getenv('SITE_URL', 'http://localhost')`. Confirmar — está presente, não adicionar novamente.

- [ ] **Step 5: Adicionar VAPID_PUBLIC_KEY e WHATSAPP_ADAPTER ao .env**

No arquivo `.env` (criar se não existir), adicionar:

```
VAPID_PUBLIC_KEY=<valor gerado no Step 3>
VAPID_PRIVATE_KEY=<valor gerado no Step 3>
VAPID_ADMIN_EMAIL=seu-email@dominio.com
WHATSAPP_ADAPTER=apps.pedidos.whatsapp.LogWhatsAppAdapter
```

- [ ] **Step 6: Verificar que Django inicia sem erros**

```bash
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 7: Commit**

```bash
git add requirements.txt config/settings.py
git commit -m "chore: adiciona pywebpush e configurações VAPID + WhatsApp adapter"
```

---

## Task 2: PushSubscription Model + Pedido.__init__

**Files:**
- Modify: `apps/pedidos/models.py`
- Create: `apps/pedidos/tests/test_notifications.py` (scaffold inicial)

- [ ] **Step 1: Escrever o teste de validação do model**

Criar `apps/pedidos/tests/test_notifications.py`:

```python
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.test import TestCase
from decimal import Decimal

from apps.pedidos.models import Pedido, PushSubscription
from apps.restaurantes.models import Restaurante


class PushSubscriptionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Pizzaria Teste',
            subdominio='pizzaria-teste',
            proprietario=self.user,
            endereco='Rua A, 10',
            cidade='Cidade',
            estado='SP',
            cep='01000-000',
            telefone='11999999999',
            email='restaurante@test.com',
            taxa_entrega=Decimal('5.00'),
            pedido_minimo=Decimal('10.00'),
            taxa_imposto=Decimal('0.00'),
            ativo=True,
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='João',
            cliente_telefone='11999999999',
            status='recebido',
            pago=True,
        )

    def test_subscription_com_restaurante_e_pedido_invalida(self):
        sub = PushSubscription(
            restaurante=self.restaurante,
            pedido=self.pedido,
            endpoint='https://fcm.example.com/abc',
            p256dh='key123',
            auth='auth123',
        )
        with self.assertRaises(ValidationError):
            sub.full_clean()

    def test_subscription_sem_restaurante_e_sem_pedido_invalida(self):
        sub = PushSubscription(
            endpoint='https://fcm.example.com/abc',
            p256dh='key123',
            auth='auth123',
        )
        with self.assertRaises(ValidationError):
            sub.full_clean()

    def test_subscription_apenas_restaurante_valida(self):
        sub = PushSubscription(
            restaurante=self.restaurante,
            endpoint='https://fcm.example.com/rest',
            p256dh='key123',
            auth='auth123',
        )
        sub.full_clean()  # não deve levantar exceção

    def test_subscription_apenas_pedido_valida(self):
        sub = PushSubscription(
            pedido=self.pedido,
            endpoint='https://fcm.example.com/ped',
            p256dh='key123',
            auth='auth123',
        )
        sub.full_clean()  # não deve levantar exceção

    def test_pedido_status_anterior_snapshot(self):
        """_status_anterior é capturado no momento em que o pedido é carregado."""
        pedido_recarregado = Pedido.objects.get(pk=self.pedido.pk)
        self.assertEqual(pedido_recarregado._status_anterior, 'recebido')

    def test_pedido_status_anterior_reflete_valor_pre_mudanca(self):
        pedido_recarregado = Pedido.objects.get(pk=self.pedido.pk)
        pedido_recarregado.status = 'preparo'
        self.assertEqual(pedido_recarregado._status_anterior, 'recebido')
```

- [ ] **Step 2: Executar teste e confirmar que falha**

```bash
python manage.py test apps.pedidos.tests.test_notifications.PushSubscriptionModelTests -v 2
```

Expected: `ImportError: cannot import name 'PushSubscription' from 'apps.pedidos.models'`

- [ ] **Step 3: Adicionar PushSubscription ao models.py e __init__ ao Pedido**

No arquivo `apps/pedidos/models.py`:

**3a. Adicionar import de Restaurante no topo** (já existe, confirmar):
```python
from apps.restaurantes.models import Restaurante
```

**3b. Adicionar `__init__` ao model `Pedido`** — inserir logo após a declaração da classe `Pedido`, antes do método `normalizar_status_por_tipo_entrega` (linha ~178):

```python
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Snapshot do status no momento do carregamento.
        # Usado pelo signal post_save para detectar mudança de status
        # sem precisar de uma query extra ao banco.
        self._status_anterior = self.status
```

**3c. Adicionar o model `PushSubscription`** — inserir ao final do arquivo, após a classe `ItemPedido`:

```python

class PushSubscription(models.Model):
    """
    Armazena uma Web Push subscription de um dispositivo/browser.

    Cada subscription pertence a UM restaurante (painel) OU a UM pedido (cliente).
    Nunca os dois ao mesmo tempo — validado em clean().

    O campo endpoint é a URL única gerada pelo serviço push do browser (FCM, Mozilla, etc).
    Ele identifica unicamente um dispositivo. Quando o usuário revoga a permissão ou
    a subscription expira, o servidor recebe 404/410 ao tentar enviar e deve deletar
    este registro.
    """
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='push_subscriptions',
        verbose_name='Restaurante',
    )
    pedido = models.ForeignKey(
        'Pedido',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='push_subscriptions',
        verbose_name='Pedido',
    )
    endpoint = models.TextField(verbose_name='Endpoint')
    p256dh = models.CharField(max_length=255, verbose_name='Chave p256dh')
    auth = models.CharField(max_length=255, verbose_name='Chave auth')
    user_agent = models.CharField(max_length=255, blank=True, verbose_name='User Agent')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Push Subscription'
        verbose_name_plural = 'Push Subscriptions'

    def clean(self):
        from django.core.exceptions import ValidationError
        tem_restaurante = bool(self.restaurante_id)
        tem_pedido = bool(self.pedido_id)
        if tem_restaurante and tem_pedido:
            raise ValidationError(
                'Uma subscription não pode pertencer a restaurante e pedido ao mesmo tempo.'
            )
        if not tem_restaurante and not tem_pedido:
            raise ValidationError(
                'Uma subscription deve pertencer a um restaurante ou a um pedido.'
            )

    def __str__(self):
        if self.restaurante_id:
            return f'Push [{self.restaurante}] {self.endpoint[:50]}'
        return f'Push [Pedido #{self.pedido_id}] {self.endpoint[:50]}'
```

- [ ] **Step 4: Criar a migration**

```bash
python manage.py makemigrations pedidos --name=add_pushsubscription_and_pedido_init
```

Expected: `Migrations for 'pedidos': apps/pedidos/migrations/XXXX_add_pushsubscription_and_pedido_init.py`

- [ ] **Step 5: Aplicar a migration**

```bash
python manage.py migrate pedidos
```

Expected: `OK` sem erros.

- [ ] **Step 6: Executar testes e confirmar que passam**

```bash
python manage.py test apps.pedidos.tests.test_notifications.PushSubscriptionModelTests -v 2
```

Expected: `OK` — 6 testes passando.

- [ ] **Step 7: Commit**

```bash
git add apps/pedidos/models.py apps/pedidos/migrations/ apps/pedidos/tests/test_notifications.py
git commit -m "feat: adiciona PushSubscription model e Pedido._status_anterior snapshot"
```

---

## Task 3: WhatsApp Adapter

**Files:**
- Create: `apps/pedidos/whatsapp.py`

- [ ] **Step 1: Escrever o teste do WhatsApp adapter**

Adicionar ao final de `apps/pedidos/tests/test_notifications.py`:

```python
from apps.pedidos.whatsapp import LogWhatsAppAdapter, get_whatsapp_adapter


class WhatsAppAdapterTests(TestCase):
    def test_log_adapter_retorna_true(self):
        adapter = LogWhatsAppAdapter()
        resultado = adapter.send('11999999999', 'Mensagem de teste')
        self.assertTrue(resultado)

    def test_get_whatsapp_adapter_retorna_instancia_configurada(self):
        with self.settings(WHATSAPP_ADAPTER='apps.pedidos.whatsapp.LogWhatsAppAdapter'):
            adapter = get_whatsapp_adapter()
        self.assertIsInstance(adapter, LogWhatsAppAdapter)
```

- [ ] **Step 2: Executar e confirmar que falha**

```bash
python manage.py test apps.pedidos.tests.test_notifications.WhatsAppAdapterTests -v 2
```

Expected: `ImportError: cannot import name 'LogWhatsAppAdapter' from 'apps.pedidos.whatsapp'`

- [ ] **Step 3: Criar apps/pedidos/whatsapp.py**

```python
import logging
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class WhatsAppAdapter:
    """
    Interface base para provedores WhatsApp.

    Implementar este contrato para adicionar um novo provedor:
    - ZAPIAdapter: z-api.io
    - TwilioWhatsAppAdapter: twilio.com/whatsapp
    - MetaCloudAdapter: developers.facebook.com/docs/whatsapp

    O provedor ativo é configurado via settings.WHATSAPP_ADAPTER.
    """

    def send(self, telefone: str, mensagem: str) -> bool:
        """
        Envia mensagem WhatsApp.

        Args:
            telefone: Número do destinatário (qualquer formato BR, ex: '11999999999').
            mensagem: Texto da mensagem.

        Returns:
            True se enviado com sucesso, False caso contrário.
        """
        raise NotImplementedError


class LogWhatsAppAdapter(WhatsAppAdapter):
    """Adapter de desenvolvimento — loga a mensagem sem enviar."""

    def send(self, telefone: str, mensagem: str) -> bool:
        logger.info('[WhatsApp FAKE] Para %s: %s', telefone, mensagem)
        return True


def get_whatsapp_adapter() -> WhatsAppAdapter:
    """Retorna a instância do adapter configurado em settings.WHATSAPP_ADAPTER."""
    adapter_class = import_string(
        getattr(settings, 'WHATSAPP_ADAPTER', 'apps.pedidos.whatsapp.LogWhatsAppAdapter')
    )
    return adapter_class()
```

- [ ] **Step 4: Executar testes e confirmar que passam**

```bash
python manage.py test apps.pedidos.tests.test_notifications.WhatsAppAdapterTests -v 2
```

Expected: `OK` — 2 testes passando.

- [ ] **Step 5: Commit**

```bash
git add apps/pedidos/whatsapp.py apps/pedidos/tests/test_notifications.py
git commit -m "feat: adiciona WhatsAppAdapter interface e LogWhatsAppAdapter"
```

---

## Task 4: WebPushService + NotificationService

**Files:**
- Create: `apps/pedidos/notifications.py`

- [ ] **Step 1: Escrever os testes do NotificationService**

Adicionar ao final de `apps/pedidos/tests/test_notifications.py`:

```python
from unittest.mock import patch, MagicMock, call
from apps.pedidos.notifications import NotificationService, WebPushService
from apps.pedidos.models import PushSubscription


class WebPushServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner2', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Teste Push',
            subdominio='teste-push',
            proprietario=self.user,
            endereco='Rua B', cidade='SP', estado='SP', cep='01000-000',
            telefone='11888888888', email='push@test.com',
            taxa_entrega=Decimal('0'), pedido_minimo=Decimal('0'),
            taxa_imposto=Decimal('0'), ativo=True,
        )
        self.sub = PushSubscription.objects.create(
            restaurante=self.restaurante,
            endpoint='https://fcm.example.com/sub1',
            p256dh='pubkey123',
            auth='authkey123',
        )

    @patch('apps.pedidos.notifications.webpush')
    def test_websupport_send_retorna_true_em_sucesso(self, mock_webpush):
        mock_webpush.return_value = None
        resultado = WebPushService.send(self.sub, {'title': 'Teste', 'body': 'Corpo'})
        self.assertTrue(resultado)

    @patch('apps.pedidos.notifications.webpush')
    def test_webpush_send_deleta_subscription_em_410(self, mock_webpush):
        from pywebpush import WebPushException
        response_mock = MagicMock()
        response_mock.status_code = 410
        exc = WebPushException('Gone', response=response_mock)
        mock_webpush.side_effect = exc

        resultado = WebPushService.send(self.sub, {'title': 'Teste', 'body': 'Corpo'})

        self.assertFalse(resultado)
        self.assertFalse(PushSubscription.objects.filter(pk=self.sub.pk).exists())


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner3', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Notif Teste',
            subdominio='notif-teste',
            proprietario=self.user,
            endereco='Rua C', cidade='SP', estado='SP', cep='01000-000',
            telefone='11777777777', email='notif@test.com',
            taxa_entrega=Decimal('0'), pedido_minimo=Decimal('0'),
            taxa_imposto=Decimal('0'), ativo=True,
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Maria',
            cliente_telefone='11966666666',
            status='recebido',
            pago=True,
        )

    @patch('apps.pedidos.notifications.WebPushService.send')
    @patch('apps.pedidos.notifications.async_to_sync')
    @patch('apps.pedidos.notifications.get_channel_layer')
    def test_novo_pedido_envia_push_para_restaurante(self, mock_layer, mock_sync, mock_push):
        PushSubscription.objects.create(
            restaurante=self.restaurante,
            endpoint='https://fcm.example.com/rest1',
            p256dh='pk1', auth='ak1',
        )
        NotificationService.novo_pedido(self.pedido)
        mock_push.assert_called_once()

    @patch('apps.pedidos.notifications.WebPushService.send')
    @patch('apps.pedidos.notifications.get_whatsapp_adapter')
    @patch('apps.pedidos.notifications.async_to_sync')
    @patch('apps.pedidos.notifications.get_channel_layer')
    def test_status_mudou_envia_whatsapp_em_entrega(self, mock_layer, mock_sync, mock_wpp, mock_push):
        mock_adapter = MagicMock()
        mock_wpp.return_value = mock_adapter
        self.pedido.status = 'entrega'
        self.pedido._skip_status_validation = True
        self.pedido.save()

        NotificationService.status_mudou(self.pedido, 'preparo')

        mock_adapter.send.assert_called_once()
        args = mock_adapter.send.call_args[0]
        self.assertIn('11966666666', args[0])
        self.assertIn('saiu para entrega', args[1])

    @patch('apps.pedidos.notifications.WebPushService.send')
    @patch('apps.pedidos.notifications.get_whatsapp_adapter')
    @patch('apps.pedidos.notifications.async_to_sync')
    @patch('apps.pedidos.notifications.get_channel_layer')
    def test_status_mudou_nao_envia_whatsapp_em_preparo(self, mock_layer, mock_sync, mock_wpp, mock_push):
        mock_adapter = MagicMock()
        mock_wpp.return_value = mock_adapter
        self.pedido.status = 'preparo'
        self.pedido._skip_status_validation = True
        self.pedido.save()

        NotificationService.status_mudou(self.pedido, 'recebido')

        mock_adapter.send.assert_not_called()
```

- [ ] **Step 2: Executar e confirmar que falha**

```bash
python manage.py test apps.pedidos.tests.test_notifications.WebPushServiceTests apps.pedidos.tests.test_notifications.NotificationServiceTests -v 2
```

Expected: `ImportError: cannot import name 'NotificationService' from 'apps.pedidos.notifications'`

- [ ] **Step 3: Criar apps/pedidos/notifications.py**

```python
import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from pywebpush import webpush, WebPushException

from .whatsapp import get_whatsapp_adapter

logger = logging.getLogger(__name__)


class WebPushService:
    """Envia Web Push notifications via VAPID (pywebpush)."""

    @staticmethod
    def send(subscription, payload: dict) -> bool:
        """
        Envia uma notificação push para a subscription informada.

        Deleta automaticamente subscriptions expiradas (HTTP 404/410).
        """
        try:
            webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': {
                        'p256dh': subscription.p256dh,
                        'auth': subscription.auth,
                    },
                },
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'},
            )
            return True
        except WebPushException as exc:
            logger.error('Web Push falhou para endpoint %s: %s', subscription.endpoint[:60], exc)
            if exc.response and exc.response.status_code in (404, 410):
                subscription.delete()
            return False
        except Exception as exc:
            logger.error('Erro inesperado ao enviar Web Push: %s', exc)
            return False


class NotificationService:
    """
    Orquestra todos os canais de notificação.

    - novo_pedido: notifica o restaurante via WebSocket (painel aberto) e Web Push (offline).
    - status_mudou: notifica o cliente via Web Push + WhatsApp (só em entrega/pronto_retirada).
    """

    @classmethod
    def novo_pedido(cls, pedido):
        """Notifica o restaurante sobre um novo pedido."""
        from .models import PushSubscription

        payload = {
            'type': 'novo_pedido',
            'title': f'Novo pedido #{pedido.id}',
            'body': (
                f'{pedido.cliente_nome} — '
                f'R$ {pedido.total:.2f} — '
                f'{pedido.get_tipo_entrega_display()}'
            ),
            'url': f'/painel/pedidos/{pedido.id}/',
            'pedido_id': pedido.id,
            'cliente_nome': pedido.cliente_nome,
            'total': str(pedido.total),
            'tipo_entrega': pedido.tipo_entrega,
        }

        # WebSocket: entrega ao browser se o painel estiver aberto
        channel_layer = get_channel_layer()
        group_name = f'painel_{pedido.restaurante_id}'
        try:
            async_to_sync(channel_layer.group_send)(group_name, {
                'type': 'novo_pedido',
                **payload,
            })
        except Exception as exc:
            logger.error('Erro no channel layer para painel %s: %s', pedido.restaurante_id, exc)

        # Web Push: entrega ao browser mesmo se o painel estiver fechado
        for sub in PushSubscription.objects.filter(restaurante_id=pedido.restaurante_id):
            WebPushService.send(sub, payload)

    @classmethod
    def status_mudou(cls, pedido, status_anterior):
        """Notifica o cliente sobre mudança de status do pedido."""
        from .models import PushSubscription

        push_payload = {
            'type': 'status_update',
            'title': f'Pedido #{pedido.id} atualizado',
            'body': pedido.customer_status_display,
            'url': f'/pedidos/{pedido.id}/acompanhar/',
            'status': pedido.status,
        }

        # Web Push para o cliente (se tiver subscription registrada)
        for sub in PushSubscription.objects.filter(pedido_id=pedido.id):
            WebPushService.send(sub, push_payload)

        # WhatsApp apenas para entrega ou pronto_retirada
        if pedido.status not in ('entrega', 'pronto_retirada'):
            return
        if not pedido.cliente_telefone:
            return

        site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
        acompanhar_url = f'{site_url}/pedidos/{pedido.id}/acompanhar/'

        if pedido.status == 'entrega':
            mensagem = (
                f'Olá {pedido.cliente_nome}! Seu pedido #{pedido.id} '
                f'saiu para entrega. Acompanhe em: {acompanhar_url}'
            )
        else:
            mensagem = (
                f'Olá {pedido.cliente_nome}! Seu pedido #{pedido.id} '
                f'está pronto para retirada. Acompanhe em: {acompanhar_url}'
            )

        try:
            adapter = get_whatsapp_adapter()
            adapter.send(pedido.cliente_telefone, mensagem)
        except Exception as exc:
            logger.error('Erro ao enviar WhatsApp para pedido %s: %s', pedido.id, exc)
```

- [ ] **Step 4: Executar testes e confirmar que passam**

```bash
python manage.py test apps.pedidos.tests.test_notifications -v 2
```

Expected: `OK` — todos os testes passando.

- [ ] **Step 5: Commit**

```bash
git add apps/pedidos/notifications.py apps/pedidos/tests/test_notifications.py
git commit -m "feat: adiciona WebPushService e NotificationService"
```

---

## Task 5: Django Signals

**Files:**
- Create: `apps/pedidos/signals.py`
- Create: `apps/pedidos/tests/test_signals.py`

Nota: `apps/pedidos/apps.py` já importa `apps.pedidos.signals` em `ready()` — não precisa ser modificado.

- [ ] **Step 1: Escrever os testes de signals**

Criar `apps/pedidos/tests/test_signals.py`:

```python
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


class PedidoSignalsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sig_owner', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Sig Restaurante',
            subdominio='sig-rest',
            proprietario=self.user,
            endereco='Rua D', cidade='SP', estado='SP', cep='01000-000',
            telefone='11555555555', email='sig@test.com',
            taxa_entrega=Decimal('0'), pedido_minimo=Decimal('0'),
            taxa_imposto=Decimal('0'), ativo=True,
        )

    @patch('apps.pedidos.signals.NotificationService.novo_pedido')
    def test_signal_dispara_novo_pedido_ao_criar(self, mock_novo):
        Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Teste',
            cliente_telefone='11999999999',
            status='recebido',
            pago=True,
        )
        mock_novo.assert_called_once()

    @patch('apps.pedidos.signals.NotificationService.status_mudou')
    def test_signal_dispara_status_mudou_ao_alterar_status(self, mock_mudou):
        pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Teste2',
            cliente_telefone='11999999998',
            status='recebido',
            pago=True,
        )
        pedido_recarregado = Pedido.objects.get(pk=pedido.pk)
        pedido_recarregado.status = 'preparo'
        pedido_recarregado._skip_status_validation = True
        pedido_recarregado.save()

        mock_mudou.assert_called_once_with(pedido_recarregado, 'recebido')

    @patch('apps.pedidos.signals.NotificationService.status_mudou')
    def test_signal_nao_dispara_se_status_nao_mudou(self, mock_mudou):
        pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Teste3',
            cliente_telefone='11999999997',
            status='recebido',
            pago=True,
        )
        pedido_recarregado = Pedido.objects.get(pk=pedido.pk)
        pedido_recarregado.observacoes = 'Atualizado'
        pedido_recarregado.save()

        mock_mudou.assert_not_called()
```

- [ ] **Step 2: Executar e confirmar que falha**

```bash
python manage.py test apps.pedidos.tests.test_signals -v 2
```

Expected: erro indicando que `NotificationService` não é chamado (signals.py ainda não existe ou está vazio).

- [ ] **Step 3: Criar apps/pedidos/signals.py**

```python
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Pedido
from .notifications import NotificationService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Pedido)
def pedido_salvo(sender, instance, created, **kwargs):
    """
    Dispara notificações quando um pedido é criado ou tem seu status alterado.

    Detecta mudança de status comparando instance.status com instance._status_anterior,
    que é capturado no __init__ do model sem query extra.
    """
    try:
        if created:
            NotificationService.novo_pedido(instance)
        elif hasattr(instance, '_status_anterior') and instance._status_anterior != instance.status:
            NotificationService.status_mudou(instance, instance._status_anterior)
    except Exception as exc:
        logger.error('Erro ao processar notificação para pedido %s: %s', instance.pk, exc)
```

- [ ] **Step 4: Executar testes e confirmar que passam**

```bash
python manage.py test apps.pedidos.tests.test_signals -v 2
```

Expected: `OK` — 3 testes passando.

- [ ] **Step 5: Commit**

```bash
git add apps/pedidos/signals.py apps/pedidos/tests/test_signals.py
git commit -m "feat: adiciona signal post_save para disparar notificações de pedido"
```

---

## Task 6: PainelConsumer + Routing

**Files:**
- Modify: `apps/pedidos/consumers.py`
- Modify: `config/routing.py`
- Create: `apps/pedidos/tests/test_painel_consumer.py`

- [ ] **Step 1: Escrever o teste do PainelConsumer**

Criar `apps/pedidos/tests/test_painel_consumer.py`:

```python
import json
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async, async_to_sync
from django.test import TestCase, override_settings

from apps.pedidos.consumers import PainelConsumer


@override_settings(CHANNEL_LAYERS={
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
})
class PainelConsumerTests(TestCase):

    async def _connect(self, restaurante_id):
        app = PainelConsumer.as_asgi()
        communicator = WebsocketCommunicator(app, f'/ws/painel/{restaurante_id}/')
        communicator.scope['url_route'] = {'kwargs': {'restaurante_id': str(restaurante_id)}}
        connected, _ = await communicator.connect()
        return communicator, connected

    def test_consumer_aceita_conexao(self):
        async def run():
            communicator, connected = await self._connect(1)
            self.assertTrue(connected)
            await communicator.disconnect()
        async_to_sync(run)()

    def test_consumer_recebe_evento_novo_pedido(self):
        async def run():
            communicator, _ = await self._connect(1)
            channel_layer = get_channel_layer()
            await channel_layer.group_send('painel_1', {
                'type': 'novo_pedido',
                'title': 'Novo pedido #99',
                'body': 'Cliente — R$ 50,00',
                'url': '/painel/pedidos/99/',
                'pedido_id': 99,
                'cliente_nome': 'Cliente',
                'total': '50.00',
                'tipo_entrega': 'delivery',
            })
            response = await communicator.receive_json_from(timeout=3)
            self.assertEqual(response['type'], 'novo_pedido')
            self.assertEqual(response['pedido_id'], 99)
            await communicator.disconnect()
        async_to_sync(run)()
```

- [ ] **Step 2: Executar e confirmar que falha**

```bash
python manage.py test apps.pedidos.tests.test_painel_consumer -v 2
```

Expected: `ImportError: cannot import name 'PainelConsumer' from 'apps.pedidos.consumers'`

- [ ] **Step 3: Adicionar PainelConsumer ao consumers.py**

Abrir `apps/pedidos/consumers.py` e adicionar após a classe `PedidoStatusConsumer` (ao final do arquivo):

```python


class PainelConsumer(AsyncWebsocketConsumer):
    """
    WebSocket do painel do restaurante.

    Restaurante conecta em: ws://host/ws/painel/{restaurante_id}/
    Grupo de broadcast: 'painel_{restaurante_id}'

    Eventos recebidos:
    - novo_pedido: novo pedido criado no restaurante
    """

    async def connect(self):
        self.restaurante_id = self.scope['url_route']['kwargs']['restaurante_id']
        self.group_name = f'painel_{self.restaurante_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def novo_pedido(self, event):
        """Recebe evento do NotificationService e repassa ao browser."""
        await self.send(text_data=json.dumps(event))
```

- [ ] **Step 4: Adicionar rota WebSocket em config/routing.py**

O arquivo `config/routing.py` atual tem:
```python
from django.urls import re_path
from apps.pedidos.consumers import PedidoStatusConsumer

websocket_urlpatterns = [
    re_path(r'ws/pedidos/(?P<pedido_id>\d+)/status/$', PedidoStatusConsumer.as_asgi()),
]
```

Substituir por:
```python
from django.urls import re_path
from apps.pedidos.consumers import PedidoStatusConsumer, PainelConsumer

websocket_urlpatterns = [
    re_path(r'ws/pedidos/(?P<pedido_id>\d+)/status/$', PedidoStatusConsumer.as_asgi()),
    re_path(r'ws/painel/(?P<restaurante_id>\d+)/$', PainelConsumer.as_asgi()),
]
```

- [ ] **Step 5: Executar testes e confirmar que passam**

```bash
python manage.py test apps.pedidos.tests.test_painel_consumer -v 2
```

Expected: `OK` — 2 testes passando.

- [ ] **Step 6: Commit**

```bash
git add apps/pedidos/consumers.py config/routing.py apps/pedidos/tests/test_painel_consumer.py
git commit -m "feat: adiciona PainelConsumer WebSocket para notificações do painel"
```

---

## Task 7: Push Subscribe API Endpoint

**Files:**
- Create: `apps/pedidos/push_views.py`
- Create: `apps/pedidos/tests/test_push_api.py`
- Modify: `apps/pedidos/api_urls.py`

- [ ] **Step 1: Escrever os testes do endpoint**

Criar `apps/pedidos/tests/test_push_api.py`:

```python
import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.pedidos.models import Pedido, PushSubscription
from apps.restaurantes.models import Restaurante


VALID_SUBSCRIPTION = {
    'endpoint': 'https://fcm.googleapis.com/fcm/send/abc123',
    'keys': {
        'p256dh': 'pubkeyabc',
        'auth': 'authkeyabc',
    },
}


class PushSubscribeAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='api_owner', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='API Restaurante',
            subdominio='api-rest',
            proprietario=self.user,
            endereco='Rua E', cidade='SP', estado='SP', cep='01000-000',
            telefone='11444444444', email='api@test.com',
            taxa_entrega=Decimal('0'), pedido_minimo=Decimal('0'),
            taxa_imposto=Decimal('0'), ativo=True,
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='API Cliente',
            cliente_telefone='11333333333',
            status='recebido',
            pago=True,
        )

    def _post(self, data):
        return self.client.post(
            '/api/pedidos/push/subscribe/',
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_subscribe_painel_cria_subscription(self):
        data = {**VALID_SUBSCRIPTION, 'tipo': 'painel', 'restaurante_id': self.restaurante.id}
        response = self._post(data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            PushSubscription.objects.filter(
                restaurante=self.restaurante,
                endpoint=VALID_SUBSCRIPTION['endpoint'],
            ).exists()
        )

    def test_subscribe_pedido_cria_subscription(self):
        data = {**VALID_SUBSCRIPTION, 'tipo': 'pedido', 'pedido_id': self.pedido.id}
        response = self._post(data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            PushSubscription.objects.filter(
                pedido=self.pedido,
                endpoint=VALID_SUBSCRIPTION['endpoint'],
            ).exists()
        )

    def test_subscribe_sem_endpoint_retorna_400(self):
        data = {'tipo': 'painel', 'restaurante_id': self.restaurante.id, 'keys': {'p256dh': 'k', 'auth': 'a'}}
        response = self._post(data)
        self.assertEqual(response.status_code, 400)

    def test_subscribe_tipo_invalido_retorna_400(self):
        data = {**VALID_SUBSCRIPTION, 'tipo': 'invalido'}
        response = self._post(data)
        self.assertEqual(response.status_code, 400)

    def test_subscribe_idempotente_atualiza_sem_duplicar(self):
        data = {**VALID_SUBSCRIPTION, 'tipo': 'painel', 'restaurante_id': self.restaurante.id}
        self._post(data)
        self._post(data)  # segunda vez com mesmo endpoint
        count = PushSubscription.objects.filter(
            restaurante=self.restaurante,
            endpoint=VALID_SUBSCRIPTION['endpoint'],
        ).count()
        self.assertEqual(count, 1)
```

- [ ] **Step 2: Executar e confirmar que falha**

```bash
python manage.py test apps.pedidos.tests.test_push_api -v 2
```

Expected: erro 404 (URL não encontrada).

- [ ] **Step 3: Criar apps/pedidos/push_views.py**

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import PushSubscription


@api_view(['POST'])
@permission_classes([AllowAny])
def push_subscribe(request):
    """
    Registra ou atualiza uma Web Push subscription.

    Body JSON:
    {
        "endpoint": "https://fcm.googleapis.com/...",
        "keys": {"p256dh": "...", "auth": "..."},
        "tipo": "painel" | "pedido",
        "restaurante_id": 5,   // obrigatório se tipo == "painel"
        "pedido_id": 42        // obrigatório se tipo == "pedido"
    }
    """
    data = request.data
    endpoint = data.get('endpoint')
    keys = data.get('keys') or {}
    tipo = data.get('tipo')

    if not endpoint or not keys.get('p256dh') or not keys.get('auth'):
        return Response(
            {'error': 'endpoint, keys.p256dh e keys.auth são obrigatórios'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    defaults = {
        'p256dh': keys['p256dh'],
        'auth': keys['auth'],
        'user_agent': (request.META.get('HTTP_USER_AGENT') or '')[:255],
    }

    if tipo == 'painel':
        restaurante_id = data.get('restaurante_id')
        if not restaurante_id:
            return Response(
                {'error': 'restaurante_id é obrigatório para tipo painel'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.restaurantes.models import Restaurante
        try:
            restaurante = Restaurante.objects.get(id=restaurante_id)
        except Restaurante.DoesNotExist:
            return Response({'error': 'Restaurante não encontrado'}, status=status.HTTP_404_NOT_FOUND)

        PushSubscription.objects.update_or_create(
            restaurante=restaurante,
            endpoint=endpoint,
            defaults=defaults,
        )

    elif tipo == 'pedido':
        pedido_id = data.get('pedido_id')
        if not pedido_id:
            return Response(
                {'error': 'pedido_id é obrigatório para tipo pedido'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import Pedido
        try:
            pedido = Pedido.objects.get(id=pedido_id)
        except Pedido.DoesNotExist:
            return Response({'error': 'Pedido não encontrado'}, status=status.HTTP_404_NOT_FOUND)

        PushSubscription.objects.update_or_create(
            pedido=pedido,
            endpoint=endpoint,
            defaults=defaults,
        )

    else:
        return Response(
            {'error': 'tipo deve ser "painel" ou "pedido"'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)
```

- [ ] **Step 4: Registrar a URL em api_urls.py**

Substituir o conteúdo de `apps/pedidos/api_urls.py`:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import PedidoViewSet
from .push_views import push_subscribe

router = DefaultRouter()
router.register('', PedidoViewSet, basename='pedido')

urlpatterns = [
    path('push/subscribe/', push_subscribe, name='push_subscribe'),
    path('', include(router.urls)),
]
```

- [ ] **Step 5: Executar testes e confirmar que passam**

```bash
python manage.py test apps.pedidos.tests.test_push_api -v 2
```

Expected: `OK` — 5 testes passando.

- [ ] **Step 6: Commit**

```bash
git add apps/pedidos/push_views.py apps/pedidos/api_urls.py apps/pedidos/tests/test_push_api.py
git commit -m "feat: adiciona endpoint POST /api/pedidos/push/subscribe/"
```

---

## Task 8: Service Worker

**Files:**
- Create: `templates/sw.js`
- Modify: `config/urls.py`
- Modify: `config/context_processors.py`

O service worker deve ser servido do caminho `/sw.js` (raiz do domínio) para ter escopo global.
A abordagem usada é um template Django servido como JavaScript — simples e sem dependências extras.

- [ ] **Step 1: Criar templates/sw.js**

```javascript
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
```

- [ ] **Step 2: Adicionar rota /sw.js em config/urls.py**

No arquivo `config/urls.py`, adicionar o import:
```python
from django.views.generic import TemplateView
```

E adicionar ao final de `urlpatterns` (antes do bloco `if settings.DEBUG`):
```python
    path('sw.js', TemplateView.as_view(
        template_name='sw.js',
        content_type='application/javascript',
    ), name='service_worker'),
```

- [ ] **Step 3: Adicionar vapid_public_key ao context processor**

No arquivo `config/context_processors.py`, localizar o `return` final e adicionar `vapid_public_key`:

```python
    return {
        'estabelecimento_atual': tenant,
        'restaurante_atual': tenant,
        'carrinho_total_itens': total_itens,
        'painel_pedidos_abertos_count': pedidos_abertos_count,
        'aguardando_confirmacao_count': aguardando_confirmacao_count,
        'base_domain': settings.BASE_DOMAIN,
        'vapid_public_key': getattr(settings, 'VAPID_PUBLIC_KEY', ''),
    }
```

- [ ] **Step 4: Verificar que /sw.js responde corretamente**

```bash
python manage.py runserver
```

Em outro terminal:
```bash
curl -s http://localhost:8000/sw.js | head -5
```

Expected: primeiras linhas do service worker (`/* Service Worker — cardapio-online`).

- [ ] **Step 5: Commit**

```bash
git add templates/sw.js config/urls.py config/context_processors.py
git commit -m "feat: adiciona service worker em /sw.js e vapid_public_key no contexto"
```

---

## Task 9: Painel Frontend — WebSocket + Web Push

**Files:**
- Create: `static/js/painel_notifications.js`
- Modify: `templates/painel/base_painel.html`

- [ ] **Step 1: Criar static/js/painel_notifications.js**

```javascript
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
        // Registra service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').then(function () {
                // Se já tem permissão, garante que está subscrito
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
```

- [ ] **Step 2: Atualizar templates/painel/base_painel.html**

No arquivo `templates/painel/base_painel.html`, localizar a linha que contém `{% block extra_js %}` (linha 74) e inserir **antes** dela:

```html
<!-- Container de toasts para notificações de novos pedidos -->
<div id="painel-toast-container"
     class="toast-container position-fixed bottom-0 end-0 p-3"
     style="z-index: 1100;"></div>

<!-- Som de alerta para novo pedido -->
<audio id="painel-alerta-som" preload="auto">
    <source src="{% static 'sounds/new_order.mp3' %}" type="audio/mpeg">
</audio>

<!-- Banner de permissão Web Push (escondido até ser necessário) -->
<div id="painel-push-banner" class="alert alert-info alert-dismissible d-none m-3" role="alert">
    <i class="bi bi-bell me-2"></i>
    <strong>Ativar notificações de pedidos?</strong>
    Você será notificado mesmo com o navegador fechado.
    <div class="mt-2">
        <button id="painel-push-ativar" type="button" class="btn btn-sm btn-primary me-2">Ativar</button>
        <button id="painel-push-dispensar" type="button" class="btn btn-sm btn-outline-secondary">Agora não</button>
    </div>
</div>
```

Ainda no mesmo arquivo, localizar o final do `{% block extra_js %}` (antes de `{% endblock %}`) e adicionar após o script inline existente:

```html
<script>
window.PAINEL_CONFIG = {
    restauranteId: {{ restaurante_atual.id|default:0 }},
    vapidPublicKey: "{{ vapid_public_key }}",
    subscribeUrl: "{% url 'push_subscribe' %}"
};
</script>
<script src="{% static 'js/painel_notifications.js' %}"></script>
```

Nota: o script inline existente com polling (`__painelPedidosBadgePolling`) permanece intacto — o WebSocket é adicional.

- [ ] **Step 3: Adicionar arquivo de som (asset manual)**

Baixar um arquivo de som curto e livre de royalties (ex: beep de 1 segundo) e salvar em:
```
static/sounds/new_order.mp3
```

Opção gratuita: https://freesound.org (pesquisar "notification beep" com licença CC0).

- [ ] **Step 4: Verificar no navegador**

```bash
python manage.py runserver
```

1. Abrir o painel do restaurante em `http://localhost:8000/painel/`
2. Confirmar que o banner "Ativar notificações de pedidos?" aparece
3. Clicar em "Ativar" e conceder permissão
4. Verificar no DevTools → Application → Service Workers que o SW está registrado
5. Verificar no DevTools → Application → Push Messages que há uma subscription

- [ ] **Step 5: Commit**

```bash
git add static/js/painel_notifications.js templates/painel/base_painel.html static/sounds/
git commit -m "feat: adiciona WebSocket + Web Push no painel do restaurante"
```

---

## Task 10: Cliente Frontend — Web Push

**Files:**
- Create: `static/js/pedido_notifications.js`
- Modify: `templates/pedidos/acompanhar.html`

- [ ] **Step 1: Criar static/js/pedido_notifications.js**

```javascript
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
```

- [ ] **Step 2: Atualizar templates/pedidos/acompanhar.html**

No arquivo `templates/pedidos/acompanhar.html`, localizar a linha com `{% if not pedido.customer_status_terminal %}` próxima ao final (linha ~425) — o bloco que exibe "Conectado em tempo real".

Inserir **antes** desse bloco, ainda dentro do `<div class="col-lg-10">`:

```html
{% if not pedido.customer_status_terminal %}
<!-- Banner de permissão Web Push para o cliente -->
<div id="pedido-push-banner" class="alert alert-info alert-dismissible d-none mt-3" role="alert">
    <i class="bi bi-bell me-2"></i>
    <strong>Receber notificações deste pedido?</strong>
    Você será avisado mesmo se fechar esta página.
    <div class="mt-2">
        <button id="pedido-push-ativar" type="button" class="btn btn-sm btn-primary me-2">Ativar</button>
        <button id="pedido-push-dispensar" type="button" class="btn btn-sm btn-outline-secondary">Agora não</button>
    </div>
</div>
{% endif %}
```

No bloco `{% block extra_js %}` ao final do arquivo (após o script WebSocket existente), adicionar:

```html
{% if not pedido.customer_status_terminal %}
<script>
window.PEDIDO_PUSH_CONFIG = {
    pedidoId: {{ pedido.id }},
    vapidPublicKey: "{{ vapid_public_key }}",
    subscribeUrl: "{% url 'push_subscribe' %}"
};
</script>
<script src="{% static 'js/pedido_notifications.js' %}"></script>
{% endif %}
```

- [ ] **Step 3: Verificar no navegador**

```bash
python manage.py runserver
```

1. Criar um pedido de teste pelo cardápio
2. Abrir a página `/pedidos/{id}/acompanhar/`
3. Confirmar que o banner "Receber notificações deste pedido?" aparece
4. Clicar "Ativar" e conceder permissão
5. Verificar no DevTools → Application → Push Messages que há uma subscription

- [ ] **Step 4: Executar todos os testes**

```bash
python manage.py test apps.pedidos.tests -v 2
```

Expected: todos os testes passando sem erros.

- [ ] **Step 5: Commit final**

```bash
git add static/js/pedido_notifications.js templates/pedidos/acompanhar.html
git commit -m "feat: adiciona Web Push para cliente na página de acompanhamento"
```

---

## Resumo de Execução

| Task | Entrega |
|---|---|
| 1 | pywebpush instalado, VAPID keys geradas, settings configurado |
| 2 | PushSubscription model + Pedido._status_anterior |
| 3 | WhatsAppAdapter interface pluggável |
| 4 | NotificationService + WebPushService |
| 5 | Signal post_save dispara notificações |
| 6 | PainelConsumer WebSocket ativo |
| 7 | POST /api/pedidos/push/subscribe/ |
| 8 | Service worker em /sw.js + vapid_public_key no contexto |
| 9 | Painel recebe notificação instantânea (WS) e offline (Push) |
| 10 | Cliente recebe push ao fechar a aba de acompanhamento |

**Para implementar WhatsApp real:** criar uma classe que estenda `WhatsAppAdapter`, implementar `send()` com o SDK do provedor escolhido, e alterar `WHATSAPP_ADAPTER` no `.env`.
