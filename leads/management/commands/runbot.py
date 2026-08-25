import asyncio
import logging
import re

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from leads.models import Lead

logger = logging.getLogger(__name__)
router = Router()

SERVICES = ["Консультація", "Замовлення послуги", "Технічна підтримка", "Інше"]

PHONE_RE = re.compile(r"^\+?\d{9,15}$")


class LeadForm(StatesGroup):
    name = State()
    phone = State()
    service = State()
    description = State()
    confirm = State()


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Залишити заявку")],
            [KeyboardButton(text="ℹ️ Послуги"), KeyboardButton(text="📞 Контакти")],
        ],
        resize_keyboard=True,
    )


def services_kb() -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=s)] for s in SERVICES]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Надіслати мій номер", request_contact=True)]],
        resize_keyboard=True,
    )


def confirm_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Підтвердити")],
            [KeyboardButton(text="✏️ Заповнити заново")],
        ],
        resize_keyboard=True,
    )


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.startswith("0") and len(digits) == 10:
        digits = "+38" + digits
    elif digits.startswith("380"):
        digits = "+" + digits
    if PHONE_RE.match(digits):
        return digits
    return None


# --- ORM обгортки (Django ORM синхронний, aiogram асинхронний) ---

save_lead = sync_to_async(Lead.objects.create, thread_sensitive=True)


@sync_to_async(thread_sensitive=True)
def count_leads_today(user_id: int) -> int:
    from django.utils import timezone

    today = timezone.localdate()
    return Lead.objects.filter(tg_user_id=user_id, created_at__date=today).count()


# --- Хендлери ---


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Вітаю! Це бот компанії <b>{settings.COMPANY_NAME}</b>.\n\n"
        "Тут можна швидко залишити заявку — ми зв'яжемося з вами найближчим часом.",
        reply_markup=main_menu(),
    )


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "скасувати")
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Немає що скасовувати.", reply_markup=main_menu())
        return
    await state.clear()
    await message.answer("Заявку скасовано.", reply_markup=main_menu())


@router.message(F.text == "ℹ️ Послуги")
async def show_services(message: Message):
    text = "\n".join(f"• {s}" for s in SERVICES)
    await message.answer(f"<b>Що ми робимо:</b>\n\n{text}", reply_markup=main_menu())


@router.message(F.text == "📞 Контакти")
async def show_contacts(message: Message):
    await message.answer(
        "<b>Контакти</b>\n\n"
        "Телефон: +380 XX XXX XX XX\n"
        "Email: hello@example.com\n"
        "Графік: Пн–Пт, 9:00–18:00",
        reply_markup=main_menu(),
    )


@router.message(F.text == "📝 Залишити заявку")
async def start_form(message: Message, state: FSMContext):
    if await count_leads_today(message.from_user.id) >= 5:
        await message.answer(
            "Ви вже залишили кілька заявок сьогодні. "
            "Наш менеджер скоро зв'яжеться з вами.",
            reply_markup=main_menu(),
        )
        return

    await state.set_state(LeadForm.name)
    await message.answer(
        "Як до вас звертатися?\n\n<i>Скасувати — /cancel</i>",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(LeadForm.name, F.text)
async def get_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await message.answer("Ім'я має бути від 2 до 100 символів. Спробуйте ще раз.")
        return

    await state.update_data(name=name)
    await state.set_state(LeadForm.phone)
    await message.answer(
        f"Приємно, {name}!\n\nЗалиште номер телефону — "
        "натисніть кнопку нижче або введіть вручну.",
        reply_markup=phone_kb(),
    )


@router.message(LeadForm.phone, F.contact)
async def get_phone_contact(message: Message, state: FSMContext):
    await _accept_phone(message, state, message.contact.phone_number)


@router.message(LeadForm.phone, F.text)
async def get_phone_text(message: Message, state: FSMContext):
    await _accept_phone(message, state, message.text)


async def _accept_phone(message: Message, state: FSMContext, raw: str):
    phone = normalize_phone(raw)
    if not phone:
        await message.answer(
            "Не схоже на номер телефону.\n"
            "Формат: <code>0671234567</code> або <code>+380671234567</code>"
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(LeadForm.service)
    await message.answer("Оберіть напрямок:", reply_markup=services_kb())


@router.message(LeadForm.service, F.text)
async def get_service(message: Message, state: FSMContext):
    service = message.text.strip()
    if service not in SERVICES:
        await message.answer("Оберіть варіант з клавіатури нижче.")
        return

    await state.update_data(service=service)
    await state.set_state(LeadForm.description)
    await message.answer(
        "Опишіть коротко вашу задачу:", reply_markup=ReplyKeyboardRemove()
    )


@router.message(LeadForm.description, F.text)
async def get_description(message: Message, state: FSMContext):
    description = message.text.strip()
    if len(description) < 5:
        await message.answer("Опишіть, будь ласка, трохи детальніше.")
        return

    await state.update_data(description=description)
    data = await state.get_data()
    await state.set_state(LeadForm.confirm)

    await message.answer(
        "<b>Перевірте заявку:</b>\n\n"
        f"Ім'я: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Напрямок: {data['service']}\n"
        f"Задача: {data['description']}",
        reply_markup=confirm_kb(),
    )


@router.message(LeadForm.confirm, F.text == "✏️ Заповнити заново")
async def restart_form(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(LeadForm.name)
    await message.answer("Гаразд, почнемо спочатку. Як до вас звертатися?",
                         reply_markup=ReplyKeyboardRemove())


@router.message(LeadForm.confirm, F.text == "✅ Підтвердити")
async def save_form(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    lead = await save_lead(
        name=data["name"],
        phone=data["phone"],
        service=data["service"],
        description=data["description"],
        tg_user_id=message.from_user.id,
        tg_username=message.from_user.username or "",
    )

    await message.answer(
        f"✅ Заявку <b>#{lead.id}</b> прийнято!\n\n"
        "Менеджер зв'яжеться з вами найближчим часом.",
        reply_markup=main_menu(),
    )

    if settings.ADMIN_CHAT_ID:
        try:
            username = (
                f"@{message.from_user.username}"
                if message.from_user.username
                else "—"
            )
            await bot.send_message(
                settings.ADMIN_CHAT_ID,
                f"🔔 <b>Нова заявка #{lead.id}</b>\n\n"
                f"Ім'я: {lead.name}\n"
                f"Телефон: <code>{lead.phone}</code>\n"
                f"Напрямок: {lead.service}\n"
                f"Задача: {lead.description}\n"
                f"Telegram: {username}",
            )
        except Exception as exc:
            logger.warning("Не вдалося сповістити адміна: %s", exc)


@router.message(LeadForm.confirm)
async def confirm_fallback(message: Message):
    await message.answer("Скористайтеся кнопками нижче.", reply_markup=confirm_kb())


@router.message()
async def fallback(message: Message):
    await message.answer("Оберіть дію з меню нижче.", reply_markup=main_menu())


# --- Точка входу ---


async def run():
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не заданий. Перевір файл .env")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logger.info("Бот запущено")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


class Command(BaseCommand):
    help = "Запускає Telegram-бота (long polling)"

    def handle(self, *args, **options):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Бот зупинено"))
