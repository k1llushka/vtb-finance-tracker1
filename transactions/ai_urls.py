from django.urls import path

from .ai_views import AIChatAPIView, CategorizeExpenseAPIView, FinancialInsightsAPIView


urlpatterns = [
    path("categorize", CategorizeExpenseAPIView.as_view(), name="categorize"),
    path("insights", FinancialInsightsAPIView.as_view(), name="insights"),
    path("chat", AIChatAPIView.as_view(), name="chat"),
]
