from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Crop,
    CropYieldBenchmark,
    Farm,
    FarmQuestion,
    HarvestRecord,
    MarketPrice,
    Notification,
    Recommendation,
    User,
)


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
@admin.register(CropYieldBenchmark)
class CropYieldBenchmarkAdmin(admin.ModelAdmin):
    list_display = ("crop", "district", "reference_year", "yield_kg_per_hectare", "source_title")
    list_filter = ("crop", "district", "reference_year")
    search_fields = ("crop", "district", "source_title")


@admin.register(HarvestRecord)
class HarvestRecordAdmin(admin.ModelAdmin):
    list_display = ("farm", "crop", "harvest_date", "quantity_kg", "recorded_by")
    list_filter = ("crop", "harvest_date")
    search_fields = ("farm__name", "crop", "recorded_by__username")


@admin.register(MarketPrice)
class MarketPriceAdmin(admin.ModelAdmin):
    list_display = ("commodity", "market", "district", "price", "unit", "currency", "observed_at", "source_title")
    list_filter = ("commodity", "district", "currency", "observed_at")
    search_fields = ("commodity", "market", "district", "source_title")
