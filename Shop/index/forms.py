from django import forms

from .models import Lead
from accounts.captcha import check_captcha

LEAD_CAPTCHA_KEY = 'lead_captcha'


class LeadForm(forms.ModelForm):
    """Форма заявки с лендинга (с капчей и honeypot-защитой от ботов)."""

    # Honeypot. Имя поля нарочно бессмысленное: поля вроде "website" браузеры
    # заполняют автозаполнением, и настоящая заявка молча отбрасывалась бы.
    lead_check = forms.CharField(
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

    def clean_lead_check(self):
        if self.cleaned_data.get('lead_check'):
            raise forms.ValidationError('Обнаружен спам.')
        return ''

    def clean_captcha(self):
        val = self.cleaned_data.get('captcha')
        if not self.request or not check_captcha(self.request.session, val, key=LEAD_CAPTCHA_KEY):
            raise forms.ValidationError('Неверный ответ на проверочный вопрос.')
        return val


class QuickLeadForm(forms.ModelForm):
    """Быстрая заявка из виджета обратного звонка / квиза / посадочной страницы.

    Без видимой капчи — на конверсионных формах капча убивает заявки.
    Защита от ботов: honeypot-поле + проверка «слишком быстрого» сабмита во вьюхе.
    """
    lead_check = forms.CharField(required=False)  # honeypot (см. комментарий в LeadForm)

    class Meta:
        model = Lead
        fields = ['name', 'phone', 'message', 'source']

    def clean_lead_check(self):
        if self.cleaned_data.get('lead_check'):
            raise forms.ValidationError('spam')
        return ''

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if len(digits) < 5:
            raise forms.ValidationError('Укажите корректный номер телефона.')
        return phone
