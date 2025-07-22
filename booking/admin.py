from django.contrib import admin
from .models import User, AvailableSlot, Appointment


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'is_doctor', 'telegram_id')
    list_filter = ('is_doctor',)
    search_fields = ('full_name', 'telegram_id')


@admin.register(AvailableSlot)
class AvailableSlotAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'doctor', 'start_datetime', 'end_datetime', 'is_booked'
    )
    list_filter = ('doctor', 'is_booked')
    search_fields = ('doctor__full_name',)
    ordering = ('start_datetime',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'doctor', 'patient', 'start_datetime', 'end_datetime', 'status'
    )
    list_filter = ('doctor', 'status')
    search_fields = (
        'doctor__full_name', 'patient__full_name',
        'patient__phone_number', 'patient__telegram_id'
    )
    ordering = ('start_datetime',)