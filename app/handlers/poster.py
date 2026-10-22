from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.keyboards.common import (another_keyboard, cancel_keyboard,
                                  confirm_keyboard, main_keyboard,
                                  skip_cancel_keyboard, template_keyboard)
from app.services.poster_generator import available_templates, generate_poster
from app.services.validation import MAX_GENRES, MAX_TEXT, clean_text, parse_season, valid_title
from app.states.poster import PosterStates

router = Router()


def summary(data: dict) -> str:
    return ("Please confirm your poster details:\n\n"
            f"Template: {data.get('template_id', 'template_01')}\n"
            f"Title: {data['title']}\n"
            f"Season: {data['season']}\n"
            f"Synopsis: {data['synopsis']}\n"
            f"IMDb rating: {data.get('rating') or 'Skipped'}\n"
            f"Studio: {data.get('studio') or 'Skipped'}\n"
            f"Genres: {data.get('genres') or '—'}")


async def begin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(PosterStates.choosing_template)
    await message.answer("Choose a poster template:", reply_markup=template_keyboard(available_templates()))


@router.message(Command("create"))
async def create_command(message: Message, state: FSMContext) -> None:
    await begin(message, state)


@router.callback_query(lambda query: query.data == "create")
async def create_callback(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await begin(query.message, state)


@router.callback_query(PosterStates.choosing_template, lambda query: query.data and query.data.startswith("template:"))
async def choose_template(query: CallbackQuery, state: FSMContext) -> None:
    template_id = query.data.split(":", 1)[1]
    if template_id not in {t["id"] for t in available_templates()}:
        await query.answer("That template is unavailable.", show_alert=True)
        return
    await state.update_data(template_id=template_id)
    await state.set_state(PosterStates.waiting_artwork)
    await query.answer()
    await query.message.edit_text("Upload the original anime artwork as a photo or image document.", reply_markup=cancel_keyboard())


@router.message(PosterStates.waiting_artwork)
async def receive_artwork(message: Message, state: FSMContext, bot: Bot) -> None:
    source = message.photo[-1] if message.photo else message.document if message.document and (message.document.mime_type or "").startswith("image/") else None
    if source is None:
        await message.answer("Please send an image (photo or image document).", reply_markup=cancel_keyboard())
        return
    if message.document and message.document.file_size and message.document.file_size > 15 * 1024 * 1024:
        await message.answer("That image is too large. Please upload an image under 15 MB.")
        return
    suffix = ".jpg"
    if message.document and message.document.file_name:
        suffix = Path(message.document.file_name).suffix.lower() or ".img"
    fd, path = tempfile.mkstemp(prefix=f"aniflix_{message.from_user.id}_", suffix=suffix)
    os.close(fd)
    try:
        telegram_file = await bot.get_file(source.file_id)
        await bot.download_file(telegram_file.file_path, destination=path)
        await state.update_data(artwork_path=path)
        await state.set_state(PosterStates.waiting_title)
        await message.answer("What is the anime title?", reply_markup=cancel_keyboard())
    except Exception:
        Path(path).unlink(missing_ok=True)
        await message.answer("I could not download that image. Please try uploading it again.")


@router.message(PosterStates.waiting_title)
async def receive_title(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "", 120)
    if not valid_title(value):
        await message.answer("Please enter a title up to 120 characters.")
        return
    await state.update_data(title=value)
    await state.set_state(PosterStates.waiting_season)
    await message.answer("Enter the season number (for example, 1).", reply_markup=cancel_keyboard())


@router.message(PosterStates.waiting_season)
async def receive_season(message: Message, state: FSMContext) -> None:
    season = parse_season(message.text or "")
    if season is None:
        await message.answer("Please enter a valid season number such as 1 or 2.")
        return
    await state.update_data(season=season)
    await state.set_state(PosterStates.waiting_synopsis)
    await message.answer("Enter the synopsis (up to 2500 characters).", reply_markup=cancel_keyboard())


@router.message(PosterStates.waiting_synopsis)
async def receive_synopsis(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "", MAX_TEXT)
    if not value:
        await message.answer("The synopsis cannot be empty.")
        return
    await state.update_data(synopsis=value)
    await state.set_state(PosterStates.waiting_rating)
    await message.answer("Enter the IMDb rating, or tap Skip.", reply_markup=skip_cancel_keyboard())


@router.callback_query(PosterStates.waiting_rating, lambda query: query.data == "skip")
async def skip_rating(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.update_data(rating=None)
    await state.set_state(PosterStates.waiting_studio)
    await query.message.edit_text("Enter the studio name, or tap Skip.", reply_markup=skip_cancel_keyboard())


@router.message(PosterStates.waiting_rating)
async def receive_rating(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "", 20)
    try:
        numeric = float(value)
        if not 0 <= numeric <= 10:
            raise ValueError
    except ValueError:
        await message.answer("Enter a rating from 0 to 10, or tap Skip.")
        return
    await state.update_data(rating=f"{numeric:g}/10")
    await state.set_state(PosterStates.waiting_studio)
    await message.answer("Enter the studio name, or tap Skip.", reply_markup=skip_cancel_keyboard())


@router.callback_query(PosterStates.waiting_studio, lambda query: query.data == "skip")
async def skip_studio(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.update_data(studio=None)
    await state.set_state(PosterStates.waiting_genres)
    await query.message.edit_text("Enter genres separated by commas.", reply_markup=cancel_keyboard())


@router.message(PosterStates.waiting_studio)
async def receive_studio(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "", 100)
    if not value:
        await message.answer("Enter a studio name or tap Skip.")
        return
    await state.update_data(studio=value)
    await state.set_state(PosterStates.waiting_genres)
    await message.answer("Enter genres separated by commas.", reply_markup=cancel_keyboard())


@router.message(PosterStates.waiting_genres)
async def receive_genres(message: Message, state: FSMContext) -> None:
    value = clean_text(message.text or "", MAX_GENRES)
    if not value:
        await message.answer("Please provide at least one genre.")
        return
    genres = ", ".join(part.strip() for part in value.split(",") if part.strip())
    await state.update_data(genres=genres)
    data = await state.get_data()
    await state.set_state(PosterStates.confirming)
    await message.answer(summary(data), reply_markup=confirm_keyboard())


@router.callback_query(PosterStates.confirming, lambda query: query.data == "generate")
async def generate(query: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await query.answer("Generating poster…")
    data = await state.get_data()
    output_path = None
    try:
        fd, output_path = tempfile.mkstemp(prefix="aniflix_poster_", suffix=".png")
        os.close(fd)
        await asyncio.to_thread(generate_poster, artwork_path=data["artwork_path"], output_path=output_path, **{k: data[k] for k in ("title", "season", "synopsis", "rating", "studio", "genres", "template_id")})
        await query.message.answer_document(FSInputFile(output_path), caption="Your ANIFLIX poster is ready!", reply_markup=another_keyboard())
    except Exception:
        await query.message.answer("I could not generate the poster from that input. Please try again with another image.", reply_markup=main_keyboard())
    finally:
        if output_path:
            Path(output_path).unlink(missing_ok=True)
        if data.get("artwork_path"):
            Path(data["artwork_path"]).unlink(missing_ok=True)
        await state.clear()


@router.callback_query(lambda query: query.data == "cancel")
async def cancel_callback(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("artwork_path"):
        Path(data["artwork_path"]).unlink(missing_ok=True)
    await state.clear()
    await query.answer("Cancelled")
    await query.message.edit_text("Poster creation cancelled.", reply_markup=main_keyboard())


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("artwork_path"):
        Path(data["artwork_path"]).unlink(missing_ok=True)
    await state.clear()
    await message.answer("Poster creation cancelled.", reply_markup=main_keyboard())
