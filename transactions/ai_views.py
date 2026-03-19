from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_services import LOW_CONFIDENCE_THRESHOLD, finance_ai_service


class CategorizeRequestSerializer(serializers.Serializer):
    description = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    date = serializers.DateField(required=False)


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()


class CategorizeExpenseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CategorizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = finance_ai_service.categorize_expense(
            user=request.user,
            description=serializer.validated_data["description"],
            amount=serializer.validated_data.get("amount"),
            tx_date=serializer.validated_data.get("date"),
        )
        return Response(
            {
                "category_id": result.category_id if result.should_apply else None,
                "category_name": result.category_name if result.should_apply else None,
                "confidence": str(result.confidence),
                "threshold": str(LOW_CONFIDENCE_THRESHOLD),
                "applied": result.should_apply,
                "rationale": result.rationale,
                "source": result.source,
            }
        )


class FinancialInsightsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        card_id = request.query_params.get("card")
        period = request.query_params.get("period", "month")
        return Response(
            finance_ai_service.generate_insights(
                user=request.user,
                card_id=int(card_id) if card_id and card_id.isdigit() else None,
                period=period,
            )
        )


class AIChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        card_id = request.data.get("card")
        period = request.data.get("period", "month")
        return Response(
            finance_ai_service.answer_chat(
                user=request.user,
                message=serializer.validated_data["message"],
                card_id=int(card_id) if str(card_id).isdigit() else None,
                period=period,
            )
        )
