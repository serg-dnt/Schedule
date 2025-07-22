from rest_framework import serializers
from .models import Service, AvailableSlot, Appointment, User
from datetime import timedelta


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'duration_minutes', 'price']


class SlotSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(
        source='doctor.full_name', read_only=True
    )

    class Meta:
        model = AvailableSlot
        fields = [
            'id',
            'doctor',
            'doctor_name',
            'start_datetime',
            'end_datetime',
            'is_booked'
        ]


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(
        source='doctor.full_name', read_only=True
    )
    patient_name = serializers.CharField(
        source='patient.full_name', read_only=True
    )
    service_name = serializers.CharField(
        source='service.name', read_only=True
    )

    class Meta:
        model = Appointment
        fields = [
            'id',
            'doctor',
            'doctor_name',
            'patient',
            'patient_name',
            'service',
            'service_name',
            'start_datetime',
            'end_datetime',
            'status',
            'created_at',
        ]


class AppointmentCreateSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    service_id = serializers.IntegerField()
    start_datetime = serializers.DateTimeField()

    def validate(self, data):
        doctor_id = data['doctor_id']
        service_id = data['service_id']
        start_datetime = data['start_datetime']

        # Валидация доктора
        try:
            doctor = User.objects.get(id=doctor_id, is_doctor=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Доктор не найден")

        # Валидация услуги
        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError("Услуга не найдена")

        needed_duration = timedelta(minutes=service.duration_minutes)

        # Найти свободные слоты, начиная с нужного времени
        available_slots = AvailableSlot.objects.filter(
            doctor=doctor,
            start_datetime__gte=start_datetime,
            is_booked=False
        ).order_by('start_datetime')

        selected_slots = []
        total_duration = timedelta()

        for slot in available_slots:
            if not selected_slots:
                # Первый слот должен начинаться в заданное время
                if slot.start_datetime != start_datetime:
                    continue
                selected_slots.append(slot)
                total_duration += slot.end_datetime - slot.start_datetime
            else:
                # Следующий слот должен начинаться сразу после предыдущего
                last = selected_slots[-1]
                if slot.start_datetime == last.end_datetime:
                    selected_slots.append(slot)
                    total_duration += slot.end_datetime - slot.start_datetime
                else:
                    break  # последовательность оборвана

            if total_duration >= needed_duration:
                break

        if total_duration < needed_duration:
            raise serializers.ValidationError(
                "Недостаточно свободных подряд слотов на указанную услугу"
            )

        data['doctor'] = doctor
        data['service'] = service
        data['selected_slots'] = selected_slots
        data['end_datetime'] = selected_slots[-1].end_datetime
        return data

    def create(self, validated_data):
        doctor = validated_data['doctor']
        service = validated_data['service']
        patient = self.context['request'].user
        start_datetime = validated_data['start_datetime']
        end_datetime = validated_data['end_datetime']
        slots_to_book = validated_data['selected_slots']

        # Бронируем слоты
        for slot in slots_to_book:
            slot.is_booked = True
            slot.save()

        appointment = Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            service=service,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status='active'
        )
        return appointment


class TelegramAuthSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    full_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)

    def create(self, validated_data):
        telegram_id = validated_data['telegram_id']
        user, created = User.objects.get_or_create(telegram_id=telegram_id)

        if 'full_name' in validated_data:
            user.first_name = validated_data['full_name']
        if 'phone' in validated_data:
            user.phone = validated_data['phone']

        user.save()
        return user
