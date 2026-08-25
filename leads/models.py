from django.db import models


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Нова"
        IN_PROGRESS = "in_progress", "В роботі"
        DONE = "done", "Закрита"
        REJECTED = "rejected", "Відхилена"

    name = models.CharField("Ім'я", max_length=100)
    phone = models.CharField("Телефон", max_length=20)
    service = models.CharField("Послуга", max_length=100, blank=True)
    description = models.TextField("Опис задачі")

    status = models.CharField(
        "Статус", max_length=20, choices=Status.choices, default=Status.NEW
    )
    comment = models.TextField("Коментар менеджера", blank=True)

    tg_user_id = models.BigIntegerField("Telegram ID", db_index=True)
    tg_username = models.CharField("Telegram username", max_length=64, blank=True)

    created_at = models.DateTimeField("Створено", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Оновлено", auto_now=True)

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.name} — {self.phone}"
