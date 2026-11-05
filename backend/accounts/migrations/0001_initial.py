import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
                                           verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, verbose_name="superuser status",
                    help_text="Designates that this user has all permissions without explicitly assigning them.")),
                ("username", models.CharField(max_length=150, unique=True, verbose_name="username",
                    validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                    error_messages={"unique": "A user with that username already exists."},
                    help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                ("is_staff", models.BooleanField(default=False, verbose_name="staff status",
                    help_text="Designates whether the user can log into this admin site.")),
                ("is_active", models.BooleanField(default=True, verbose_name="active",
                    help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now,
                                                     verbose_name="date joined")),
                ("groups", models.ManyToManyField(blank=True, related_name="user_set",
                    related_query_name="user", to="auth.group", verbose_name="groups",
                    help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set",
                    related_query_name="user", to="auth.permission", verbose_name="user permissions",
                    help_text="Specific permissions for this user.")),
            ],
            options={"verbose_name": "user", "verbose_name_plural": "users", "abstract": False},
            managers=[("objects", django.contrib.auth.models.UserManager())],
        ),
        migrations.CreateModel(name="Faculty", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
                                      verbose_name="ID")),
            ("name", models.CharField(max_length=200, unique=True)),
        ]),
        migrations.CreateModel(name="StudyGroup", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
                                      verbose_name="ID")),
            ("name", models.CharField(max_length=50, unique=True)),
            ("programme", models.CharField(max_length=200)),
            ("course", models.PositiveSmallIntegerField()),
            ("faculty", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                related_name="groups", to="accounts.faculty")),
        ], options={"constraints": [models.CheckConstraint(
            condition=models.Q(("course__gte", 1), ("course__lte", 8)), name="group_course_1_to_8"
        )]}),
        migrations.CreateModel(name="StudentProfile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
                                      verbose_name="ID")),
            ("full_name", models.CharField(max_length=250)),
            ("group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                related_name="students", to="accounts.studygroup")),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                related_name="student_profile", to=settings.AUTH_USER_MODEL)),
        ]),
    ]
