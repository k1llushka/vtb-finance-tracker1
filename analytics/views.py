from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from transactions.models import Transaction
from .forms import BudgetForm
from .models import Budget, AIRecommendation


class AnalyticsView(LoginRequiredMixin, View):
    """Аналитика расходов и доходов"""
    template_name = 'analytics/analytics.html'

    def generate_ai_recommendations(self, user, transactions, budgets):
        """Генерация и сохранение AI-рекомендаций"""
        recommendations = []

        # 1. Перерасход бюджета
        for b in budgets:
            spent = transactions.filter(
                category=b.category,
                type="expense"
            ).aggregate(total=Sum("amount"))["total"] or 0

            if spent > b.amount:
                recommendations.append(
                    f"Вы превысили бюджет категории «{b.category.name}» на {spent - b.amount} ₽."
                )

            elif spent > b.amount * Decimal("0.8"):
                recommendations.append(
                    f"Категория «{b.category.name}» почти достигла лимита. Осталось {b.amount - spent} ₽."
                )

        # 2. Категория с максимальными расходами
        top_category = (
            transactions.filter(type="expense")
            .values("category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")
            .first()
        )
        if top_category:
            recommendations.append(
                f"Самые большие расходы в категории «{top_category['category__name']}». "
                "Есть смысл проанализировать траты."
            )

        # 3. Динамика расходов за неделю
        last_week = timezone.now().date() - timedelta(days=7)
        week_expense = transactions.filter(
            date__gte=last_week,
            type="expense"
        ).aggregate(total=Sum("amount"))["total"] or 0

        if week_expense > Decimal("5000"):
            recommendations.append(
                "Расходы за последнюю неделю выше среднего. Попробуйте сократить необязательные покупки."
            )

        # 4. Если рекомендаций нет
        if not recommendations:
            recommendations.append("Отлично! Ваши траты выглядят стабильно и сбалансировано.")

        # Сохранение в БД
        for text in recommendations:
            AIRecommendation.objects.create(user=user, text=text)

        return recommendations

    def get(self, request):
        user = request.user

        # Период анализа
        period = int(request.GET.get('period', '30'))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=period)

        # Транзакции за период
        transactions = Transaction.objects.filter(
            user=user,
            date__range=[start_date, end_date]
        ).select_related('category')

        # Суммарные данные
        total_income = transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or Decimal("0")
        total_expense = transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or Decimal("0")

        # Бюджеты
        budgets = Budget.objects.filter(user=user)

        # Создание новых рекомендаций
        recommendations = self.generate_ai_recommendations(user, transactions, budgets)

        context = {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
            "days": period,
            "start_date": start_date,
            "end_date": end_date,
            "recommendations": recommendations,
        }

        return render(request, self.template_name, context)


class RecommendationListView(LoginRequiredMixin, ListView):
    """История рекомендаций"""
    template_name = "analytics/recommendations.html"
    context_object_name = "recommendations"

    def get_queryset(self):
        return AIRecommendation.objects.filter(user=self.request.user).order_by("-created_at")


class BudgetListView(LoginRequiredMixin, ListView):
    """Список бюджетов"""
    model = Budget
    context_object_name = 'budgets'
    template_name = 'analytics/budget_list.html'

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)


class BudgetCreateView(LoginRequiredMixin, CreateView):
    """Добавление бюджета"""
    model = Budget
    form_class = BudgetForm
    template_name = 'analytics/budget_form.html'
    success_url = reverse_lazy("analytics:budget_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Бюджет успешно создан!")
        return super().form_valid(form)
