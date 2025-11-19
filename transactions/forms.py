from django import forms
from .models import Transaction, Category, Budget
from datetime import date


class TransactionForm(forms.ModelForm):
    """Форма для создания/редактирования транзакции"""

    class Meta:
        model = Transaction
        fields = ['type', 'category', 'amount', 'date', 'description']
        widgets = {
            'type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание транзакции (необязательно)'
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Фильтруем категории по пользователю
            self.fields['category'].queryset = Category.objects.filter(
                user=user,
                is_active=True
            )

        # Устанавливаем сегодняшнюю дату по умолчанию
        if not self.instance.pk:
            self.fields['date'].initial = date.today()


class CategoryForm(forms.ModelForm):
    """Форма для создания/редактирования категории"""

    class Meta:
        model = Category
        fields = ['name', 'type', 'icon', 'color', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название категории',
                'required': True
            }),
            'type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'icon': forms.Select(attrs={
                'class': 'form-select'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Описание (необязательно)'
            }),
        }


class BudgetForm(forms.ModelForm):
    """Форма для создания/редактирования бюджета"""

    class Meta:
        model = Budget
        fields = ['category', 'amount', 'month']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'month': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'month',
                'required': True
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Только категории расходов
            self.fields['category'].queryset = Category.objects.filter(
                user=user,
                type='expense',
                is_active=True
            )


class TransactionFilterForm(forms.Form):
    """Форма для фильтрации транзакций"""

    type = forms.ChoiceField(
        label='Тип',
        choices=[('', 'Все')] + list(Transaction.TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ModelChoiceField(
        label='Категория',
        queryset=Category.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        label='С',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        label='По',
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                user=user,
                is_active=True
            )