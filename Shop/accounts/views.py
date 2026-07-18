from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import RegisterForm, LoginForm, ProfileForm
from .captcha import new_captcha


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    if request.method == 'POST':
        form = RegisterForm(request.POST, request=request)
        if form.is_valid():
            old_session_key = request.session.session_key
            user = form.save()
            login(request, user, backend='accounts.backends.EmailOrPhoneBackend')
            from main.cart import merge_session_cart_into_user
            merge_session_cart_into_user(request, old_session_key, user)
            messages.success(request, 'Аккаунт создан. Добро пожаловать!')
            return redirect('accounts:profile')
    else:
        form = RegisterForm(request=request)
    question = new_captcha(request.session)
    return render(request, 'accounts/register.html', {'form': form, 'captcha_question': question})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    if request.method == 'POST':
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['login'],
                password=form.cleaned_data['password'],
            )
            if user:
                old_session_key = request.session.session_key
                login(request, user)
                from main.cart import merge_session_cart_into_user
                merge_session_cart_into_user(request, old_session_key, user)
                messages.success(request, 'Вы вошли в аккаунт.')
                return redirect(next_url or 'accounts:profile')
            messages.error(request, 'Неверный логин или пароль.')
    else:
        form = LoginForm(request=request)
    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    logout(request)
    messages.success(request, 'Вы вышли из аккаунта.')
    return redirect('index:index')


@login_required
def profile(request):
    from main.models import Order, Review
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'items__product_variant__product'
    ).order_by('-created')
    reviews = Review.objects.filter(user=request.user).select_related('product').order_by('-created')
    return render(request, 'accounts/profile.html', {'orders': orders, 'reviews': reviews})


@login_required
def profile_edit(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileForm(request.POST, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные обновлены.')
            return redirect('accounts:profile')
    else:
        prof = getattr(user, 'profile', None)
        form = ProfileForm(user=user, initial={
            'email': user.email,
            'phone': prof.phone if prof else '',
            'first_name': user.first_name,
            'last_name': user.last_name,
            'middle_name': prof.middle_name if prof else '',
        })
    return render(request, 'accounts/profile_edit.html', {'form': form})
