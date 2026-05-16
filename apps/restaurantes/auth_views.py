# =============================================================================
# apps/restaurantes/auth_views.py - Views de autenticação
#
# Registro de novos usuários, login, logout.
# Após registro, cria automaticamente um restaurante para o novo proprietário.
# =============================================================================

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

from .models import Restaurante

def registro_view(request):
    """
    Cadastro público desativado.
    Usuários e restaurantes devem ser criados pelo administrador master no Django Admin.
    """
    messages.warning(
        request,
        'Cadastro desativado. Solicite a criação da conta ao administrador master.'
    )
    return redirect('login')


def login_view(request):
    """
    View de login com formulário padrão do Django.

    Redireciona para o painel após login bem-sucedido.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)

            if user.is_superuser:
                return redirect('/admin/')

            if not Restaurante.objects.filter(proprietario=user).exists():
                messages.warning(
                    request,
                    'Sua conta ainda não está vinculada a uma panificadora. '
                    'Solicite o vínculo ao administrador master.'
                )
                return redirect('home')

            return redirect('painel_dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'auth/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def logout_view(request):
    """Faz logout e redireciona para a home."""
    logout(request)
    messages.info(request, 'Você saiu do sistema.')
    return redirect('home')
