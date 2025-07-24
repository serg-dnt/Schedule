from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics,  status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
from collections import defaultdict
from booking.permissions import IsTelegramDoctor

from .models import Service, AvailableSlot, Appointment
from .serializers import (
    ServiceSerializer,
    SlotSerializer,
    AppointmentSerializer,
    AppointmentCreateSerializer,
)

User = get_user_model()


class ServiceListView(generics.ListAPIView):
    """Список всех услуг"""
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsTelegramDoctor]


class AvailableSlotsView(APIView):
    """Получение свободных слотов для услуги (учитывая длительность)"""
    permission_classes = [IsTelegramDoctor]

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
    """Создание записи на приём"""
    permission_classes = [IsTelegramDoctor]

    def post(self, request):
        serializer = AppointmentCreateSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            appointment = serializer.save(patient=request.user)
            return Response(AppointmentSerializer(appointment).data, status=201)
        return Response(serializer.errors, status=400)


class CancelAppointmentView(APIView):
    """Отмена своей записи"""
    permission_classes = [IsTelegramDoctor]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(id=pk)
        except Appointment.DoesNotExist:
            return Response({'error': 'Запись не найдена'}, status=404)

        if request.user != appointment.patient and not request.user.is_doctor:
            return Response({'error': 'Нет доступа'}, status=403)

        # Освобождаем связанные слоты
        appointment.slots.update(is_booked=False)
        appointment.status = 'cancelled'
        appointment.save()
        return Response({'status': 'Запись отменена'})


class MyAppointmentsView(generics.ListAPIView):
    """Получение всех своих записей (пациент)"""
    serializer_class = AppointmentSerializer
    permission_classes = [IsTelegramDoctor]

    def get_queryset(self):
        return Appointment.objects.filter(
            patient=self.request.user).order_by('start_datetime'
        )


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
            is_booked=False
        ).order_by("start_datetime")

        return Response(SlotSerializer(slots, many=True).data)


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
            doctor=request.user).order_by('start_datetime'
        )
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
            .filter(doctor=request.user)
            .values_list('start_datetime__date', flat=True)
            .distinct()
        )
        return Response(sorted(set(str(date) for date in dates)))


class SlotFreeDatesView(APIView):
    """Получение дат, на которые у врача есть свободные слоты"""
    permission_classes = [IsTelegramDoctor]

    def get(self, request):
        if not request.user.is_doctor:
            return Response({"error": "Доступ запрещён"}, status=403)

        dates = (
            AvailableSlot.objects
            .filter(doctor=request.user, is_booked=False)
            .values_list('start_datetime__date', flat=True)
            .distinct()
        )
        return Response(sorted(set(str(date) for date in dates)))


class DoctorSlotsView(APIView):
    """Получение всех слотов врача"""
    permission_classes = [IsTelegramDoctor]

    def get(self, request):
        if not request.user.is_doctor:
            return Response({"error": "Доступ запрещён"}, status=403)

        slots = AvailableSlot.objects.filter(
            doctor=request.user
        ).order_by('start_datetime')
        serializer = SlotSerializer(slots, many=True)
        return Response(serializer.data)


# class SlotDeleteView(APIView):
#     """Удаление свободного слота врачом"""
#     permission_classes = [IsAuthenticated]
#
#     def delete(self, request, pk):
#         try:
#             slot = AvailableSlot.objects.get(
#                 id=pk, doctor=request.user, is_booked=False
#             )
#         except AvailableSlot.DoesNotExist:
#             return Response(
#                 {"error": "Слот не найден или уже занят"}, status=404
#             )
#
#         slot.delete()
#         return Response({"status": "Слот удалён"})


class DoctorSlotsView(APIView):
    permission_classes = [IsTelegramDoctor]

    def get(self, request):
        slots = AvailableSlot.objects.filter(
            doctor=request.user
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
