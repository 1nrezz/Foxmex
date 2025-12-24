from aiogram.fsm.state import State, StatesGroup
class FixFSM(StatesGroup):
    waiting_for_text = State()


class AddQuestionFSM(StatesGroup):
    waiting_for_text = State()


class DeleteQuestionFSM(StatesGroup):
    waiting_for_text = State()