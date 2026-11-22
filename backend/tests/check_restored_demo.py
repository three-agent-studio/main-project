"""Executed by 'manage.py shell' against the isolated PostgreSQL restore in CI."""

from academics.models import Assessment, Lesson
from accounts.models import StaffProfile, StudentProfile
from notifications.models import Announcement
from service_requests.models import RequestEvent, ServiceRequest

students = StudentProfile.objects.filter(user__username__startswith="jury_student_")
assert students.count() == 2
assert students.values("group__faculty_id").distinct().count() == 2
assert StaffProfile.objects.filter(user__username="jury_deanery", user__is_staff=False).exists()
assert Lesson.objects.filter(group__name__startswith="ДЕМО-ЖЮРИ-").count() >= 6
assert Assessment.objects.filter(student__in=students, score=5).count() == 1
assert ServiceRequest.objects.filter(student__in=students).count() == 1
assert RequestEvent.objects.filter(ticket__student__in=students).count() == 1
assert Announcement.objects.filter(faculty__groups__students__in=students).count() == 2
print("Verified restored profiles, roles, schedule, results, request history and announcements.")
