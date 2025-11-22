from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Q
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Transaction, Category, Budget
from .forms import TransactionForm, CategoryForm, BudgetForm, TransactionFilterForm


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'transactions/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        period = self.request.GET.get("period", "month")
        today = datetime.now().date()

        # Определяем период
        if period == "week":
            start_date = today - timedelta(days=today.weekday())
            title = "Статистика за текущую неделю"
        elif period == "year":
            start_date = today.replace(month=1, day=1)
            title = "Статистика за текущий год"
        else:
            start_date = today.replace(day=1)
            title = "Статистика за текущий месяц"

        # Транзакции за выбранный период
        transactions = Transaction.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=today
        )

        income = transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        expense = transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        balance = income - expense

        # 🔥 Добавляем последние 10 транзакций (НЕ зависят от периода)
        recent_transactions = Transaction.objects.filter(
            user=user
        ).order_by('-date')[:10]

        context.update({
            'income': income,
            'expense': expense,
            'balance': balance,
            'period': period,
            'period_title': title,
            'recent_transactions': recent_transactions,  # ← ВОТ ЭТОГО НЕ ХВАТАЛО
        })

        # Группировка расходов по категориям
        category_data = (
            Transaction.objects.filter(user=user, type="expense")
            .values("category__name", "category__color")
            .annotate(total=Sum("amount"))
        )

        context["chart_labels"] = [item["category__name"] for item in category_data]
        context["chart_values"] = [float(item["total"]) for item in category_data]
        context["chart_colors"] = [item["category__color"] or "#cccccc" for item in category_data]

        return context




class TransactionListView(LoginRequiredMixin, ListView):
    """Список всех транзакций"""
    model = Transaction
    template_name = 'transactions/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)

        form = TransactionFilterForm(self.request.GET, user=self.request.user)
        if form.is_valid():
            if form.cleaned_data.get('type'):
                queryset = queryset.filter(type=form.cleaned_data['type'])
            if form.cleaned_data.get('category'):
                queryset = queryset.filter(category=form.cleaned_data['category'])
            if form.cleaned_data.get('date_from'):
                queryset = queryset.filter(date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data.get('date_to'):
                queryset = queryset.filter(date__lte=form.cleaned_data['date_to'])

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        context['filter_form'] = TransactionFilterForm(self.request.GET, user=self.request.user)
        context['total_income'] = queryset.filter(type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        context['total_expense'] = queryset.filter(type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')

        return context


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transactions:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user  # ← ВАЖНО
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)



class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = reverse_lazy('transactions:list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Транзакция успешно обновлена!')
        return super().form_valid(form)


class TransactionDeleteView(DeleteView):
    model = Transaction
    template_name = 'transactions/transaction_confirm_delete.html'
    success_url = reverse_lazy('transactions:list')


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'transactions/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'transactions/category_form.html'
    success_url = reverse_lazy('transactions:category_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Категория успешно создана!')
        return super().form_valid(form)

class CategoryDeleteView(DeleteView):
    model = Category
    template_name = "transactions/category_confirm_delete.html"
    success_url = reverse_lazy("transactions:category_list")

    def get_queryset(self):
        # Чтобы пользователь видел только свои категории
        return Category.objects.filter(user=self.request.user)

