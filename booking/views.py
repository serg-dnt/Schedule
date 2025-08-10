from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime, date
from collections import defaultdict
from booking.permissions import IsTelegramDoctor
from rest_framework.generics import RetrieveAPIView
import logging

from .models import Service, AvailableSlot, Appointment
from .serializers import (
    ServiceSerializer,
    SlotSerializer,
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentCancelSerializer,
    DoctorShortSerializer, TelegramAuthSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class DoctorListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        doctors = User.objects.filter(is_doctor=True, is_doctor_approved=True)
        serializer = DoctorShortSerializer(doctors, many=True)
        logger.info(f"Возвращено {len(doctors)} докторов")
        return Response(serializer.data)


class ServiceListView(generics.ListAPIView):
    """Список всех услуг"""
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsTelegramDoctor]


class DoctorServicesView(APIView):
    """Получение списка услуг конкретного доктора по его ID."""
    permission_classes = [AllowAny] # ПОЗЖЕ ПОПРАВИТЬ

    def get(self, request):
        doctor_id = request.query_params.get('doctor_id')
        if not doctor_id:
            return Response({"error": "doctor_id is requiered"}, status=400)

        services = Service.objects.filter(doctor_id=doctor_id)
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)


class AvailableSlotsView(APIView):
    """Получение свободных слотов для услуги (учитывая длительность)"""
    permission_classes = [AllowAny]

    def get(self, request):
        service_id = request.query_params.get('service_id')
        doctor_id = request.query_params.get('doctor_id')

        if not service_id or not doctor_id:
            return Response(
                {"error": "service_id и doctor_id обязательны"}, status=400
            )

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return Response({"error": "Услуга не найдена"}, status=404)

        duration = timedelta(minutes=service.duration_minutes)
        now = timezone.now()

        all_slots = AvailableSlot.objects.filter(
            doctor_id=doctor_id,
            is_booked=False,
            start_datetime__gte=now
        ).order_by('start_datetime')

        # Группируем слоты по дате
        slots_by_day = defaultdict(list)
        for slot in all_slots:
            date = slot.start_datetime.date()
            slots_by_day[date].append(slot)

        result = []
        for day, slots in slots_by_day.items():
            i = 0
            while i <= len(slots) - 1:
                start_slot = slots[i]
                end_time = start_slot.start_datetime + duration
                combined = [start_slot]
                j = i + 1
                while j < len(slots) and slots[j].start_datetime == combined[-1].end_datetime:
                    combined.append(slots[j])
                    if combined[-1].end_datetime == end_time:
                        result.append(SlotSerializer(start_slot).data)
                        break
                    j += 1
                i += 1

        return Response(result)


class AppointmentCreateView(APIView):
    """Создание записи на приём через Telegram"""

    permission_classes = [AllowAny]  # Позже можно заменить на custom-permission по Telegram ID

    def post(self, request):
        serializer = AppointmentCreateSerializer(
            data=request.data
        )
        if serializer.is_valid():
            appointment = serializer.save()
            return Response(AppointmentSerializer(appointment).data, status=201)
        return Response(serializer.errors, status=400)


class AppointmentCancelView(APIView):
    permission_classes = [AllowAny]  # позже можно ограничить доступ

    def post(self, request):
        telegram_id = request.headers.get("X-Telegram-ID")
        if not telegram_id:
            return Response({"error": "Отсутствует Telegram ID"}, status=400)

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)

        serializer = AppointmentCancelSerializer(
            data=request.data,
            context={"user": user}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Записи успешно отменены."}, status=200)

        return Response(serializer.errors, status=400)


class SlotsListView(APIView):
    permission_classes = [IsTelegramDoctor]

    def get(self, request):
        if not request.user.is_doctor:
            return Response({"error": "Доступ запрещён"}, status=403)

        date_str = request.query_params.get("date")
        if not date_str:
            return Response({"error": "Параметр 'date' обязателен"}, status=400)

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Неверный формат даты"}, status=400)

        slots = AvailableSlot.objects.filter(
            doctor=request.user,
            start_datetime__date=date_obj,
            # is_booked=False
        ).order_by("start_datetime")

        return Response(SlotSerializer(slots, many=True).data)


class SlotDetailAPIView(RetrieveAPIView):
    queryset = AvailableSlot.objects.all()
    serializer_class = SlotSerializer
    permission_classes = [AllowAny]


class CreateSlotsView(APIView):
    """Создание слотов на основе переданных start/end_datetime"""
    permission_classes = [IsTelegramDoctor]

    def post(self, request):
        if not request.user.is_doctor:
            return Response({"error": "Доступ запрещён"}, status=403)

        slots = request.data.get("slots")
        if not slots or not isinstance(slots, list):
            return Response({"error": "Ожидался список слотов"}, status=400)

        created = []
        for slot_data in slots:
            try:
                start = datetime.fromisoformat(slot_data["start_datetime"])
                end = datetime.fromisoformat(slot_data["end_datetime"])
            except (KeyError, ValueError):
                return Response({"error": "Неверный формат времени в слоте"}, status=400)

            if start >= end:
                continue  # Пропускаем некорректные интервалы

            conflict = AvailableSlot.objects.filter(
                doctor=request.user,
                start_datetime__lt=end,
                end_datetime__gt=start
            ).exists()

            if not conflict:
                slot = AvailableSlot.objects.create(
                    doctor=request.user,
                    start_datetime=start,
                    end_datetime=end,
                    is_booked=False
                )
                created.append(slot)

        return Response(SlotSerializer(created, many=True).data, status=201)


class DoctorAppointmentsView(APIView):
    """Получение всех записей врача"""
    permission_classes = [IsTelegramDoctor]

    def get(self, request):
        if not request.user.is_doctor:
            return Response({"error": "Доступ запрещён"}, status=403)

        appointments = Appointment.objects.filter(
            doctor=request.user,
            status='active'
        ).order_by('start_datetime')
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)


