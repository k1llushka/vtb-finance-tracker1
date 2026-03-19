import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Avg, Sum
from django.utils import timezone
from openai import OpenAI

from cards.models import Card

from .models import Category, Transaction


LOW_CONFIDENCE_THRESHOLD = Decimal("0.70")
DEFAULT_CHAT_CACHE_TTL = 60 * 10
DEFAULT_INSIGHTS_CACHE_TTL = 60 * 15
MONTH_NAME_TO_NUMBER = {
    "январ": 1,
    "феврал": 2,
    "март": 3,
    "апрел": 4,
    "ма": 5,
    "июн": 6,
    "июл": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}
CATEGORY_KEYWORDS = {
    "кафе": ["кафе", "ресторан", "coffee", "кофе", "еда", "доставка", "пицца", "суши", "burger"],
    "транспорт": ["такси", "metro", "метро", "автобус", "бензин", "азс", "транспорт", "parking"],
    "дом": ["аренда", "квартира", "жкх", "ремонт", "ikea", "дом", "коммунал"],
    "здоровье": ["аптека", "клиника", "врач", "здоров", "мед", "pharmacy"],
    "развлечения": ["кино", "театр", "игра", "steam", "netflix", "развлеч", "concert"],
    "покупки": ["ozon", "wb", "wildberries", "market", "shop", "магазин", "одежда", "продукт"],
    "счета": ["связь", "телефон", "интернет", "подписка", "налог", "штраф", "коммунал"],
}


@dataclass
class CategorizationResult:
    category_id: int | None
    category_name: str | None
    confidence: Decimal
    rationale: str
    source: str

    @property
    def should_apply(self) -> bool:
        return self.category_id is not None and self.confidence >= LOW_CONFIDENCE_THRESHOLD


class FinanceAIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = getattr(settings, "OPENAI_FINANCE_MODEL", "gpt-5-mini")

    def categorize_expense(
        self,
        *,
        user,
        description: str,
        amount: Decimal | None = None,
        tx_date: date | None = None,
    ) -> CategorizationResult:
        description = (description or "").strip()
        if not description:
            return CategorizationResult(None, None, Decimal("0.00"), "Пустое описание.", "rule")

        categories = list(
            Category.objects.filter(user=user, type=Transaction.TYPE_EXPENSE, is_active=True).values("id", "name")
        )
        if not categories:
            return CategorizationResult(None, None, Decimal("0.00"), "Нет доступных категорий расходов.", "rule")

        heuristic_match = self._keyword_match(categories, description)
        if heuristic_match:
            return heuristic_match

        if not self.client:
            return CategorizationResult(None, None, Decimal("0.35"), "OpenAI не настроен, использован fallback.", "rule")

        cache_key = self._cache_key("categorize", user.id, description.lower())
        cached = cache.get(cache_key)
        if cached:
            return CategorizationResult(**cached)

        prompt = self._build_categorization_prompt(categories, description, amount, tx_date)
        result = self._safe_categorization_from_llm(prompt, categories)
        cache.set(cache_key, result.__dict__, timeout=60 * 60)
        return result

    def generate_insights(self, *, user, card_id: int | None = None, period: str = "month") -> dict[str, Any]:
        cache_value = f"{timezone.localdate().isoformat()}:{card_id or 'all'}:{period}"
        cache_key = self._cache_key("insights", user.id, cache_value)
        cached = cache.get(cache_key)
        if cached:
            return cached

        card = self._get_card(user, card_id)
        period_start, period_end, period_label = self._resolve_period_bounds(period)
        current_period = self._build_period_summary(
            user=user,
            period_start=period_start,
            period_end=period_end,
            card=card,
            period_label=period_label,
        )

        if period == "month":
            previous_end = period_start - timedelta(days=1)
            previous_start = previous_end.replace(day=1)
            previous_label = self._format_month_label(previous_start)
        elif period == "week":
            previous_end = period_start - timedelta(days=1)
            previous_start = previous_end - timedelta(days=6)
            previous_label = "прошлая неделя"
        else:
            previous_end = period_start - timedelta(days=1)
            previous_start = previous_end.replace(month=1, day=1)
            previous_label = "прошлый год"

        previous_period = self._build_period_summary(
            user=user,
            period_start=previous_start,
            period_end=previous_end,
            card=card,
            period_label=previous_label,
        )

        payload = {
            "period": {
                "label": current_period["label"],
                "from": current_period["period_start"].isoformat(),
                "to": current_period["period_end"].isoformat(),
                "card": self._card_label(card),
            },
            "insights": self._build_deterministic_insights(current_period, previous_period),
            "recommendations": self._build_recommendations(current_period, previous_period),
            "forecast": self._build_forecast(current_period, previous_period),
            "totals": current_period["totals"],
        }
        cache.set(cache_key, payload, timeout=DEFAULT_INSIGHTS_CACHE_TTL)
        return payload

    def answer_chat(
        self,
        *,
        user,
        message: str,
        card_id: int | None = None,
        period: str = "month",
    ) -> dict[str, Any]:
        normalized_message = (message or "").strip()
        if not normalized_message:
            return {"answer": "Напишите вопрос о расходах, доходах, балансе, бюджете или категориях.", "context": {}}

        card = self._get_card(user, card_id)
        period_start, period_end, period_label, period_code = self._resolve_chat_period(normalized_message, period)
        cache_value = f"{normalized_message.lower()}:{card_id or 'all'}:{period_code}:{period_start.isoformat()}:{period_end.isoformat()}"
        cache_key = self._cache_key("chat", user.id, cache_value)
        cached = cache.get(cache_key)
        if cached:
            return cached

        summary = self._build_period_summary(
            user=user,
            period_start=period_start,
            period_end=period_end,
            card=card,
            period_label=period_label,
        )
        context = {
            "period": {
                "label": summary["label"],
                "from": summary["period_start"].isoformat(),
                "to": summary["period_end"].isoformat(),
                "card": self._card_label(card),
            },
            "totals": summary["totals"],
            "top_expense_categories": summary["top_expense_categories"],
            "largest_expenses": summary["largest_expenses"],
        }

        answer = self._answer_with_rules(normalized_message, summary)
        if answer is None and self.client:
            answer = self._answer_with_llm(normalized_message, context)
        if answer is None:
            answer = self._fallback_summary_answer(summary)

        payload = {"answer": answer, "context": context}
        cache.set(cache_key, payload, timeout=DEFAULT_CHAT_CACHE_TTL)
        return payload

    def _build_period_summary(
        self,
        *,
        user,
        period_start: date,
        period_end: date,
        card: Card | None = None,
        period_label: str,
    ) -> dict[str, Any]:
        queryset = Transaction.objects.filter(user=user, date__gte=period_start, date__lte=period_end)
        if card:
            queryset = queryset.filter(card=card)

        income = queryset.filter(type=Transaction.TYPE_INCOME).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        expense_qs = queryset.filter(type=Transaction.TYPE_EXPENSE)
        expense = expense_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        avg_expense = expense_qs.aggregate(avg=Avg("amount"))["avg"] or Decimal("0")

        top_expense_categories = []
        if expense > 0:
            category_rows = expense_qs.values("category__name").annotate(total=Sum("amount")).order_by("-total")[:5]
            for row in category_rows:
                total = Decimal(str(row["total"]))
                share = ((total / expense) * 100).quantize(Decimal("0.1"))
                top_expense_categories.append(
                    {
                        "name": row["category__name"] or "Без категории",
                        "total": str(total.quantize(Decimal("0.01"))),
                        "share": str(share),
                    }
                )

        largest_expenses = [
            {
                "date": tx.date.isoformat(),
                "amount": str(tx.amount),
                "description": tx.description[:80],
                "category": tx.category.name if tx.category else "Без категории",
            }
            for tx in expense_qs.select_related("category").order_by("-amount")[:5]
        ]

        return {
            "label": period_label,
            "period_start": period_start,
            "period_end": period_end,
            "card_label": self._card_label(card),
            "totals": {
                "income": str(income.quantize(Decimal("0.01"))),
                "expense": str(expense.quantize(Decimal("0.01"))),
                "balance": str((income - expense).quantize(Decimal("0.01"))),
                "avg_expense": str(avg_expense.quantize(Decimal("0.01"))),
                "transactions_count": queryset.count(),
            },
            "top_expense_categories": top_expense_categories,
            "largest_expenses": largest_expenses,
        }

    def _build_deterministic_insights(self, current_period: dict[str, Any], previous_period: dict[str, Any]) -> list[dict[str, str]]:
        insights: list[dict[str, str]] = []
        current_expense = Decimal(str(current_period["totals"]["expense"]))
        previous_expense = Decimal(str(previous_period["totals"]["expense"]))

        if current_period["top_expense_categories"]:
            top_category = current_period["top_expense_categories"][0]
            insights.append(
                {
                    "title": "Главная категория",
                    "value": f"{top_category['total']} ₽",
                    "description": f"{top_category['name']} занимает {top_category['share']}% расходов.",
                    "icon": "bi-pie-chart-fill",
                }
            )

        if previous_expense > 0:
            diff = (((current_expense - previous_expense) / previous_expense) * 100).quantize(Decimal("0.1"))
            insights.append(
                {
                    "title": "Сравнение с прошлым периодом",
                    "value": f"{diff}%",
                    "description": "Изменение расходов по сравнению с предыдущим сопоставимым периодом.",
                    "icon": "bi-graph-up-arrow",
                }
            )

        insights.append(
            {
                "title": "Средний чек",
                "value": f"{current_period['totals']['avg_expense']} ₽",
                "description": "Средняя сумма одной расходной транзакции.",
                "icon": "bi-receipt-cutoff",
            }
        )
        insights.append(
            {
                "title": "Баланс периода",
                "value": f"{current_period['totals']['balance']} ₽",
                "description": f"Доходы минус расходы. Карта: {current_period['card_label']}.",
                "icon": "bi-wallet2",
            }
        )
        return insights

    def _build_recommendations(self, current_period: dict[str, Any], previous_period: dict[str, Any]) -> list[dict[str, str]]:
        recommendations: list[dict[str, str]] = []
        current_expense = Decimal(str(current_period["totals"]["expense"]))
        previous_expense = Decimal(str(previous_period["totals"]["expense"]))
        current_income = Decimal(str(current_period["totals"]["income"]))

        if current_period["top_expense_categories"]:
            top_category = current_period["top_expense_categories"][0]
            suggested_saving = (Decimal(str(top_category["total"])) * Decimal("0.20")).quantize(Decimal("0.01"))
            recommendations.append(
                {
                    "title": "Где можно сэкономить",
                    "message": f"Если сократить расходы на {top_category['name']} на 20%, можно сохранить около {suggested_saving} ₽.",
                    "priority": "medium",
                }
            )

        if previous_expense > 0 and current_expense > previous_expense:
            growth = (((current_expense - previous_expense) / previous_expense) * 100).quantize(Decimal("0.1"))
            recommendations.append(
                {
                    "title": "Расходы выросли",
                    "message": f"Расходы выросли на {growth}% относительно прошлого периода. Проверьте крупные и повторяющиеся траты.",
                    "priority": "high",
                }
            )

        if current_income > 0:
            savings_rate = (((current_income - current_expense) / current_income) * 100).quantize(Decimal("0.1"))
            if savings_rate < Decimal("20.0"):
                recommendations.append(
                    {
                        "title": "Низкая норма накоплений",
                        "message": f"Сейчас вы сохраняете около {savings_rate}% дохода. Хорошая цель на месяц - хотя бы 20%.",
                        "priority": "medium",
                    }
                )

        if Decimal(str(current_period["totals"]["balance"])) < 0:
            recommendations.append(
                {
                    "title": "Баланс ушёл в минус",
                    "message": "В этом периоде расходы превысили доходы. Стоит ограничить необязательные категории и крупные покупки.",
                    "priority": "high",
                }
            )

        return recommendations

    def _build_forecast(self, current_period: dict[str, Any], previous_period: dict[str, Any]) -> dict[str, Any]:
        current_expense = Decimal(str(current_period["totals"]["expense"]))
        previous_expense = Decimal(str(previous_period["totals"]["expense"]))
        projected = ((current_expense + previous_expense) / 2).quantize(Decimal("0.01")) if previous_expense > 0 else current_expense
        return {
            "projected_expense_next_month": str(projected),
            "confidence": "medium" if previous_expense > 0 else "low",
            "method": "Среднее текущего и предыдущего сопоставимого периода.",
        }

    def _answer_with_rules(self, message: str, summary: dict[str, Any]) -> str | None:
        lower = message.lower()
        totals = summary["totals"]
        top_categories = summary["top_expense_categories"]
        card_tail = f" по карте {summary['card_label']}" if summary["card_label"] != "Все карты" else ""

        if any(word in lower for word in ("анализ", "отчет", "отчёт", "сводк", "покажи")):
            leader = top_categories[0]["name"] if top_categories else "нет выраженного лидера"
            return (
                f"За {summary['label']}{card_tail}: доходы {totals['income']} ₽, расходы {totals['expense']} ₽, "
                f"баланс {totals['balance']} ₽. Крупнейшая категория расходов: {leader}."
            )

        if any(word in lower for word in ("сколько", "потрат", "расход")) and any(word in lower for word in ("еда", "еду", "продукт", "кафе", "ресторан")):
            return self._category_total_answer(summary, {"еда", "кафе", "продукт", "ресторан"}, "на еду и кафе")

        if any(word in lower for word in ("транспорт", "такси", "метро", "бензин")):
            return self._category_total_answer(summary, {"транспорт", "такси", "метро", "бензин"}, "на транспорт")

        if any(word in lower for word in ("связь", "интернет", "телефон", "подписк")):
            return self._category_total_answer(summary, {"связь", "интернет", "телефон", "подписк"}, "на связь и подписки")

        if any(word in lower for word in ("доход", "заработ", "зарплат")):
            return f"За {summary['label']}{card_tail} доходы составили {totals['income']} ₽."

        if "баланс" in lower:
            return f"Баланс за {summary['label']}{card_tail}: {totals['balance']} ₽."

        if any(word in lower for word in ("улучш", "улучши", "бюджет", "сэконом", "эконом")):
            if top_categories:
                top = top_categories[0]
                saving = (Decimal(top["total"]) * Decimal("0.20")).quantize(Decimal("0.01"))
                return (
                    f"Сейчас больше всего уходит на {top['name']} - {top['total']} ₽. "
                    f"Если сократить эту категорию на 20%, можно сэкономить около {saving} ₽."
                )
            return "Для рекомендаций по бюджету нужно больше расходных данных за выбранный период."

        if any(word in lower for word in ("снизить расходы", "уменьшить расходы", "как сэкономить")):
            if top_categories:
                lines = [f"1. Сначала проверьте категорию «{top_categories[0]['name']}» - это главный источник трат."]
                if len(top_categories) > 1:
                    lines.append(f"2. Затем посмотрите «{top_categories[1]['name']}» как вторую по объёму категорию.")
                lines.append("3. Начните с сокращения необязательных и повторяющихся покупок, а не базовых платежей.")
                return " ".join(lines)
            return "Пока недостаточно данных, чтобы подсказать, где лучше снижать расходы."

        if any(word in lower for word in ("прогноз", "следующ", "месяц")):
            current = Decimal(totals["expense"])
            return f"Если структура трат не изменится, ориентир на следующий период{card_tail}: около {current.quantize(Decimal('0.01'))} ₽ расходов."

        if any(word in lower for word in ("крупн", "больш", "максим")) and any(word in lower for word in ("трат", "покуп", "расход")):
            if summary["largest_expenses"]:
                top = summary["largest_expenses"][0]
                return f"Самая крупная трата за {summary['label']}{card_tail}: {top['amount']} ₽, категория {top['category']}, дата {top['date']}."
            return "Крупных расходов за выбранный период не найдено."

        return None

    def _category_total_answer(self, summary: dict[str, Any], keywords: set[str], title: str) -> str:
        total = Decimal("0.00")
        matched_categories = []
        for category in summary["top_expense_categories"]:
            category_name = category["name"].lower()
            if any(keyword in category_name for keyword in keywords):
                total += Decimal(category["total"])
                matched_categories.append(category["name"])

        if total > 0:
            categories_text = ", ".join(matched_categories)
            return f"За {summary['label']} потрачено {total.quantize(Decimal('0.01'))} ₽ {title}. Категории: {categories_text}."
        return f"За {summary['label']} я не нашёл расходов {title}."

    def _answer_with_llm(self, message: str, context: dict[str, Any]) -> str | None:
        try:
            response = self.client.responses.create(
                model=self.model,
                temperature=0,
                input=(
                    "Ты AI-ассистент финансового трекера.\n"
                    "Отвечай только на основе контекста.\n"
                    "Если данных недостаточно, честно скажи об этом.\n"
                    "Не придумывай транзакции, суммы, карты и категории.\n"
                    "Отвечай кратко, полезно и по-русски.\n\n"
                    f"Контекст: {json.dumps(context, ensure_ascii=False)}\n"
                    f"Вопрос пользователя: {message}"
                ),
            )
            return response.output_text.strip()
        except Exception:
            return None

    def _fallback_summary_answer(self, summary: dict[str, Any]) -> str:
        totals = summary["totals"]
        return (
            f"За {summary['label']} расходы составили {totals['expense']} ₽, "
            f"доходы {totals['income']} ₽, баланс {totals['balance']} ₽."
        )

    def _safe_categorization_from_llm(self, prompt: str, categories: list[dict[str, Any]]) -> CategorizationResult:
        try:
            response = self.client.responses.create(
                model=self.model,
                temperature=0,
                input=prompt,
                text={"format": {"type": "json_object"}},
            )
            data = json.loads(response.output_text)
        except Exception:
            return CategorizationResult(None, None, Decimal("0.00"), "Не удалось получить ответ модели.", "llm")

        category_id = data.get("category_id")
        confidence = Decimal(str(data.get("confidence", "0"))).quantize(Decimal("0.01"))
        rationale = str(data.get("rationale", ""))
        category_name = next((item["name"] for item in categories if item["id"] == category_id), None)

        if category_name is None:
            return CategorizationResult(None, None, Decimal("0.00"), "Модель не выбрала допустимую категорию.", "llm")
        return CategorizationResult(category_id, category_name, confidence, rationale, "llm")

    def _build_categorization_prompt(self, categories: list[dict[str, Any]], description: str, amount: Decimal | None, tx_date: date | None) -> str:
        return (
            "Ты классифицируешь пользовательский расход.\n"
            "Ответь только JSON-объектом вида "
            '{"category_id": number|null, "confidence": number, "rationale": "string"}.\n'
            "Правила:\n"
            "- Выбирай category_id только из списка ниже.\n"
            "- Если уверенность ниже 0.70, верни category_id=null.\n"
            "- Не придумывай новые категории.\n"
            "- Учитывай только описание, сумму и дату.\n\n"
            f"Категории: {json.dumps(categories, ensure_ascii=False)}\n"
            f"Описание: {description}\n"
            f"Сумма: {amount if amount is not None else 'unknown'}\n"
            f"Дата: {tx_date.isoformat() if tx_date else 'unknown'}"
        )

    def _keyword_match(self, categories: list[dict[str, Any]], description: str) -> CategorizationResult | None:
        lowered = description.lower()
        category_lookup = {item["name"].lower(): item for item in categories}
        for base_name, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                for category_name, category in category_lookup.items():
                    if base_name in category_name:
                        return CategorizationResult(
                            category_id=category["id"],
                            category_name=category["name"],
                            confidence=Decimal("0.84"),
                            rationale="Категория определена по ключевым словам в описании.",
                            source="rule",
                        )
        return None

    def _period_from_message(self, message: str) -> str | None:
        lowered = message.lower()
        if "недел" in lowered:
            return "week"
        if "год" in lowered:
            return "year"
        if "меся" in lowered or any(stem in lowered for stem in MONTH_NAME_TO_NUMBER):
            return "month"
        return None

    def _resolve_chat_period(self, message: str, fallback_period: str) -> tuple[date, date, str, str]:
        lowered = message.lower()
        today = timezone.localdate()

        if "прошл" in lowered and "меся" in lowered:
            month_end = today.replace(day=1) - timedelta(days=1)
            month_start = month_end.replace(day=1)
            return month_start, month_end, self._format_month_label(month_start), "month"

        for stem, month_number in MONTH_NAME_TO_NUMBER.items():
            if stem in lowered:
                year_match = re.search(r"(20\d{2})", lowered)
                year = int(year_match.group(1)) if year_match else today.year
                month_start = date(year, month_number, 1)
                next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
                month_end = min(next_month - timedelta(days=1), today) if year == today.year and month_number == today.month else next_month - timedelta(days=1)
                return month_start, month_end, self._format_month_label(month_start), "month"

        period_code = self._period_from_message(message) or fallback_period
        start, end, label = self._resolve_period_bounds(period_code)
        return start, end, label, period_code

    def _resolve_period_bounds(self, period: str) -> tuple[date, date, str]:
        today = timezone.localdate()
        if period == "week":
            start = today - timedelta(days=today.weekday())
            return start, today, "текущую неделю"
        if period == "year":
            start = today.replace(month=1, day=1)
            return start, today, f"{today.year} год"
        start = today.replace(day=1)
        return start, today, self._format_month_label(start)

    def _format_month_label(self, month_start: date) -> str:
        month_names = ["", "январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
        return f"{month_names[month_start.month]} {month_start.year}"

    def _get_card(self, user, card_id: int | None) -> Card | None:
        if not card_id:
            return None
        return Card.objects.filter(user=user, id=card_id).first()

    def _card_label(self, card: Card | None) -> str:
        if not card:
            return "Все карты"
        return f"{card.bank_name} - **** {card.card_number[-4:]}"

    def _cache_key(self, prefix: str, user_id: int, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return f"finance_ai:{prefix}:{user_id}:{digest}"


finance_ai_service = FinanceAIService()
