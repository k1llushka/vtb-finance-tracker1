from django.db import models
from django.conf import settings
import json


class AIRecommendation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_recommendations"
    )
    text = models.TextField("Рекомендация")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "AI рекомендация"
        verbose_name_plural = "AI рекомендации"

    def __str__(self):
        return f"Рекомендация для {self.user}"

class Budget(models.Model):
    """Бюджеты по категориям"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analytics_budgets'
    )

    category = models.ForeignKey(
        'transactions.Category',
        on_delete=models.CASCADE,
        related_name='analytics_budgets'
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Сумма бюджета'
    )

    period_start = models.DateField(verbose_name='Начало периода')
    period_end = models.DateField(verbose_name='Конец периода')

    alert_threshold = models.IntegerField(
        default=80,
        verbose_name='Порог уведомления (%)'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Бюджет'
        verbose_name_plural = 'Бюджеты'

    def __str__(self):
        return f"Бюджет {self.category.name}: {self.amount} руб."
