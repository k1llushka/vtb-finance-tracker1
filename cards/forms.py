from django import forms
from .models import Card
from transactions.models import Account


class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ['account', 'card_holder', 'card_type', 'card_system', 'expiry_date', 'color']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'card_holder': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IVAN IVANOV'}),
            'card_type': forms.Select(attrs={'class': 'form-select'}),
            'card_system': forms.Select(attrs={'class': 'form-select'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['account'].queryset = Account.objects.filter(user=user, is_active=True)