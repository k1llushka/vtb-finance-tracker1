from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, api_views

app_name = 'transactions'

# API Router
router = DefaultRouter()
router.register(r'api/transactions', api_views.TransactionViewSet, basename='api-transaction')
router.register(r'api/categories', api_views.CategoryViewSet, basename='api-category')
router.register(r'api/budgets', api_views.BudgetViewSet, basename='api-budget')
router.register(r'api/ai', api_views.AIAnalyticsViewSet, basename='api-ai')

urlpatterns = [
    # Web Views
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('list/', views.TransactionListView.as_view(), name='list'),
    path('add/', views.TransactionCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', views.TransactionUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='delete'),

    # Категории
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_add'),

    # API
    path('', include(router.urls)),
]