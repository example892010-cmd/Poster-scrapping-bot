from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Create Poster", callback_data="create")],
        [InlineKeyboardButton(text="Templates", callback_data="templates")],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Cancel", callback_data="cancel")],
    ])


def skip_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Skip", callback_data="skip")],
        [InlineKeyboardButton(text="Back", callback_data="back"), InlineKeyboardButton(text="Cancel", callback_data="cancel")],
    ])


def template_keyboard(templates: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=t["name"], callback_data=f"template:{t['id']}")] for t in templates]
    rows.append([InlineKeyboardButton(text="Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Generate Poster", callback_data="generate")],
        [InlineKeyboardButton(text="Back", callback_data="back"), InlineKeyboardButton(text="Cancel", callback_data="cancel")],
    ])


def another_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Create Another Poster", callback_data="create")],
        [InlineKeyboardButton(text="Main Menu", callback_data="menu")],
    ])
