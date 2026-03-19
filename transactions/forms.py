from datetime import date

from django import forms

from cards.models import Card

from .models import Budget, Category, Transaction


def get_categories_for_transaction_type(user, tx_type):
    categories = Category.objects.filter(user=user, is_active=True)
    if tx_type in (Transaction.TYPE_INCOME, Transaction.TYPE_EXPENSE):
        categories = categories.filter(type=tx_type)
    if tx_type == Transaction.TYPE_INCOME:
        salary_categories = categories.filter(name__icontains="зарп")
        if salary_categories.exists():
            categories = salary_categories
    return categories.order_by("name")


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["type", "amount", "category", "card", "date", "description"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        tx_type = None
        if "type" in self.data:
            tx_type = self.data.get("type")
        elif self.instance and self.instance.pk:
            tx_type = self.instance.type
        else:
            tx_type = self.initial.get("type") or Transaction.TYPE_EXPENSE

        self.fields["card"].queryset = Card.objects.filter(user=user)
        self.fields["card"].empty_label = "Наличными / Без карты"
        self.fields["category"].queryset = get_categories_for_transaction_type(user, tx_type)
        self.fields["type"].initial = tx_type

        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

        self.fields["type"].widget.attrs["class"] = "form-select"
        self.fields["category"].widget.attrs["class"] = "form-select"
        self.fields["card"].widget.attrs["class"] = "form-select"
        self.fields["description"].widget.attrs.update({"rows": 5})

        if not self.instance.pk:
            self.fields["date"].initial = date.today()

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        tx_type = cleaned_data.get("type")
        if category and tx_type and category.type != tx_type:
            self.add_error("category", "Категория не соответствует выбранному типу транзакции.")
        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "type", "icon", "color", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "type": forms.Select(attrs={"class": "form-select"}),
            "icon": forms.Select(attrs={"class": "form-select"}),
            "color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ["category", "amount", "month"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select", "required": True}),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00",
                    "step": "0.01",
                    "min": "0.01",
                    "required": True,
                }
            ),
            "month": forms.DateInput(attrs={"class": "form-control", "type": "month", "required": True}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["category"].queryset = Category.objects.filter(user=user, type="expense", is_active=True)


class TransactionFilterForm(forms.Form):
    type = forms.ChoiceField(
        label="Тип",
        choices=[("", "Все")] + list(Transaction.TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    category = forms.ModelChoiceField(
        label="Категория",
        queryset=Category.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["category"].queryset = Category.objects.filter(user=user, is_active=True)
