"""
Unit tests for BFS status graph in apps/core/algorithms.py
and Pedido.validar_transicao_status().
"""
from django.test import TestCase
from apps.core.algorithms import GRAFO_STATUS_PEDIDO, bfs_caminho_mais_curto
