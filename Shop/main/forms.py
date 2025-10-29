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
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'comment']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите ваше имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите вашу фамилию'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.ru'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Город, улица, дом, квартира'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Комментарии к заказу...'}),
        }
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия', 
            'email': 'Email',
            'phone': 'Телефон',
            'address': 'Адрес доставки',
            'comment': 'Комментарий к заказу',
        }