from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .ai_services import finance_ai_service
from .models import Budget, Category, Transaction
from .serializers import (
    AIRecommendationSerializer,
    BudgetSerializer,
    CategorySerializer,
    ChartDataSerializer,
    StatisticsSerializer,
    TransactionSerializer,
)


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        card_id = self.request.query_params.get("card")
        if card_id and card_id.isdigit():
            queryset = queryset.filter(card_id=int(card_id))
        return queryset

    def perform_create(self, serializer):
        transaction = serializer.save(user=self.request.user)
        if transaction.type == Transaction.TYPE_EXPENSE and transaction.category_id is None and transaction.description:
            categorization = finance_ai_service.categorize_expense(
                user=self.request.user,
                description=transaction.description,
                amount=transaction.amount,
                tx_date=transaction.date,
            )
            if categorization.should_apply:
                transaction.category_id = categorization.category_id
                transaction.save(update_fields=["category"])

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        queryset = self._filter_by_period(self.get_queryset(), request.query_params.get("period", "month"))

        income = queryset.filter(type=Transaction.TYPE_INCOME).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        expense = queryset.filter(type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        avg_transaction = queryset.aggregate(avg=Avg("amount"))["avg"] or Decimal("0")

        data = {
            "total_income": income,
            "total_expense": expense,
            "balance": income - expense,
            "transactions_count": queryset.count(),
            "categories_count": queryset.values("category").distinct().count(),
            "avg_transaction": avg_transaction,
        }
        return Response(StatisticsSerializer(data).data)

    @action(detail=False, methods=["get"])
    def chart_data(self, request):
        chart_type = request.query_params.get("type", "monthly")
        if chart_type == "monthly":
            return self._get_monthly_chart_data(request)
        if chart_type == "category":
            return self._get_category_chart_data(request)
        if chart_type == "trend":
            return self._get_trend_chart_data(request)
        return Response({"error": "Invalid chart type"}, status=400)

    def _get_monthly_chart_data(self, request):
        today = timezone.localdate()
        card_id = request.query_params.get("card")
        months = []
        income_data = []
        expense_data = []

        for i in range(6, -1, -1):
            dt = today - timedelta(days=30 * i)
            month_start = dt.replace(day=1)
            next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = min(next_month - timedelta(days=1), today) if i == 0 else next_month - timedelta(days=1)

            income_queryset = Transaction.objects.filter(
                user=request.user,
                type=Transaction.TYPE_INCOME,
                date__gte=month_start,
                date__lte=month_end,
            )
            expense_queryset = Transaction.objects.filter(
                user=request.user,
                type=Transaction.TYPE_EXPENSE,
                date__gte=month_start,
                date__lte=month_end,
            )
            if card_id and card_id.isdigit():
                income_queryset = income_queryset.filter(card_id=int(card_id))
                expense_queryset = expense_queryset.filter(card_id=int(card_id))

            months.append(month_start.strftime("%B"))
            income_data.append(float(income_queryset.aggregate(total=Sum("amount"))["total"] or 0))
            expense_data.append(float(expense_queryset.aggregate(total=Sum("amount"))["total"] or 0))

        data = {
            "labels": months,
            "datasets": [
                {
                    "label": "Доходы",
                    "data": income_data,
                    "backgroundColor": "rgba(40, 167, 69, 0.2)",
                    "borderColor": "rgba(40, 167, 69, 1)",
                    "borderWidth": 2,
                },
                {
                    "label": "Расходы",
                    "data": expense_data,
                    "backgroundColor": "rgba(220, 53, 69, 0.2)",
                    "borderColor": "rgba(220, 53, 69, 1)",
                    "borderWidth": 2,
                },
            ],
        }
        return Response(ChartDataSerializer(data).data)

    def _get_category_chart_data(self, request):
        card_id = request.query_params.get("card")
        period = request.query_params.get("period", "month")
        queryset = self._filter_by_period(
            Transaction.objects.filter(user=request.user, type=Transaction.TYPE_EXPENSE),
            period,
        )
        if card_id and card_id.isdigit():
            queryset = queryset.filter(card_id=int(card_id))

        categories = queryset.values("category__name", "category__color").annotate(total=Sum("amount")).order_by("-total")[:10]
        data = {
            "labels": [item["category__name"] or "Без категории" for item in categories],
            "datasets": [
                {
                    "label": "Расходы по категориям",
                    "data": [float(item["total"]) for item in categories],
                    "backgroundColor": [item["category__color"] or "#b9c1d1" for item in categories],
                    "borderWidth": 0,
                }
            ],
        }
        return Response(ChartDataSerializer(data).data)

    def _get_trend_chart_data(self, request):
        today = timezone.localdate()
        card_id = request.query_params.get("card")
        dates = []
        balance_data = []

        for i in range(29, -1, -1):
            dt = today - timedelta(days=i)
            income_queryset = Transaction.objects.filter(user=request.user, type=Transaction.TYPE_INCOME, date__lte=dt)
            expense_queryset = Transaction.objects.filter(user=request.user, type=Transaction.TYPE_EXPENSE, date__lte=dt)
            if card_id and card_id.isdigit():
                income_queryset = income_queryset.filter(card_id=int(card_id))
                expense_queryset = expense_queryset.filter(card_id=int(card_id))

            income = income_queryset.aggregate(total=Sum("amount"))["total"] or 0
            expense = expense_queryset.aggregate(total=Sum("amount"))["total"] or 0
            dates.append(dt.strftime("%d.%m"))
            balance_data.append(float(income - expense))

        data = {
            "labels": dates,
            "datasets": [
                {
                    "label": "Баланс",
                    "data": balance_data,
                    "fill": True,
                    "backgroundColor": "rgba(13, 110, 253, 0.1)",
                    "borderColor": "rgba(13, 110, 253, 1)",
                    "borderWidth": 2,
                    "tension": 0.4,
                }
            ],
        }
        return Response(ChartDataSerializer(data).data)

    def _filter_by_period(self, queryset, period):
        today = timezone.localdate()
        if period == "week":
            return queryset.filter(date__gte=today - timedelta(days=today.weekday()), date__lte=today)
        if period == "year":
            return queryset.filter(date__gte=today.replace(month=1, day=1), date__lte=today)
        return queryset.filter(date__gte=today.replace(day=1), date__lte=today)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AIAnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def recommendations(self, request):
        period = request.query_params.get("period", "month")
        card_id = request.query_params.get("card")
        payload = finance_ai_service.generate_insights(
            user=request.user,
            card_id=int(card_id) if card_id and card_id.isdigit() else None,
            period=period,
        )
        recommendations = [
            {
                "type": "warning" if item["priority"] == "high" else "info",
                "title": item["title"],
                "message": item["message"],
                "priority": item["priority"],
            }
            for item in payload["recommendations"]
        ]
        return Response(AIRecommendationSerializer(recommendations, many=True).data)

    @action(detail=False, methods=["get"])
    def forecast(self, request):
        period = request.query_params.get("period", "month")
        card_id = request.query_params.get("card")
        payload = finance_ai_service.generate_insights(
            user=request.user,
            card_id=int(card_id) if card_id and card_id.isdigit() else None,
            period=period,
        )
        return Response(
            {
                "total_forecast": payload["forecast"]["projected_expense_next_month"],
                "category_forecasts": [],
                "confidence": payload["forecast"]["confidence"],
                "based_on_months": 2,
            }
        )

    @action(detail=False, methods=["get"])
    def insights(self, request):
        period = request.query_params.get("period", "month")
        card_id = request.query_params.get("card")
        payload = finance_ai_service.generate_insights(
            user=request.user,
            card_id=int(card_id) if card_id and card_id.isdigit() else None,
            period=period,
        )
        return Response(payload["insights"])
