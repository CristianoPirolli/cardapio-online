# Coding Conventions

**Analysis Date:** 2026-04-02

## Language and Locale

All identifiers, field names, verbose names, error messages, comments, and docstrings
are written in **Portuguese (pt-BR)**. This is a deliberate project convention, not an
accident. Every new file must follow this same language rule.

- Model field names: Portuguese (`cliente_nome`, `taxa_entrega`, `criado_em`)
- URL route names: Portuguese (`painel_dashboard`, `cardapio_publico`, `ver_carrinho`)
- Template names and directories: Portuguese (`pagamentos/`, `pedidos/`, `produtos/`)
- Python variable names inside functions: Portuguese (`restaurante`, `itens_sessao`, `resultado`)
- Exception classes: Portuguese names (`PedidoCheckoutError`)

## Naming Patterns

**Files:**
- Module files: lowercase, no separators (`views.py`, `models.py`, `services.py`)
- URL modules are split by concern — `urls.py` for HTML views, `api_urls.py` for DRF
- Auth views live in a dedicated file: `auth_views.py` / `auth_urls.py`

**Functions:**
- snake_case throughout: `criar_pagamento`, `montar_resumo_carrinho`, `validar_dados_checkout`
- Private helpers: leading underscore: `_get_carrinho`, `_salvar_carrinho`, `_item_key`, `_criar_pagamento_mock`
- View helpers that are not views: `_restaurante_do_usuario`, `_redirecionar_sem_restaurante`

**Variables:**
- snake_case: `pedido_minimo`, `taxa_imposto`, `preco_unitario`
- Context dict keys match template variable names exactly

**Types / Classes:**
- PascalCase models: `Restaurante`, `Pedido`, `ItemPedido`, `Pagamento`, `Categoria`, `Produto`
- PascalCase DRF classes: `RestauranteSerializer`, `IsProprietarioOrReadOnly`, `RestauranteViewSet`
- PascalCase form classes: `RestauranteForm`, `ProdutoForm`, `TamanhoPizzaFormSet`
- PascalCase admin classes: `RestauranteAdmin`, `PedidoAdmin`, `PagamentoAdmin`
- PascalCase exception: `PedidoCheckoutError`

**URL Names:**
- Pattern: `{app}_{action}` — `painel_dashboard`, `painel_pedidos`, `painel_configuracoes`
- Public views: `cardapio_publico`, `produto_detalhe`, `ver_carrinho`, `checkout`
- Payment views: `pagamento_escolher`, `pagamento_sucesso`, `pagamento_erro`
- AJAX/API endpoints: `acompanhar_pedido_status`, `painel_pedidos_abertos_count`

## File-Level Header Convention

Every `.py` file begins with a multi-line comment block:

```python
# =============================================================================
# apps/pagamentos/services.py - Serviços de pagamento (Mercado Pago e Mock)
#
# Configure PAYMENT_GATEWAY no .env:
#   PAYMENT_GATEWAY=mercadopago  -> Mercado Pago (cartão + PIX)
#   PAYMENT_GATEWAY=mock         -> Simulação local (desenvolvimento)
# =============================================================================
```

Always include the file path and a brief description. Public vs private interfaces
are documented here. This is expected for all new files.

## Django App Structure

Each app follows this consistent structure:

```
apps/{app_name}/
├── __init__.py
├── admin.py          # ModelAdmin registrations with @admin.register
├── api_urls.py       # DRF router URLs
├── api_views.py      # DRF ViewSet / APIView classes
├── apps.py           # AppConfig
├── forms.py          # ModelForm and InlineFormSet classes (when needed)
├── migrations/       # Auto-generated
├── models.py         # Model definitions
├── serializers.py    # DRF ModelSerializer classes
├── services.py       # Business logic functions (no HTTP, no templates)
├── tests/
│   ├── __init__.py
│   └── test_services.py
├── urls.py           # HTML view URL patterns
└── views.py          # Function-based HTML views
```

## View Pattern: Function-Based Views (FBV)

**All HTML views are function-based.** No class-based views are used for HTML rendering.

```python
@login_required
def painel_configuracoes(request):
    """Docstring in Portuguese describing the view."""
    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        return _redirecionar_sem_restaurante(request)

    if request.method == 'POST':
        form = RestauranteForm(request.POST, request.FILES, instance=restaurante)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações atualizadas com sucesso!')
            return redirect('painel_configuracoes')
    else:
        form = RestauranteForm(instance=restaurante)

    return render(request, 'painel/configuracoes.html', {
        'form': form,
        'restaurante': restaurante,
    })
```

Key patterns:
- Auth guard at function start: `@login_required` decorator or explicit check
- Ownership check immediately after: `_restaurante_do_usuario(request)` → redirect if None
- POST/GET branching with early returns
- Single `render()` at the end of GET path
- Context dict always includes `restaurante` key

**API views use DRF ViewSets** (`ModelViewSet`). Files: `apps/*/api_views.py`.

## Business Logic Convention: Service Layer

Business logic lives in `services.py`, not in views or models. Views only:
1. Parse request data
2. Call service functions
3. Handle errors (catch exceptions, call `messages.*`)
4. Render or redirect

Service functions:
- Are pure Python — no `request`, no `render`, no `redirect`
- Raise custom exceptions for domain errors: `PedidoCheckoutError`
- Use `@transaction.atomic()` for multi-step DB writes
- Accept typed arguments (model instances, dicts), not request objects

Example:
- `apps/pedidos/services.py`: `criar_pedido_do_carrinho`, `validar_dados_checkout`, `montar_resumo_carrinho`
- `apps/pagamentos/services.py`: `criar_pagamento`, `confirmar_pagamento_mock`, `processar_webhook_mp`