class AppointmentDatesView(APIView):
    """Получение дат, на которые у врача есть записи"""
    permission_classes = [IsTelegramDoctor]

    def get(self, request):
        if not request.user.is_doctor:
            return Response({"error": "Доступ запрещён"}, status=403)

        dates = (
            Appointment.objects
            .filter(doctor=request.user, status='active')
            .values_list('start_datetime__date', flat=True)
            .distinct()
        )
        return Response(sorted(set(str(date) for date in dates)))


class SlotFreeDatesView(APIView):
    """Получение дат, на которые у врача есть свободные слоты"""
    permission_classes = [AllowAny]
    def get(self, request):
        doctor_id = request.query_params.get("doctor_id")
        service_id = request.query_params.get("service_id")

        if not doctor_id:
            return Response(
                {"error": "doctor_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        slots = AvailableSlot.objects.filter(
            doctor_id=doctor_id,
            start_datetime__date__gte=date.today(),
            # is_booked=False
        ).order_by("start_datetime")

        if not service_id:
            # Просто вернуть уникальные даты, где есть хотя бы один слот
            dates = sorted(
                set(slot.start_datetime.date() for slot in slots))
            return Response({"dates": [str(d) for d in dates]})

        # Ниже — логика для пациента (фильтрация по длительности услуги)
        try:
            service = Service.objects.get(pk=service_id)
            duration = service.duration
        except Service.DoesNotExist:
            return Response(
                {"error": "Service not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Группировка по дате
        grouped = {}
        for slot in slots:
            slot_date = slot.start_datetime.date()
            grouped.setdefault(slot_date, []).append(slot)

        valid_dates = []
        needed = duration // 15
        for slot_date, slot_list in grouped.items():
            slot_list = sorted(slot_list, key=lambda s: s.start_datetime)
            for i in range(len(slot_list) - needed + 1):
                chunk = slot_list[i:i + needed]
                ok = all(
                    (chunk[j + 1].start_datetime - chunk[
                        j].start_datetime).total_seconds() == 15 * 60
                    for j in range(len(chunk) - 1)
                )
                if ok:
                    valid_dates.append(str(slot_date))
                    break

        return Response({"dates": sorted(valid_dates)})


class DoctorSlotsView(APIView):
    """Получение всех слотов врача"""
    permission_classes = [IsTelegramDoctor]

    def get(self, request):
        if not request.user.is_doctor:
            return Response({"error": "Доступ запрещён"}, status=403)

        slots = AvailableSlot.objects.filter(
            doctor=request.user,
            is_booked=False
        ).order_by('start_datetime')
        serializer = SlotSerializer(slots, many=True)
        return Response(serializer.data)


class DeleteSlotsView(APIView):
    permission_classes = [IsTelegramDoctor]

    def delete(self, request):
        slot_ids = request.data.get("slot_ids", [])
        if not isinstance(slot_ids, list) or not all(isinstance(id, int) for id in slot_ids):
            return Response({"error": "Некорректный формат slot_ids"}, status=400)

        # Удаляем только слоты, которые принадлежат текущему врачу и ещё не заняты
        slots = AvailableSlot.objects.filter(id__in=slot_ids, doctor=request.user, is_booked=False)
        deleted_count = slots.count()
        slots.delete()

        return Response({"deleted": deleted_count}, status=204)


class PatientAppointmentsView(APIView):
    """Список записей пациента по Telegram ID"""
    permission_classes = [AllowAny]

    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        if not telegram_id:
            return Response({"error": "Telegram ID обязателен"}, status=400)

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)

        appointments = Appointment.objects.filter(patient=user, status="active").select_related("doctor", "service")
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)


class TelegrammAuthView(APIView):

    def post(self, request):
        serializer = TelegramAuthSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "ok"},  status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckUserExistsView(APIView):
    def get(self, request, telegram_id):
        exists = User.objects.filter(telegram_id=telegram_id).exists()
        return Response(
            {"exists": exists},
            status=status.HTTP_200_OK if exists else status.HTTP_404_NOT_FOUND
        )


class CheckIsDoctorView(APIView):
    def get(self, request, telegram_id):
        is_doctor = User.objects.filter(telegram_id=telegram_id, is_doctor=True).exists()
        return Response(
            {"is_doctor": is_doctor},
            status=status.HTTP_200_OK if is_doctor else status.HTTP_404_NOT_FOUND
        )



class DoctorByTelegramIDAPIView(APIView):
    def get(self, request):
        telegram_id = request.headers.get("X-Telegram-ID")
        if not telegram_id:
            return Response({"detail": "Missing X-Telegram-ID header."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            doctor = User.objects.get(telegram_id=telegram_id, is_doctor=True)
        except User.DoesNotExist:
            return Response({"detail": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(DoctorShortSerializer(doctor).data)