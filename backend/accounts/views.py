from django.conf import settings
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET
from rest_framework.generics import RetrieveAPIView

from .models import User
from .serializers import MeSerializer


class StudentLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        # Explicit, Django-validated `next` still wins; dual-role users keep /profile.
        if self.get_redirect_url():
            return self.get_redirect_url()
        teacher = getattr(self.request.user, "teacher_profile", None)
        if teacher and teacher.is_active and not hasattr(self.request.user, "student_profile"):
            return "/teaching"
        return super().get_success_url()

    def form_valid(self, form):
        # Keep Django's authentication, safe `next` redirect and session-key rotation.
        # Remembering only changes cookie lifetime; credentials never enter browser storage.
        response = super().form_valid(form)
        self.request.session.set_expiry(
            settings.SESSION_COOKIE_AGE if self.request.POST.get("remember_me") == "on" else 0
        )
        return response


class MeView(RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        # Never accept a user id from URL/body here. Identity comes only from the session.
        return User.objects.select_related(
            "student_profile__group__faculty", "staff_profile__faculty", "teacher_profile__faculty"
        ).get(pk=self.request.user.pk)


@require_GET
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})
