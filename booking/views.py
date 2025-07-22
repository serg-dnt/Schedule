from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta, datetime
from collections import defaultdict
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import TelegramAuthSerializer

from .models import Service, AvailableSlot, Appointment
from .serializers import (
    ServiceSerializer,
    SlotSerializer,
    AppointmentSerializer,
    AppointmentCreateSerializer,
)

class ServiceListView(generics.ListAPIView):
    """Список всех услуг"""
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]


class AvailableSlotsView(APIView):
    """Получение свободных слотов для услуги (учитывая длительность)"""
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(
            patient=self.request.user).order_by('start_datetime'
        )


class CreateSlotsView(APIView):
    """Массовое создание слотов для врача"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_doctor:
            return Response({"error": "Доступ запрещён"}, status=403)

        day = request.data.get('day')  # YYYY-MM-DD
        start_time = request.data.get('start_time')  # HH:MM
        end_time = request.data.get('end_time')      # HH:MM
        step = int(request.data.get('slot_length_minutes', 30))

        if not all([day, start_time, end_time]):
            return Response(
                {"error": "Необходимо указать day, start_time и end_time"},
                status=400
            )

        try:
            date_obj = datetime.strptime(day, "%Y-%m-%d").date()
            start = datetime.combine(
                date_obj, datetime.strptime(start_time, "%H:%M").time()
            )
            end = datetime.combine(
                date_obj, datetime.strptime(end_time, "%H:%M").time()
            )
        except ValueError:
            return Response(
                {"error": "Неверный формат даты/времени"}, status=400
            )

        created = []
        current = start
        while current + timedelta(minutes=step) <= end:
            conflict = AvailableSlot.objects.filter(
                doctor=request.user,
                start_datetime__lt=current + timedelta(minutes=step),
                end_datetime__gt=current
            ).exists()

            if not conflict:
                slot = AvailableSlot.objects.create(
                    doctor=request.user,
                    start_datetime=current,
                    end_datetime=current + timedelta(minutes=step),
                    is_booked=False
                )
                created.append(slot)
            current += timedelta(minutes=step)

        return Response(SlotSerializer(created, many=True).data)


class DoctorAppointmentsView(APIView):
    """Получение всех записей врача"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_doctor:
            return Response({"error": "Доступ запрещён"}, status=403)

        appointments = Appointment.objects.filter(
            doctor=request.user).order_by('start_datetime'
        )
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)


class SlotDeleteView(APIView):
    """Удаление свободного слота врачом"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            slot = AvailableSlot.objects.get(
                id=pk, doctor=request.user, is_booked=False
            )
        except AvailableSlot.DoesNotExist:
            return Response(
                {"error": "Слот не найден или уже занят"}, status=404
            )

        slot.delete()
        return Response({"status": "Слот удалён"})


class TelegramAuthView(APIView):
    def post(self, request):
        serializer = TelegramAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        })
