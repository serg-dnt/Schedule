from rest_framework import serializers
from .models import Service, AvailableSlot, Appointment, User
from datetime import timedelta


class DoctorShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'full_name', 'telegram_id')


class PatientShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name", "phone_number")


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
    doctor = DoctorShortSerializer(read_only=True)
    patient = PatientShortSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id',
            'doctor',
            'patient',
            'service',
            'start_datetime',
            'end_datetime',
            'status',
            'created_at',
        ]


# serializers.py

class AppointmentCreateSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()
    service_id = serializers.IntegerField()
    start_datetime = serializers.DateTimeField()
    telegram_id = serializers.IntegerField()

    def validate(self, data):
        doctor_id = data['doctor_id']
        service_id = data['service_id']
        start_datetime = data['start_datetime']
        telegram_id = data['telegram_id']

        # 🔍 Найти пациента по telegram_id
        try:
            patient = User.objects.get(telegram_id=telegram_id, is_doctor=False)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пациент не найден по telegram_id")

        # ✅ Валидация доктора
        try:
            doctor = User.objects.get(id=doctor_id, is_doctor=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("Доктор не найден")

        # ✅ Валидация услуги
        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            raise serializers.ValidationError("Услуга не найдена")

        needed_duration = timedelta(minutes=service.duration_minutes)

        available_slots = AvailableSlot.objects.filter(
            doctor=doctor,
            start_datetime__gte=start_datetime,
            is_booked=False
        ).order_by('start_datetime')

        selected_slots = []
        total_duration = timedelta()

        for slot in available_slots:
            if not selected_slots:
                if slot.start_datetime != start_datetime:
                    continue
                selected_slots.append(slot)
                total_duration += slot.end_datetime - slot.start_datetime
            else:
                last = selected_slots[-1]
                if slot.start_datetime == last.end_datetime:
                    selected_slots.append(slot)
                    total_duration += slot.end_datetime - slot.start_datetime
                else:
                    break

            if total_duration >= needed_duration:
                break

        if total_duration < needed_duration:
            raise serializers.ValidationError("Недостаточно свободных слотов")

        # ✍️ Добавим данные в validated_data
        data['doctor'] = doctor
        data['service'] = service
        data['patient'] = patient
        data['selected_slots'] = selected_slots
        data['end_datetime'] = selected_slots[-1].end_datetime
        return data

    def create(self, validated_data):
        patient = validated_data['patient']
        doctor = validated_data['doctor']
        service = validated_data['service']
        start_datetime = validated_data['start_datetime']
        end_datetime = validated_data['end_datetime']
        slots_to_book = validated_data['selected_slots']

        for slot in slots_to_book:
            slot.is_booked = True
            slot.save()

        return Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            service=service,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            status='active'
        )


class AppointmentCancelSerializer(serializers.Serializer):
    appointment_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )

    def validate(self, data):
        appointment_ids = data['appointment_ids']
        user = self.context.get("user")

        if not user:
            raise serializers.ValidationError("Пользователь не найден")

        if user.is_doctor:
            # Врач может отменить только свои записи
            appointments = Appointment.objects.filter(
                id__in=appointment_ids,
                doctor=user,
                status='active'
            )
        else:
            # Пациент может отменить только свои записи
            appointments = Appointment.objects.filter(
                id__in=appointment_ids,
                patient=user,
                status='active'
            )

        if appointments.count() != len(set(appointment_ids)):
            raise serializers.ValidationError("Некоторые записи не найдены или вам не принадлежат")

        data['appointments'] = appointments
        return data

    def save(self, **kwargs):
        appointments = self.validated_data['appointments']

        for appointment in appointments:
            # Освобождаем связанные слоты
            slots = AvailableSlot.objects.filter(
                doctor=appointment.doctor,
                start_datetime__gte=appointment.start_datetime,
                end_datetime__lte=appointment.end_datetime,
                is_booked=True
            )
            slots.update(is_booked=False)

            appointment.status = 'cancelled'
            appointment.save()

        return appointments


class TelegramAuthSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
    full_name = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)

    def create(self, validated_data):
        telegram_id = validated_data["telegram_id"]
        user, created = User.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                "full_name": validated_data.get("full_name", ""),
                "phone_number": validated_data.get("phone_number", ""),
                "is_doctor": False,
                "username": f"tg_{validated_data['telegram_id']}"
            }
        )

        # Обновление данных, если уже существующий пользователь
        if not created:
            if "full_name" in validated_data:
                user.full_name = validated_data["full_name"]
            if "phone_number" in validated_data:
                user.phone_number = validated_data["phone_number"]
            user.save()

        return user