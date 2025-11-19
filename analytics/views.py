from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Avg
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
        )

        # Статистика
        total_income = transactions.filter(type='income').aggregate(
            total=Sum('amount')
        )['total'] or 0

        total_expense = transactions.filter(type='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0

        # Расходы по категориям
        expense_by_category = transactions.filter(
            type='expense'
        ).values(
            'category__name', 'category__color'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        # Тренд расходов
        expense_trend = self.calculate_trend(transactions.filter(type='expense'))

        # AI рекомендации
        recommendations = AIRecommendation.objects.filter(
            user=user,
            is_read=False
        )[:3]

        context = {
            'period': period,
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'expense_by_category': expense_by_category,
            'expense_trend': expense_trend,
            'recommendations': recommendations,
        }

        return render(request, self.template_name, context)

    def calculate_trend(self, transactions):
        """Расчет тренда расходов"""
        if not transactions.exists():
            return 0

        df = pd.DataFrame(list(transactions.values('date', 'amount')))
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').resample('D').sum()

        if len(df) < 2:
            return 0

        # Простая линейная регрессия
        x = np.arange(len(df))
        y = df['amount'].values

        if len(x) > 0 and len(y) > 0:
            slope = np.polyfit(x, y, 1)[0]
            return round(slope, 2)

        return 0


class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = 'analytics/budget_list.html'
    context_object_name = 'budgets'

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Добавляем информацию о расходах для каждого бюджета
        for budget in context['budgets']:
            budget.spent = budget.get_spent_amount()
            budget.percentage = budget.get_percentage_used()
            budget.remaining = budget.amount - budget.spent

        return context


class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'analytics/budget_form.html'
    success_url = reverse_lazy('analytics:budget_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Бюджет успешно создан!')
        return super().form_valid(form)


class RecommendationListView(LoginRequiredMixin, ListView):
    model = AIRecommendation
    template_name = 'analytics/recommendations.html'
    context_object_name = 'recommendations'
    paginate_by = 10

    def get_queryset(self):
        return AIRecommendation.objects.filter(user=self.request.user)


class ReportsView(LoginRequiredMixin, View):
    template_name = 'analytics/reports.html'

    def get(self, request):
        # Здесь будет генерация отчетов
        return render(request, self.template_name)