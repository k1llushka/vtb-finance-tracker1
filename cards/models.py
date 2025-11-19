from django.db import models
from django.conf import settings
import random


class Card(models.Model):
    """Банковские карты"""

    CARD_TYPES = [
        ('debit', 'Дебетовая'),
        ('credit', 'Кредитная'),
    ]

    CARD_SYSTEMS = [
        ('mir', 'МИР'),
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cards'
    )

    account = models.ForeignKey(
        'transactions.Account',
        on_delete=models.CASCADE,
        related_name='cards'
    )

    card_number = models.CharField(
        max_length=19,
        unique=True,
        verbose_name='Номер карты'
    )

    card_holder = models.CharField(
        max_length=100,
        verbose_name='Держатель карты'
    )

    card_type = models.CharField(
        max_length=10,
        choices=CARD_TYPES,
        verbose_name='Тип карты'
    )

    card_system = models.CharField(
        max_length=20,
        choices=CARD_SYSTEMS,
        default='mir',
        verbose_name='Платежная система'
    )

    expiry_date = models.DateField(verbose_name='Срок действия')

    cvv = models.CharField(max_length=3, verbose_name='CVV')

    is_active = models.BooleanField(default=True, verbose_name='Активна')

    color = models.CharField(
        max_length=7,
        default='#0066CC',
        verbose_name='Цвет карты'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Карта'
        verbose_name_plural = 'Карты'

    def __str__(self):
        return f"{self.card_system.upper()} **** {self.card_number[-4:]}"

    def masked_number(self):
        """Маскированный номер карты"""
        return f"**** **** **** {self.card_number[-4:]}"