from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import AbstractUser
from decimal import Decimal


class User(AbstractUser):
    telegram_id = models.BigIntegerField(unique=True, blank=True, null=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    is_doctor = models.BooleanField(default=False)
    is_doctor_approved = models.BooleanField(default=False)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['full_name', 'phone_number']

    def __str__(self):
        return f"{'Dr. ' if self.is_doctor else ''}{self.full_name}"


class Service(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(5)]
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    def __str__(self):
        return self.name


class AvailableSlot(models.Model):
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'is_doctor': True},
        related_name='available_slots'
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    is_booked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('doctor', 'start_datetime')
        ordering = ['start_datetime']

    def __str__(self):
        doctor_full_name = self.doctor.full_name
        start_datetime = self.start_datetime.strftime('%Y-%m-%d %H:%M')
        return f"{doctor_full_name}: {start_datetime}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'is_doctor': False},
        related_name='appointments'
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'is_doctor': True},
        related_name='doctor_appointments'
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active'
    )

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        patient_full_name = self.patient.full_name
        service_name = self.service.name
        start_datetime = self.start_datetime.strftime('%Y-%m-%d %H:%M')
        return f"{patient_full_name} — {service_name} @ {start_datetime}"