from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta
import pandas as pd
import numpy as np
from .models import Budget, AIRecommendation
from transactions.models import Transaction, Category
from .forms import BudgetForm


class AnalyticsView(LoginRequiredMixin, View):
    template_name = 'analytics/analytics.html'

    def get(self, request):
        user = request.user

        # Период анализа
        period = request.GET.get('period', '30')
        days = int(period)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Транзакции за период
        transactions = Transaction.objects.filter(
            user=user,
            date__range=[start_date, end_date]