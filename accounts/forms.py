# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, UserProfile


class LoginForm(AuthenticationForm):
    """Форма входа в систему"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя или Email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        })
    )


class RegisterForm(UserCreationForm):
    """Форма регистрации нового пользователя"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )

    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя'
        })
    )

    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фамилия'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя пользователя'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Пароль'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Подтвердите пароль'
        })

        # Русские метки
        self.fields['username'].label = 'Имя пользователя'
        self.fields['email'].label = 'Email'
        self.fields['first_name'].label = 'Имя'
        self.fields['last_name'].label = 'Фамилия'
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'


class UserUpdateForm(forms.ModelForm):
    """Форма для обновления информации пользователя"""

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'address',
            'avatar',
            'passport_number',
            'inn'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя пользователя'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Фамилия'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (999) 123-45-67'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Адрес проживания'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'passport_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234 567890'
            }),
            'inn': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123456789012'
            }),
        }
        labels = {
            'username': 'Имя пользователя',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email',
            'phone_number': 'Телефон',
            'address': 'Адрес',
            'avatar': 'Фото профиля',
            'passport_number': 'Номер паспорта',
            'inn': 'ИНН',
        }
        help_texts = {
            'username': 'Обязательное поле. Только буквы, цифры и символы @/./+/-/_',
            'email': 'Введите действующий email адрес',
            'phone_number': 'Формат: +7 (999) 123-45-67',
            'passport_number': 'Серия и номер паспорта',
            'inn': '12-значный ИНН',
        }


class UserProfileForm(forms.ModelForm):
    """Форма для настроек профиля пользователя"""

    class Meta:
        model = UserProfile
        fields = [
            'monthly_budget',
            'currency',
            'notification_enabled',
            'email_notifications',
            'ai_recommendations_enabled'
        ]
        widgets = {
            'monthly_budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '50000',
                'step': '0.01',
                'min': '0'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'notification_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'ai_recommendations_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'monthly_budget': 'Месячный бюджет (₽)',
            'currency': 'Валюта',
            'notification_enabled': 'Включить уведомления',
            'email_notifications': 'Email уведомления',
            'ai_recommendations_enabled': 'AI рекомендации',
        }
        help_texts = {
            'monthly_budget': 'Укажите планируемый месячный бюджет',
            'currency': 'Основная валюта для отображения',
            'notification_enabled': 'Получать уведомления о транзакциях',
            'email_notifications': 'Получать уведомления на email',
            'ai_recommendations_enabled': 'Получать AI рекомендации по управлению финансами',
        }