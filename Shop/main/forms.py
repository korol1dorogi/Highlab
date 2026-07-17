# shop/forms.py
from django import forms
from .models import Order

class OrderForm(forms.ModelForm):
    """Форма оформления заказа"""
    confirm_data = forms.BooleanField(
        required=True,
        label='Подтверждаю корректность введенных данных',
        error_messages={'required': 'Необходимо подтвердить корректность данных'}
    )

    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone',
                  'delivery_method', 'payment_method', 'address', 'comment']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите ваше имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите вашу фамилию'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.ru'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}),
            'delivery_method': forms.RadioSelect(),
            'payment_method': forms.RadioSelect(),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Город, улица, дом, квартира'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Комментарии к заказу...'}),
        }
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email',
            'phone': 'Телефон',
            'delivery_method': 'Способ получения',
            'payment_method': 'Способ оплаты',
            'address': 'Адрес доставки',
            'comment': 'Комментарий к заказу',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Адрес обязателен только при доставке — проверяем в clean().
        self.fields['address'].required = False

    def clean(self):
        cleaned = super().clean()
        delivery = cleaned.get('delivery_method')
        address = (cleaned.get('address') or '').strip()
        if delivery in ('courier', 'shipping') and not address:
            self.add_error('address', 'Укажите адрес для выбранного способа доставки')
        if delivery == 'pickup':
            # Для самовывоза адрес не нужен — фиксируем маркер для менеджера.
            cleaned['address'] = 'Самовывоз'
        return cleaned
