from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.keyboards.common import main_keyboard

router = Router()
WELCOME = ("Welcome to ANIFLIX Poster Maker.\n\n"
           "Create an anime poster from your own artwork and metadata. "
           "Use /create to begin, /templates to view templates, or /help for instructions.")


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=main_keyboard())


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Upload your anime artwork, then provide title, season, synopsis, genres, and optional rating/studio. "
        "You can cancel any time with /cancel. The bot uses your supplied image and the exact configured template.",
        reply_markup=main_keyboard(),
    )
