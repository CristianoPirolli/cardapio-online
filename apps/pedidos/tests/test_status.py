"""
Unit tests for BFS status graph in apps/core/algorithms.py
and Pedido.validar_transicao_status().
"""
from django.test import TestCase
from apps.core.algorithms import GRAFO_STATUS_PEDIDO, bfs_caminho_mais_curto


class StatusGraphTest(TestCase):
    """Tests for the BFS status graph transitions."""

    def test_aguardando_goes_to_aguardando_confirmacao(self):
        """aguardando -> aguardando_confirmacao must be a direct valid transition."""
        self.assertIn(
            'aguardando_confirmacao',
            GRAFO_STATUS_PEDIDO['aguardando']
        )

    def test_aguardando_confirmacao_goes_to_recebido(self):
        """aguardando_confirmacao -> recebido must be a direct valid transition."""
        self.assertIn(
            'recebido',
            GRAFO_STATUS_PEDIDO['aguardando_confirmacao']
        )

    def test_aguardando_confirmacao_goes_to_cancelado(self):
        """aguardando_confirmacao -> cancelado must be a direct valid transition."""
        self.assertIn(
            'cancelado',
            GRAFO_STATUS_PEDIDO['aguardando_confirmacao']
        )

    def test_aguardando_does_not_go_directly_to_recebido(self):
        """aguardando should no longer transition directly to recebido."""
        self.assertNotIn('recebido', GRAFO_STATUS_PEDIDO['aguardando'])

    def test_bfs_can_reach_concluido_from_aguardando_confirmacao(self):
        """BFS finds a path from aguardando_confirmacao to concluido."""
        path = bfs_caminho_mais_curto(
            GRAFO_STATUS_PEDIDO, 'aguardando_confirmacao', 'concluido'
        )
        self.assertTrue(len(path) > 0)
