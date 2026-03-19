from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from transactions.models import Category, Transaction


User = get_user_model()


class AIApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("ai-user", password="12345")
        self.client.force_authenticate(self.user)
        self.food_category = Category.objects.create(
            user=self.user,
            name="Кафе и еда",
            type="expense",
            color="#ff6600",
        )
        self.transport_category = Category.objects.create(
            user=self.user,
            name="Транспорт",
            type="expense",
            color="#0066ff",
        )
        Transaction.objects.create(
            user=self.user,
            category=self.food_category,
            type="expense",
            amount=Decimal("1500.00"),
            description="Кофе и обед",
            date=date(2026, 3, 10),
        )
        Transaction.objects.create(
            user=self.user,
            category=self.transport_category,
            type="expense",
            amount=Decimal("800.00"),
            description="Такси домой",
            date=date(2026, 3, 11),
        )
        Transaction.objects.create(
            user=self.user,
            type="income",
            amount=Decimal("120000.00"),
            description="Зарплата",
            date=date(2026, 3, 5),
        )

    def test_categorize_endpoint_uses_safe_keyword_fallback(self):
        response = self.client.post(
            "/ai/categorize",
            {"description": "Ужин в кафе рядом с офисом", "amount": "900.00", "date": "2026-03-12"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["applied"])
        self.assertEqual(response.data["category_name"], "Кафе и еда")

    def test_insights_endpoint_returns_structured_payload(self):
        response = self.client.get("/ai/insights")

        self.assertEqual(response.status_code, 200)
        self.assertIn("insights", response.data)
        self.assertIn("recommendations", response.data)
        self.assertIn("forecast", response.data)

    def test_chat_endpoint_answers_from_user_data(self):
        response = self.client.post("/ai/chat", {"message": "Сколько я потратил на еду?"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("answer", response.data)
        self.assertIn("ед", response.data["answer"].lower())
