from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Crop, Farm, FarmQuestion, Notification, Recommendation, User


@admin.register(User)
class AgriUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("AgriCloud profile", {"fields": ("role", "district", "phone")}),)
    list_display = ("username", "email", "role", "district", "is_staff")
    list_filter = ("role", "district")


admin.site.register(Farm)
admin.site.register(Crop)
admin.site.register(FarmQuestion)
admin.site.register(Recommendation)
admin.site.register(Notification)
