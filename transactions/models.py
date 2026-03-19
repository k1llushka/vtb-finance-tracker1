from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum

from cards.models import Card


class Category(models.Model):
    """Категории транзакций."""

    TYPE_CHOICES = [
        ("income", "Доход"),
        ("expense", "Расход"),
    ]

    ICON_CHOICES = [
        ("bi-wallet2", "Кошелек"),
        ("bi-cart", "Покупки"),
        ("bi-house", "Дом"),
        ("bi-car-front", "Транспорт"),
        ("bi-cup-hot", "Еда"),
        ("bi-heart-pulse", "Здоровье"),
        ("bi-controller", "Развлечения"),
        ("bi-book", "Образование"),
        ("bi-briefcase", "Работа"),
        ("bi-gift", "Подарки"),
        ("bi-piggy-bank", "Накопления"),
        ("bi-credit-card", "Счета"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
        verbose_name="Пользователь",
    )
    name = models.CharField("Название", max_length=100)
    type = models.CharField("Тип", max_length=10, choices=TYPE_CHOICES)
    icon = models.CharField("Иконка", max_length=50, choices=ICON_CHOICES, default="bi-wallet2")
    color = models.CharField("Цвет", max_length=7, default="#0d6efd")
    description = models.TextField("Описание", blank=True)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]
        unique_together = ["user", "name", "type"]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Transaction(models.Model):
    """Финансовые транзакции пользователя."""

    TYPE_INCOME = "income"
    TYPE_EXPENSE = "expense"

    TYPE_CHOICES = [
        (TYPE_INCOME, "Доход"),
        (TYPE_EXPENSE, "Расход"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Пользователь",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="transactions",
        verbose_name="Категория",
    )
    type = models.CharField("Тип", max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(
        "Сумма",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    description = models.TextField("Описание", blank=True)
    date = models.DateField("Дата")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.category} - {self.amount}"


class Budget(models.Model):
    """Бюджеты по категориям."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets",
        verbose_name="Пользователь",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="budgets",
        verbose_name="Категория",
    )
    amount = models.DecimalField(
        "Лимит",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    month = models.DateField("Месяц")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Бюджет"
        verbose_name_plural = "Бюджеты"
        unique_together = ["user", "category", "month"]
        ordering = ["-month"]

    def __str__(self):
        return f"{self.category.name} - {self.amount}"

    def get_spent(self):
        month_start = self.month.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        total = self.category.transactions.filter(
            user=self.user,
            type=Transaction.TYPE_EXPENSE,
            date__gte=month_start,
            date__lt=next_month,
        ).aggregate(total=Sum("amount"))["total"]
        return total or Decimal("0")

    def get_remaining(self):
        return self.amount - self.get_spent()

    def get_percentage(self):
        if not self.amount:
            return Decimal("0")
        return (self.get_spent() / self.amount) * 100
