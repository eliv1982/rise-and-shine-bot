from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    waiting_for_name = State()
    waiting_for_gender = State()


class GenerationState(StatesGroup):
    choosing_sphere = State()
    waiting_for_theme_early = State()  # Своя тема в меню сферы: ввод текста/голоса
    choosing_relationship_subsphere = State()
    choosing_style = State()
    confirm_style_extra = State()  # После выбора пресета: добавить описание или продолжить
    waiting_for_custom_style = State()
    after_result = State()


class SubscriptionState(StatesGroup):
    choosing_language = State()
    choosing_sphere = State()
    choosing_relationship_subsphere = State()
    choosing_style = State()
    choosing_hour = State()
    choosing_minute = State()
    confirming = State()

