"""Create synthetic CI-only data in an isolated test database; never run on a public database."""
from django.contrib.auth import get_user_model

from accounts.models import Faculty, StudentProfile, StudyGroup

faculty = Faculty.objects.create(name="Демонстрационный факультет")
group = StudyGroup.objects.create(name="ДЕМО-1", faculty=faculty, programme="ИТ", course=1)
user = get_user_model().objects.create_user(
    username="browser_student", password="ephemeral-browser-test-only"
)
StudentProfile.objects.create(user=user, full_name="Демонстрационный студент", group=group)
