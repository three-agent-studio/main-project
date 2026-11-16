from django.urls import path

from .views import LessonDetailView, LessonListView

urlpatterns = [
    path("lessons/", LessonListView.as_view(), name="lesson-list"),
    path("lessons/<uuid:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
]
