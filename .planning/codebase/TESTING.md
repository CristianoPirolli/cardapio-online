# Testing Patterns

**Analysis Date:** 2026-04-02

## Test Framework

**Runner:**
- Django's built-in test runner (`django.test.TestCase`)
- No pytest, no pytest-django — the project uses `manage.py test` directly
- No `pytest.ini`, `setup.cfg`, or `tox.ini` present

**Assertion Library:**
- `unittest` / `django.test.TestCase` assertions (`assertEqual`, `assertRaises`, `assertIsNotNone`)

**Run Commands:**
```bash
python manage.py test                          # Run all tests
python manage.py test apps.pagamentos          # Run tests for one app
python manage.py test apps.pedidos.tests.test_services  # Run specific test file
```

No coverage tooling is configured. No `coverage.py` entry in `requirements.txt`.

## Test File Organization

**Location:** Tests live in a dedicated `tests/` subdirectory within each app (not co-located).

**Structure:**
```
apps/
├── pagamentos/
│   └── tests/
│       ├── __init__.py
│       └── test_services.py
└── pedidos/
    └── tests/
        ├── __init__.py
        └── test_services.py
```

**Naming:**
- Test files: `test_{module}.py` (e.g., `test_services.py`)
- Test classes: `{Feature}Tests` in PascalCase (e.g., `PagamentoMockTests`, `PedidoServicesTests`)
- Test methods: `test_{what_is_being_tested}` in snake_case

## Test Files Present

| File | Tests | What it tests |
|---|---|---|
| `apps/pagamentos/tests/test_services.py` | 6 | Payment service functions (mock + Stripe gateway) |
| `apps/pedidos/tests/test_services.py` | 3 | Order checkout service functions |

**Total: 2 test files, 9 test cases.**

No tests exist for:
- `apps/restaurantes/` (models, views, auth, admin)
- `apps/produtos/` (models, views, admin)
- Any view layer (HTML views or DRF API views)
- Middleware (`config/middleware.py`)
- Admin actions
- URL routing
- Template rendering

## Test Class Structure

Each test file uses one or more `TestCase` subclasses, each with a `setUp` method that
builds the full object graph from scratch:

```python
class PagamentoMockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner_pag', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Restaurante Pagamentos',
            subdominio='restaurante-pagamentos',
            proprietario=self.user,
            # ... all required fields with explicit values
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Cliente Teste',
            # ...
        )
```

Pattern:
- No factories or fixtures — all objects created inline with `Model.objects.create()`
- All required fields provided explicitly (no reliance on model defaults)
- Each class has its own `setUp`, even if the setup is nearly identical to another class
- `refresh_from_db()` called explicitly after service calls to verify DB state

## Mocking

**Framework:** `unittest.mock` (`patch`, `MagicMock`)

**Pattern:**
```python
@override_settings(PAYMENT_GATEWAY='stripe', STRIPE_SECRET_KEY='sk_test_fake123')
@patch('apps.pagamentos.services.stripe.checkout.Session.create')
def test_criar_pagamento_stripe_card(self, mock_create):
    mock_session = MagicMock()
    mock_session.id = 'cs_test_abc123'
    mock_session.url = 'https://checkout.stripe.com/pay/cs_test_abc123'
    mock_create.return_value = mock_session

    resultado = criar_pagamento(self.pedido, metodo='card')

    call_kwargs = mock_create.call_args[1]
    self.assertEqual(call_kwargs['payment_method_types'], ['card'])
```

- External API calls (Stripe, Mercado Pago) are always mocked — no real API calls in tests
- Settings overridden per-test with `@override_settings`
- Mock targets use full dotted path to the import site (e.g., `apps.pagamentos.services.stripe...`)
- `MagicMock` used for complex response objects; attributes set directly

## What Is Tested

### `apps/pagamentos/tests/test_services.py`

**`PagamentoMockTests`** (3 tests):
- `test_criar_pagamento_mock`: creates a mock `Pagamento` with status `pendente`, correct gateway and value
- `test_confirmar_pagamento_mock`: confirms mock payment, sets `status='aprovado'`, marks `pedido.pago=True` and `status='recebido'`
- `test_criar_pagamento_idempotente`: calling `criar_pagamento` twice for the same pedido returns the same `Pagamento` instance

**`PagamentoStripeTests`** (5 tests → note: file references `stripe` but current models show `mercadopago`; tests still import old `stripe` paths):
- `test_criar_pagamento_stripe_card`: Stripe checkout session created, URL returned, correct `payment_method_types`
- `test_criar_pagamento_stripe_pix`: PIX method creates session with PIX payment type and options
- `test_trocar_metodo_cancela_antigo`: switching payment method marks old `Pagamento` as `recusado` and creates a new one
- `test_confirmar_pagamento_stripe`: confirming approved Stripe session sets payment `aprovado`, marks `pedido.pago`
- `test_confirmar_pagamento_stripe_idempotente`: already-confirmed payment is not re-processed

