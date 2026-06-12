from django import forms

from .models import Lead
from accounts.captcha import check_captcha

LEAD_CAPTCHA_KEY = 'lead_captcha'


class LeadForm(forms.ModelForm):
    """Форма заявки с лендинга (с капчей и honeypot-защитой от ботов)."""

    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off',
                                       'class': 'hp-field', 'aria-hidden': 'true'}),
    )
    captcha = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'field', 'placeholder': 'Ответ',
                                       'autocomplete': 'off', 'inputmode': 'numeric'}),
    )

    class Meta:
        model = Lead
        fields = ['name', 'phone', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'field', 'placeholder': 'Ваше имя', 'autocomplete': 'name',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'field', 'placeholder': '+7 (___) ___-__-__', 'autocomplete': 'tel',
            }),
            'message': forms.Textarea(attrs={
                'class': 'field', 'rows': 3,
                'placeholder': 'Коротко о задаче (необязательно)',
            }),
        }

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Обнаружен спам.')
        return ''

    def clean_captcha(self):
        val = self.cleaned_data.get('captcha')
        if not self.request or not check_captcha(self.request.session, val, key=LEAD_CAPTCHA_KEY):
            raise forms.ValidationError('Неверный ответ на проверочный вопрос.')
        return val
