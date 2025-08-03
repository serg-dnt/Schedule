from django.urls import path
from . import views
from .views import CreateSlotsView, DoctorSlotsView, SlotFreeDatesView, \
    AppointmentDatesView, SlotsListView, DoctorListView, DoctorServicesView, \
    PatientAppointmentsView, TelegrammAuthView, CheckUserExistsView, \
    SlotDetailAPIView, DoctorByTelegramIDAPIView

urlpatterns = [
    # Врачи (Специалисты)
    path('doctors/', DoctorListView.as_view(), name='doctor-list'),

    # Услуги
    path('services/', views.ServiceListView.as_view(), name='service-list'),
    path('services/doctor/', DoctorServicesView.as_view(), name='doctor-services'),

    # Слоты
    path('slots/', SlotsListView.as_view(), name='slot-list'),
    path('slots/<int:pk>/', SlotDetailAPIView.as_view(), name='slot-detail'),
    path(
        'slots/available/',
        views.AvailableSlotsView.as_view(),
        name='available-slots'
    ),
    path(
        'slots/create/',
        CreateSlotsView.as_view(),
        name='create-slots'
    ),
    path(
        'slots/delete/',
        views.DeleteSlotsView.as_view(),
        name='delete-slots'
    ),
    path("slots/all/", DoctorSlotsView.as_view(), name="doctor-all-slots"),
    path("slots/free_dates/", SlotFreeDatesView.as_view(), name="slots-free-dates"),


    # Записи
    path(
        'appointments/create/',
        views.AppointmentCreateView.as_view(),
        name='create-appointment'
    ),
    path(
        'appointments/cancel/',
        views.AppointmentCancelView.as_view(),
        name='cancel-appointment'
    ),
    path(
        'appointments/by-patient/',
        PatientAppointmentsView.as_view(),
        name='appointments-by-patient'
    ),
    path(
        'appointments/',
        views.DoctorAppointmentsView.as_view(),
        name='doctor-appointments'
    ),
    path("appointments/dates/", AppointmentDatesView.as_view(), name="appointments-dates"),

    # Авторизация
    path("users/register", TelegrammAuthView.as_view(), name="telegram-register"),
    path("users/check/<int:telegram_id>/", CheckUserExistsView.as_view(), name="telegram-check"),
    path("doctors/by_telegram/", DoctorByTelegramIDAPIView.as_view(), name="doctors-by-telegram"),
]