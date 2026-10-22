from aiogram.fsm.state import State, StatesGroup


class PosterStates(StatesGroup):
    choosing_template = State()
    waiting_artwork = State()
    waiting_title = State()
    waiting_season = State()
    waiting_synopsis = State()
    waiting_rating = State()
    waiting_studio = State()
    waiting_genres = State()
    confirming = State()
