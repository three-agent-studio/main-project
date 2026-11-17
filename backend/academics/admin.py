from django import forms
from django.contrib import admin

from accounts.admin import StaffProfileAdmin

from .models import Lesson, LessonChange, TeachingAssignment
from .services import EDITABLE_FIELDS, change_lesson


class LessonAdminForm(forms.ModelForm):
    change_reason = forms.CharField(
        label="Причина изменения",
        max_length=500,
        required=False,
        help_text=(
            "Этот текст виден студентам группы. "
            "Не указывайте внутренние заметки и персональные данные."
        ),
    )
    expected_revision = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Lesson
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields["change_reason"].required = True
            self.fields["expected_revision"].required = True
            self.initial["expected_revision"] = self.instance.revision

    def clean(self):
        cleaned = super().clean()
        if not self.instance._state.adding:
            # ModelAdmin's changeform transaction holds this lock through save_model.
            current = Lesson.objects.select_for_update().get(pk=self.instance.pk)
            if current.revision != cleaned.get("expected_revision"):
                raise forms.ValidationError("Занятие уже изменилось. Обновите страницу.")
        return cleaned


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    form = LessonAdminForm
    list_display = ["subject", "group", "starts_at", "room", "status", "revision"]
    list_filter = ["group", "status", "kind"]
    search_fields = ["subject", "teacher", "room", "group__name"]
    readonly_fields = ["revision", "updated_at"]

    def get_readonly_fields(self, request, obj=None):
        # Group changes could expose old history to a different audience. Create
        # a separate occurrence for another group instead of reassigning this one.
        return [*self.readonly_fields, "group"] if obj else self.readonly_fields

    def save_model(self, request, obj, form, change):
        if change:
            saved = change_lesson(
                obj.pk,
                changes={name: getattr(obj, name) for name in EDITABLE_FIELDS},
                reason=form.cleaned_data["change_reason"],
                actor=request.user,
                expected_revision=form.cleaned_data["expected_revision"],
            )
            obj.revision, obj.status = saved.revision, saved.status
        else:
            super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return False  # Cancel occurrences to preserve history and notification references.


@admin.register(LessonChange)
class LessonChangeAdmin(admin.ModelAdmin):
    list_display = ["lesson", "revision", "reason", "created_at"]
    readonly_fields = [field.name for field in LessonChange._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(StaffProfileAdmin):
    list_display = ["teacher", "group", "subject", "term", "is_active"]
    list_filter = ["is_active", "group", "teacher"]
    search_fields = ["subject", "teacher__full_name", "group__name"]

    def get_readonly_fields(self, request, obj=None):
        return ["teacher", "group", "subject", "term"] if obj else []