## Model Conventions

**Fields:**
- All `CharField` / `DecimalField` / `BooleanField` include `verbose_name` in Portuguese
- Timestamps always: `criado_em = DateTimeField(auto_now_add=True)`, `atualizado_em = DateTimeField(auto_now=True)`
- Monetary fields: `DecimalField(max_digits=10, decimal_places=2)` with `MinValueValidator(0)`
- Status fields: `CharField(max_length=N, choices=STATUS_CHOICES)` with choices as list of tuples
- Booleans for availability/active: `ativo`, `disponivel`, `pago`

**Meta class (always present):**
```python
class Meta:
    verbose_name = 'Pedido'
    verbose_name_plural = 'Pedidos'
    ordering = ['-criado_em']
    indexes = [
        models.Index(fields=['restaurante', 'status'], name='idx_pedido_rest_status'),
    ]
```

Index names follow convention: `idx_{model}_{field(s)}`.

**`__str__`:**
- Always defined
- Returns human-readable string in Portuguese

**Model methods:**
- Business methods that compute derived state: `calcular_totais`, `validar_transicao_status`
- Properties for computed read-only values: `@property esta_aberto`, `@property proximo_passo`
- Private methods for internal calculations: `_calcular_esta_aberto`, `_dias_funcionamento_tuple`

**Custom `save()` pattern:**
```python
def save(self, *args, **kwargs):
    if not self.subdominio:
        self.subdominio = slugify(self.nome)
    super().save(*args, **kwargs)
    cache_restaurante.invalidate(f"aberto:{self.id}")
```
Always call `super().save()`. Invalidate caches after save.

## Admin Conventions

All models use `@admin.register(Model)` decorator — not `admin.site.register()`.

```python
@admin.register(Restaurante)
class RestauranteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'subdominio', ...)
    list_filter = ('ativo', 'estado')
    search_fields = ('nome', 'subdominio', 'email')
    list_editable = ('ativo',)
    readonly_fields = ('criado_em', 'atualizado_em')
    fieldsets = (...)
```

- `fieldsets`: always used, organized by logical category
- `readonly_fields`: always includes timestamps (`criado_em`, `atualizado_em`)
- Inlines: `TabularInline` for related records (items, pizza sizes)

## URL Patterns

**HTML views:** registered in `apps/{app}/urls.py`, included in `config/urls.py`.
**API views:** registered in `apps/{app}/api_urls.py`, included under `/api/`.

Pattern style — explicit paths, no trailing slash on detail routes:
```python
path('pedidos/', views.painel_pedidos, name='painel_pedidos'),
path('pedidos/<int:pedido_id>/', views.painel_pedido_detalhe, name='painel_pedido_detalhe'),
```

- Typed converters always used: `<int:pedido_id>`, `<int:produto_id>`
- Action sub-paths for non-CRUD: `path('pedidos/abertos/count/', ...)`
- Webhook endpoints registered explicitly with `@csrf_exempt`

## Forms

- `forms.ModelForm` with explicit `class Meta: fields = [...]` lists (never `fields = '__all__'`)
- Widget overrides in `Meta.widgets` dict for textarea rows, number input steps
- Queryset filtering in `__init__`: filter choices by current tenant's restaurant
- `InlineFormSet` via `inlineformset_factory` for related records (e.g., pizza sizes)

## Import Organization

1. Standard library (`os`, `uuid`, `logging`, `decimal`, `collections`)
2. Django core (`django.shortcuts`, `django.db.models`, `django.conf`)
3. Third-party (`rest_framework`, `mercadopago`, `slugify`)
4. Internal apps (`apps.restaurantes.models`, `apps.pedidos.models`)
5. Same-app imports (`.models`, `.forms`, `.services`)

No path aliases used — all imports are full dotted paths.

## Error Handling

**Domain errors:** Raise `PedidoCheckoutError` (or similar custom exception) in service layer.
Views catch with `try/except` and call `messages.error(request, str(exc))`.

**External API errors:** Catch `Exception as exc`, log with `logger.warning(...)`, then propagate
or surface as `messages.error` in view.

**Logging:**
```python
logger = logging.getLogger(__name__)
logger.warning('processar_webhook_mp error: %s', exc)
logger.debug('verificar_status_pagamento: %s', exc)
```
`logger` is module-level; uses `%s` formatting (not f-strings) per Python logging convention.

## Template Conventions

- Templates organized by app in `templates/{app_name}/`
- Painel (admin panel) templates in `templates/painel/`
- All templates extend `base.html` or `templates/painel/base_painel.html`
- Template names match view function names: `painel_configuracoes` view → `painel/configuracoes.html`
- Context variables named in Portuguese matching model field names

## Comments

**Inline comments** are used extensively to explain algorithmic choices and
Big-O complexity rationale (the codebase uses a "Grokking Algorithms" theme):
```python
# Big O (Cap. 1): índices transformam busca de O(n) para O(log n)
# Tabela Hash (Cap. 5): transições como dicionário para lookup O(1)
```

**Docstrings:** Every public function and class has a docstring in Portuguese describing
purpose, behavior, and optimization notes where relevant.

## Caching Conventions

Custom `HashCache` instances from `apps/core/algorithms.py` are used for in-process caching:
- `cache_restaurante` (TTL 30s): restaurant config and open/closed status
- `cache_cardapio` (TTL 30s): menu data per restaurant
- `cache_produtos` (TTL 10s): product lookups

Cache keys follow pattern: `"{domain}:{id}"` — e.g., `"aberto:1"`, `"cardapio:3"`.
Always invalidate cache in `save()` after writing to DB.

---

*Convention analysis: 2026-04-02*
