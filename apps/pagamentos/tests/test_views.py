"""
Integration tests for apps/pagamentos/views.py (PIX manual flow).
Test cases are added progressively by each wave.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.restaurantes.models import Restaurante
from apps.pedidos.models import Pedido
from apps.pagamentos.models import Pagamento
