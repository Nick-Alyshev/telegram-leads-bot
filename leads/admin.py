import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "phone_link",
        "service",
        "short_description",
        "status",
        "created_at",
    )
    list_display_links = ("id", "name")
    list_filter = ("status", "service", "created_at")
    search_fields = ("name", "phone", "description", "tg_username")
    list_editable = ("status",)
    date_hierarchy = "created_at"
    readonly_fields = ("tg_user_id", "tg_username", "created_at", "updated_at")
    list_per_page = 50
    actions = ("export_csv", "mark_in_progress", "mark_done")

    fieldsets = (
        ("Заявка", {"fields": ("name", "phone", "service", "description")}),
        ("Обробка", {"fields": ("status", "comment")}),
        (
            "Службове",
            {
                "fields": ("tg_user_id", "tg_username", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Телефон")
    def phone_link(self, obj):
        return format_html('<a href="tel:{}">{}</a>', obj.phone, obj.phone)

    @admin.display(description="Опис")
    def short_description(self, obj):
        text = obj.description
        return text if len(text) <= 60 else text[:60] + "…"

    @admin.action(description="Вивантажити в CSV")
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="leads.csv"'
        response.write("\ufeff")  # BOM, щоб Excel не ламав кирилицю

        writer = csv.writer(response, delimiter=";")
        writer.writerow(
            ["ID", "Ім'я", "Телефон", "Послуга", "Опис", "Статус", "Створено"]
        )
        for lead in queryset:
            writer.writerow(
                [
                    lead.id,
                    lead.name,
                    lead.phone,
                    lead.service,
                    lead.description,
                    lead.get_status_display(),
                    lead.created_at.strftime("%d.%m.%Y %H:%M"),
                ]
            )
        return response

    @admin.action(description="Позначити «В роботі»")
    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status=Lead.Status.IN_PROGRESS)
        self.message_user(request, f"Оновлено заявок: {updated}")

    @admin.action(description="Позначити «Закрита»")
    def mark_done(self, request, queryset):
        updated = queryset.update(status=Lead.Status.DONE)
        self.message_user(request, f"Оновлено заявок: {updated}")


admin.site.site_header = "Заявки з Telegram"
admin.site.site_title = "LeadBot"
admin.site.index_title = "Панель управління"
