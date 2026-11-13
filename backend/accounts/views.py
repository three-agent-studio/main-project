from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET
from rest_framework.generics import RetrieveAPIView

from .models import User
from .serializers import MeSerializer


class MeView(RetrieveAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        # Never accept a user id from URL/body here. Identity comes only from the session.
        return User.objects.select_related("student_profile__group__faculty").get(
            pk=self.request.user.pk
        )


@require_GET
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})
