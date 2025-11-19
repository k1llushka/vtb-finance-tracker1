from django.db import models
from django.conf import settings
import json


class Budget(models.Model):
    """Бюджеты по категориям"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budgets'
    )

    category = models.ForeignKey(
        'transactions.Category',
        on_delete=models.CASCADE,
        related_name='budgets'
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

    def get_spent_amount(self):
        """Получить потраченную сумму"""
        from transactions.models import Transaction

        spent = Transaction.objects.filter(
            user=self.user,
            category=self.category,
            type='expense',
            date__range=[self.period_start, self.period_end]
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0

        return spent

    def get_percentage_used(self):
        """Процент использования бюджета"""
        spent = self.get_spent_amount()
        return (spent / self.amount * 100) if self.amount > 0 else 0


class AIRecommendation(models.Model):
    """AI-рекомендации"""

    RECOMMENDATION_TYPES = [
        ('saving', 'Сбережения'),
        ('investment', 'Инвестиции'),
        ('budget', 'Бюджет'),
        ('warning', 'Предупреждение'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )

    type = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_TYPES,
        verbose_name='Тип'
    )

    title = models.CharField(max_length=200, verbose_name='Заголовок')
    description = models.TextField(verbose_name='Описание')

    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Дополнительные данные'
    )

    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    is_applied = models.BooleanField(default=False, verbose_name='Применено')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'AI-рекомендация'
        verbose_name_plural = 'AI-рекомендации'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_type_display()}: {self.title}"