from aiogram.filters.state import State, StatesGroup


class StartForm(StatesGroup):
    name = State()
    birth_date = State()


class AskState(StatesGroup):
    question = State()
    choose_type = State()
    payment = State()


class AdminState(StatesGroup):
    push_ads = State()
