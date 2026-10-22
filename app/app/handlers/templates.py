from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards.common import template_keyboard
from app.services.poster_generator import available_templates

router = Router()


async def send_templates(target: Message | CallbackQuery) -> None:
    text = "Available poster templates:" if available_templates() else "No templates are configured yet."
    keyboard = template_keyboard(available_templates())
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)


@router.message(Command("templates"))
async def templates_command(message: Message) -> None:
    await send_templates(message)


@router.callback_query(lambda query: query.data == "templates")
async def templates_callback(query: CallbackQuery) -> None:
    await query.answer()
    await send_templates(query)
