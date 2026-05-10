from rest_framework.throttling import AnonRateThrottle


class PedidoCreateThrottle(AnonRateThrottle):
    scope = 'pedido_create'


class PagamentoCreateThrottle(AnonRateThrottle):
    scope = 'pagamento_create'
