"""
Integration tests for apps/pagamentos/views.py (PIX manual flow).
Test cases are added progressively by each wave.
"""
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from apps.restaurantes.models import Restaurante
from apps.pedidos.models import Pedido
from apps.pagamentos.models import Pagamento
from apps.pagamentos.services import criar_pagamento_pix_manual


# Use simple StaticFilesStorage (no manifest) during tests to avoid
# ValueError from CompressedManifestStaticFilesStorage when static files
# haven't been collected (normal in dev/CI environments).
@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)
class PixManualViewTest(TestCase):
    """Integration tests for customer-facing PIX payment views."""

    def setUp(self):
        self.client = Client()
        user = User.objects.create_user(username='viewtest', password='pass')
        self.restaurante = Restaurante.objects.create(
            proprietario=user,
            nome='Restaurante View Test',
            subdominio='viewtest',
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Cliente',
            cliente_telefone='11999999999',
            status='aguardando',
            pago=False,
            subtotal='50.00',
            taxa_entrega='5.00',
            imposto='0.00',
            total='55.00',
        )

    def test_pix_page_loads_with_pedido_id(self):
        """GET /pagamentos/<id>/ returns 200 and shows copy button (REQ-01, REQ-02)."""
        response = self.client.get(f'/pagamentos/{self.pedido.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'btn-copiar')
        self.assertContains(response, 'pix-code')

    def test_upload_page_loads(self):
        """GET /pagamentos/<id>/upload/ returns 200 with file input."""
        criar_pagamento_pix_manual(self.pedido)
        response = self.client.get(f'/pagamentos/{self.pedido.id}/upload/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')
        self.assertContains(response, 'type="file"')

    def test_upload_valid_image_sets_aguardando_confirmacao(self):
        """POST with valid jpg file transitions pedido to aguardando_confirmacao (REQ-03, REQ-05)."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        criar_pagamento_pix_manual(self.pedido)
        fake_image = SimpleUploadedFile(
            'comprovante.jpg',
            b'\xff\xd8\xff\xe0' + b'\x00' * 100,  # minimal JPEG header bytes
            content_type='image/jpeg'
        )
        response = self.client.post(
            f'/pagamentos/{self.pedido.id}/upload/',
            {'comprovante': fake_image},
        )
        self.assertEqual(response.status_code, 302)  # redirect to success
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'aguardando_confirmacao')
        self.assertFalse(self.pedido.pago)  # NOT pago yet — restaurant must accept

    def test_upload_rejects_invalid_type(self):
        """POST with .exe file returns form error without status change (REQ-07)."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        criar_pagamento_pix_manual(self.pedido)
        bad_file = SimpleUploadedFile('virus.exe', b'MZ\x90\x00', content_type='application/octet-stream')
        response = self.client.post(
            f'/pagamentos/{self.pedido.id}/upload/',
            {'comprovante': bad_file},
        )
        self.assertEqual(response.status_code, 200)  # stays on form
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'aguardando')  # unchanged

    def test_upload_rejects_file_larger_than_10mb(self):
        """POST with file >10MB returns form error without status change (REQ-13)."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        criar_pagamento_pix_manual(self.pedido)
        oversized = SimpleUploadedFile(
            'comprovante_grande.pdf',
            b'%PDF-' + b'0' * (10 * 1024 * 1024 + 1),
            content_type='application/pdf'
        )
        response = self.client.post(
            f'/pagamentos/{self.pedido.id}/upload/',
            {'comprovante': oversized},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '10 MB')
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'aguardando')
