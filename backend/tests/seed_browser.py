"""Create synthetic CI-only data in an isolated test database; never run on a public database."""
from django.contrib.auth import get_user_model

from accounts.models import Faculty, StaffProfile, StudentProfile, StudyGroup

faculty = Faculty.objects.create(name="Демонстрационный факультет")
group = StudyGroup.objects.create(name="ДЕМО-1", faculty=faculty, programme="ИТ", course=1)
user = get_user_model().objects.create_user(
    username="browser_student", password="ephemeral-browser-test-only"
)
StudentProfile.objects.create(user=user, full_name="Демонстрационный студент", group=group)

# Different faculties make accidental shared-data responses visible in browser regressions.
other_faculty = Faculty.objects.create(name="Другой демонстрационный факультет")
other_group = StudyGroup.objects.create(
    name="ДЕМО-2", faculty=other_faculty, programme="Физика", course=2
)
other = get_user_model().objects.create_user(
    username="browser_student_other", password="ephemeral-browser-test-only"
)
StudentProfile.objects.create(
    user=other, full_name="Второй демонстрационный студент", group=other_group
)
employee = get_user_model().objects.create_user(
    username="browser_employee", password="ephemeral-browser-test-only"
)
StaffProfile.objects.create(user=employee, full_name="Демонстрационный сотрудник", faculty=faculty)
