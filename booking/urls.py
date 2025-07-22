from django.urls import path
from . import views

urlpatterns = [
    # Услуги
    path('services/', views.ServiceListView.as_view(), name='service-list'),

    # Слоты
    path(
        'slots/available/',
        views.AvailableSlotsView.as_view(),
        name='available-slots'
    ),
    path(
        'slots/create/',
        views.CreateSlotsView.as_view(),
        name='create-slots'
    ),
    path(
        'slots/<int:pk>/delete/',
        views.SlotDeleteView.as_view(),
        name='delete-slot'
    ),

    # Записи
    path(
        'appointments/create/',
        views.AppointmentCreateView.as_view(),
        name='create-appointment'
    ),
    path(
        'appointments/<int:pk>/cancel/',
        views.CancelAppointmentView.as_view(),
        name='cancel-appointment'
    ),
    path(
        'appointments/mine/',
        views.MyAppointmentsView.as_view(),
        name='my-appointments'
    ),
    path(
        'appointments/doctor/',
        views.DoctorAppointmentsView.as_view(),
        name='doctor-appointments'
    ),

    # Авторизация
    path(
        'auth/telegram/',
        views.TelegramAuthView.as_view(),
        name='telegram-auth'
    )
]