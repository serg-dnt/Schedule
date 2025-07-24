from rest_framework.permissions import BasePermission
from booking.models import User

class IsTelegramDoctor(BasePermission):
    def has_permission(self, request, view):
        telegram_id = request.headers.get("X-Telegram-ID")
        if not telegram_id:
            return False
        try:
            user = User.objects.get(telegram_id=telegram_id, is_doctor=True)
            request.user = user  # вручную привязываем пользователя
            return True
        except User.DoesNotExist:
            return False