### `apps/pedidos/tests/test_services.py`

**`PedidoServicesTests`** (3 tests):
- `test_validar_dados_checkout_exige_nome_e_telefone`: missing name and phone raises `PedidoCheckoutError`
- `test_criar_pedido_do_carrinho_cria_pedido_itens_e_entrega`: full checkout creates `Pedido`, `ItemPedido`, calculates totals correctly
- `test_criar_pedido_do_carrinho_faz_rollback_quando_minimo_nao_atingido`: order below minimum rolls back all DB changes (atomic transaction)

## Coverage Gaps

**Critical gaps — high risk:**

**Views (all apps):**
- No test for any HTML view in any app
- Files: `apps/restaurantes/views.py`, `apps/pedidos/views.py`, `apps/produtos/views.py`, `apps/pagamentos/views.py`
- Risk: broken redirects, permission bypasses, template errors, session mishandling

**Authentication:**
- No test for login/logout flows
- File: `apps/restaurantes/auth_views.py`
- Risk: auth bypass, broken login redirects

**Multi-tenant middleware:**
- No test for tenant resolution by subdomain
- File: `config/middleware.py`
- Risk: cross-tenant data leakage, wrong restaurant shown

**Model methods and properties:**
- `Restaurante.esta_aberto` / `_calcular_esta_aberto`: timezone-sensitive, no tests
- `Pedido.validar_transicao_status`: no direct tests (only exercised through service tests indirectly)
- `Pedido.calcular_totais`: only implicitly tested via checkout service test
- File: `apps/restaurantes/models.py`, `apps/pedidos/models.py`

**Shopping cart flow:**
- No test for cart session management
- `adicionar_ao_carrinho`, `remover_do_carrinho`, `atualizar_carrinho`
- File: `apps/pedidos/views.py`

**Mercado Pago integration (current gateway):**
- `confirmar_pagamento_mp`, `processar_webhook_mp`, `_criar_pagamento_mp_pix`
- File: `apps/pagamentos/services.py`
- Note: existing Stripe tests reference the old gateway; MP functions have no test coverage

**Admin actions:**
- `marcar_preparo`, `marcar_entrega`, `marcar_concluido` bulk actions bypass `save()` validation
- File: `apps/pedidos/admin.py`

**API views (DRF):**
- No tests for any API endpoint
- Files: `apps/*/api_views.py`

**Core algorithms:**
- `bfs_caminho_mais_curto`, `bfs_status_alcancaveis`, `produtos_na_faixa_preco`, `agrupar_por_categoria_hash`
- File: `apps/core/algorithms.py`
- Risk: algorithmic bugs are silent

## Testing Patterns to Follow When Adding Tests

**Test a service function:**
```python
class MinhaFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Teste',
            subdominio='teste',
            proprietario=self.user,
            endereco='Rua A, 1',
            cidade='SP',
            estado='SP',
            cep='01000-000',
            telefone='11999999999',
            email='r@test.com',
            taxa_entrega=Decimal('5.00'),
            pedido_minimo=Decimal('10.00'),
            taxa_imposto=Decimal('10.00'),
            ativo=True,
        )

    def test_algo_especifico(self):
        resultado = minha_funcao(self.restaurante)
        self.assertEqual(resultado['campo'], valor_esperado)
```

**Test a view (when added):**
```python
from django.test import Client

class PainelViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='owner', password='123')
        # ... create restaurante
        self.client.login(username='owner', password='123')

    def test_dashboard_retorna_200(self):
        response = self.client.get('/painel/')
        self.assertEqual(response.status_code, 200)
```

**Test with mocked external API:**
```python
@override_settings(PAYMENT_GATEWAY='mercadopago', MP_ACCESS_TOKEN='TEST-fake')
@patch('apps.pagamentos.services.mercadopago.SDK')
def test_criar_pagamento_mp(self, mock_sdk_class):
    mock_sdk = MagicMock()
    mock_sdk_class.return_value = mock_sdk
    mock_sdk.preference().create.return_value = {
        'status': 201,
        'response': {'id': 'pref_123', 'init_point': 'https://mp.com/pay'}
    }
    resultado = criar_pagamento(self.pedido, metodo='card')
    self.assertEqual(resultado['gateway'], 'mercadopago')
```

## Notes on Test/Code Drift

The `PagamentoStripeTests` class tests `confirmar_pagamento_stripe` and Stripe-specific
paths. However, `apps/pagamentos/services.py` has been migrated to Mercado Pago (as of
migration `0006_switch_to_mercadopago.py` and the current `services.py`). The Stripe
tests import `confirmar_pagamento_stripe` which no longer exists in production code.
These tests will fail or be skipped when run against the current codebase.

Before adding new payment tests, verify which functions are actually exported from
`apps/pagamentos/services.py` and update test imports accordingly.

---

*Testing analysis: 2026-04-02*
