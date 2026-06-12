from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Profile, normalize_phone
from .captcha import check_captcha


class HoneypotMixin(forms.Form):
    """Скрытое поле-ловушка: люди его не видят, боты заполняют."""
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off',
                                       'class': 'hp-field', 'aria-hidden': 'true'}),
    )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise ValidationError('Обнаружен спам.')
        return ''


class RegisterForm(HoneypotMixin):
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'field', 'placeholder': 'Email'}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': '+7 (___) ___-__-__'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Фамилия (необязательно)'}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Имя (необязательно)'}))
    middle_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Отчество (необязательно)'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'field', 'placeholder': 'Пароль', 'autocomplete': 'new-password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'field', 'placeholder': 'Повторите пароль', 'autocomplete': 'new-password'}))
    captcha = forms.CharField(widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Ваш ответ', 'autocomplete': 'off', 'inputmode': 'numeric'}))

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email

    def clean_phone(self):
        raw = self.cleaned_data.get('phone') or ''
        if not raw.strip():
            return ''
        phone = normalize_phone(raw)
        if len(phone) < 10:
            raise ValidationError('Введите корректный номер телефона.')
        if Profile.objects.filter(phone=phone).exists():
            raise ValidationError('Пользователь с таким телефоном уже зарегистрирован.')
        return phone

    def clean_captcha(self):
        val = self.cleaned_data.get('captcha')
        if not self.request or not check_captcha(self.request.session, val):
            raise ValidationError('Неверный ответ на проверочный вопрос.')
        return val

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('email') and not cleaned.get('phone'):
            raise ValidationError('Укажите email или телефон — он будет вашим логином.')
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Пароли не совпадают.')
        if p1:
            try:
                validate_password(p1)
            except ValidationError as e:
                self.add_error('password1', e)
        return cleaned

    def save(self):
        d = self.cleaned_data
        email = d.get('email') or ''
        phone = d.get('phone') or ''
        username = email or phone
        user = User(username=username, email=email,
                    first_name=d.get('first_name') or '', last_name=d.get('last_name') or '')
        user.set_password(d['password1'])
        user.save()
        Profile.objects.create(user=user, phone=phone, middle_name=d.get('middle_name') or '')
        return user


class LoginForm(HoneypotMixin):
    login = forms.CharField(widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Email или телефон', 'autocomplete': 'username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'field', 'placeholder': 'Пароль', 'autocomplete': 'current-password'}))


class ProfileForm(forms.Form):
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'field', 'placeholder': 'Email'}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': '+7 (___) ___-__-__'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Фамилия'}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Имя'}))
    middle_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Отчество'}))

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise ValidationError('Этот email уже используется.')
        return email

    def clean_phone(self):
        raw = self.cleaned_data.get('phone') or ''
        if not raw.strip():
            return ''
        phone = normalize_phone(raw)
        if len(phone) < 10:
            raise ValidationError('Введите корректный номер телефона.')
        if Profile.objects.filter(phone=phone).exclude(user=self.user).exists():
            raise ValidationError('Этот телефон уже используется.')
        return phone

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('email') and not cleaned.get('phone'):
            raise ValidationError('Оставьте хотя бы email или телефон.')
        return cleaned

    def save(self):
        u = self.user
        d = self.cleaned_data
        u.email = d.get('email') or ''
        u.first_name = d.get('first_name') or ''
        u.last_name = d.get('last_name') or ''
        u.save()
        prof, _ = Profile.objects.get_or_create(user=u)
        prof.phone = d.get('phone') or ''
        prof.middle_name = d.get('middle_name') or ''
        prof.save()
        return u
