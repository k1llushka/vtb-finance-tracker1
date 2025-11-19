from django.urls import path
from . import views

app_name = 'cards'

urlpatterns = [
    path('', views.CardListView.as_view(), name='card_list'),
    path('create/', views.CardCreateView.as_view(), name='card_create'),
    path('<int:pk>/', views.CardDetailView.as_view(), name='card_detail'),
]