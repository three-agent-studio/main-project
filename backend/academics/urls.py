from django.urls import path
from rest_framework.routers import SimpleRouter

from .teaching_views import (
    StudentActivities,
    StudentAssessments,
    TeacherActivityViewSet,
    TeacherAssignmentList,
    TeacherResults,
    TeacherRoster,
)
from .views import LessonDetailView, LessonListView

urlpatterns = [
    path("lessons/", LessonListView.as_view(), name="lesson-list"),
    path("lessons/<uuid:pk>/", LessonDetailView.as_view(), name="lesson-detail"),
    path("activities/", StudentActivities.as_view()),
    path("assessments/", StudentAssessments.as_view()),
    path("teaching/assignments/", TeacherAssignmentList.as_view()),
    path("teaching/activities/<uuid:pk>/students/", TeacherRoster.as_view()),
    path("teaching/activities/<uuid:pk>/results/", TeacherResults.as_view()),
]
router = SimpleRouter()
router.register("teaching/activities", TeacherActivityViewSet, basename="teaching-activity")
urlpatterns += router.urls
