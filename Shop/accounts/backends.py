from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from .models import Profile, normalize_phone


class EmailOrPhoneBackend(ModelBackend):
    """Вход по email ИЛИ телефону + пароль."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        login = (username or kwargs.get('email') or '').strip()
        if not login or password is None:
            return None

        user = None
        if '@' in login:
            user = User.objects.filter(email__iexact=login).order_by('id').first()
        else:
            phone = normalize_phone(login)
            if phone:
                prof = Profile.objects.select_related('user').filter(phone=phone).first()
                if prof:
                    user = prof.user
            if user is None:
                user = User.objects.filter(username=login).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
