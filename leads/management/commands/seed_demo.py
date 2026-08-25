"""Наповнює базу демонстраційними заявками.

Використання:
    python manage.py seed_demo          # додати 8 заявок
    python manage.py seed_demo --clear  # спочатку видалити всі наявні
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from leads.models import Lead

DEMO_LEADS = [
    {
        "name": "Олена Ковальчук",
        "phone": "+380671482357",
        "service": "Консультація",
        "description": (
            "Цікавить встановлення кондиціонера в квартиру 62 м². "
            "Коли можна замовити виїзд майстра на заміри?"
        ),
        "status": Lead.Status.DONE,
        "comment": "Замір проведено 12.08, договір підписано.",
        "days_ago": 11,
        "username": "olena_k",
    },
    {
        "name": "Андрій Мельник",
        "phone": "+380932847561",
        "service": "Замовлення послуги",
        "description": (
            "Потрібне прибирання офісу 120 м² раз на тиждень. "
            "Скиньте, будь ласка, прайс і умови договору."
        ),
        "status": Lead.Status.DONE,
        "comment": "Уклали договір на 3 місяці.",
        "days_ago": 9,
        "username": "a_melnyk",
    },
    {
        "name": "Марина Ткаченко",
        "phone": "+380501847293",
        "service": "Технічна підтримка",
        "description": (
            "Не працює особистий кабінет — при вході пише помилку 500. "
            "Пробувала з телефона і з ноутбука, те саме."
        ),
        "status": Lead.Status.DONE,
        "comment": "Проблема на боці хостингу, усунено.",
        "days_ago": 7,
        "username": "maryna_tk",
    },
    {
        "name": "Сергій Бондаренко",
        "phone": "+380637291845",
        "service": "Замовлення послуги",
        "description": (
            "Потрібно перевезти обладнання зі складу на Оболоні "
            "в офіс на Печерську. Приблизно 15 коробок і 4 стелажі."
        ),
        "status": Lead.Status.IN_PROGRESS,
        "comment": "Погоджуємо дату, чекаю відповідь по вівторку.",
        "days_ago": 4,
        "username": "s_bondarenko",
    },
    {
        "name": "Ірина Савченко",
        "phone": "+380973614829",
        "service": "Консультація",
        "description": (
            "Хочу дізнатись про варіанти обслуговування для невеликої "
            "кав'ярні. Скільки коштує щомісячний пакет?"
        ),
        "status": Lead.Status.IN_PROGRESS,
        "comment": "Надіслано КП, чекаю зворотний зв'язок.",
        "days_ago": 3,
        "username": "iryna_s",
    },
    {
        "name": "Володимир Кравець",
        "phone": "+380664958172",
        "service": "Технічна підтримка",
        "description": (
            "Після оновлення не приходять сповіщення на пошту. "
            "Раніше все працювало нормально."
        ),
        "status": Lead.Status.NEW,
        "comment": "",
        "days_ago": 1,
        "username": "vkravets",
    },
    {
        "name": "Наталія Гриценко",
        "phone": "+380685173946",
        "service": "Замовлення послуги",
        "description": (
            "Потрібен монтаж системи відеоспостереження на 6 камер "
            "для магазину. Чи виїжджаєте в Бровари?"
        ),
        "status": Lead.Status.NEW,
        "comment": "",
        "days_ago": 0,
        "username": "n_hrytsenko",
    },
    {
        "name": "Тарас Лисенко",
        "phone": "+380952836147",
        "service": "Інше",
        "description": "Доброго дня, а ви працюєте у вихідні?",
        "status": Lead.Status.REJECTED,
        "comment": "Не цільове звернення, відповіли в чаті.",
        "days_ago": 6,
        "username": "",
    },
]


class Command(BaseCommand):
    help = "Наповнює базу демонстраційними заявками для скріншотів і показу клієнту"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Видалити всі наявні заявки перед наповненням",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = Lead.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Видалено записів: {deleted}"))

        now = timezone.now()
        created = 0

        for item in DEMO_LEADS:
            lead = Lead.objects.create(
                name=item["name"],
                phone=item["phone"],
                service=item["service"],
                description=item["description"],
                status=item["status"],
                comment=item["comment"],
                tg_user_id=random.randint(100_000_000, 999_999_999),
                tg_username=item["username"],
            )

            # created_at має auto_now_add, тому дату задаємо окремим update
            created_at = now - timedelta(
                days=item["days_ago"],
                hours=random.randint(1, 9),
                minutes=random.randint(0, 59),
            )
            Lead.objects.filter(pk=lead.pk).update(created_at=created_at)
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Додано заявок: {created}"))
        self.stdout.write("Готово. Відкрий /admin/leads/lead/ для перегляду.")