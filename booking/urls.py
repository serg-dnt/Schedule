from django.urls import path
from . import views
from .views import CreateSlotsView, DoctorSlotsView, SlotFreeDatesView, AppointmentDatesView, SlotsListView

urlpatterns = [
    # Услуги
    path('services/', views.ServiceListView.as_view(), name='service-list'),

    # Слоты
    path('slots/', SlotsListView.as_view(), name='slot-list'),
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
    path("appointments/dates/", AppointmentDatesView.as_view(), name="appointments-dates"),

    # Авторизация
]