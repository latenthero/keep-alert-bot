import logging
from web3 import Web3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from unbonded_eth_checker import UnbondedEthChecker
import mongo_helper
import config

bot = Bot(token=config.bot_token)
memory_storage = MemoryStorage()
dp = Dispatcher(bot, storage=memory_storage)


class AddAddress(StatesGroup):
    waiting_for_new_address = State()


class RemoveAddress(StatesGroup):
    waiting_for_remove = State()


class SetThreshold(StatesGroup):
    waiting_for_new_threshold = State()


kb_add = u'\U00002795 Add address'
kb_remove = u'\U0000274C Remove address'
kb_threshold = u'\U0000270F Set threshold'
kb_info = u'\U00002139 Info'

# Emoji codes
emoji_ok = u'\U00002705'
emoji_error = u'\U0001F6AB'
emoji_list = u'\U0001F4CB'
emoji_flag = u'\U0001F6A9'

main_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.add(types.KeyboardButton(text=kb_add))
main_keyboard.add(types.KeyboardButton(text=kb_remove))
main_keyboard.add(types.KeyboardButton(text=kb_threshold))
main_keyboard.add(types.KeyboardButton(text=kb_info))
remove_keyboard = types.ReplyKeyboardRemove()


def validate_address(address):
    try:
        Web3.toChecksumAddress(address)
        return True
    except Exception:
        return False


def validate_threshold(value):
    try:
        return float(value)
    except ValueError:
        return False


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    # poll_keyboard.add(types.KeyboardButton(text='Cancel'))
    await message.answer('Choose action', reply_markup=main_keyboard)


@dp.message_handler(lambda message: message.text == kb_add, state='*')
async def add_address_step_1(message: types.Message):
    await message.answer('Send me address:', reply_markup=remove_keyboard)
    await AddAddress.waiting_for_new_address.set()


@dp.message_handler(state=AddAddress.waiting_for_new_address, content_types=types.ContentTypes.TEXT)
async def add_address_step_2(message: types.Message, state: FSMContext):
    address = message.text
    if not validate_address(address):
        await message.answer('%s Address `%s` is invalid' % (emoji_error, address), reply_markup=main_keyboard, parse_mode=types.ParseMode.MARKDOWN)
    else:
        mongo_helper.add_address_to_db(address, message.chat.id)
        await message.answer('%s Address `%s` added' % (emoji_ok, address), reply_markup=main_keyboard,  parse_mode=types.ParseMode.MARKDOWN)
    await state.finish()


@dp.message_handler(lambda message: message.text == kb_remove, state='*')
async def remove_address_step_1(message: types.Message):
    addresses = mongo_helper.get_addresses_from_db(message.chat.id)
    if not addresses:
        await message.answer('You have no addresses. Try to add a new one', reply_markup=main_keyboard)
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for address in addresses:
            keyboard.add(address)
        keyboard.add('Cancel')
        await message.answer('Click address to remove:', reply_markup=keyboard)
        await RemoveAddress.waiting_for_remove.set()


@dp.message_handler(state=RemoveAddress.waiting_for_remove, content_types=types.ContentTypes.TEXT)
async def remove_address_step_2(message: types.Message, state: FSMContext):  # обратите внимание, есть второй аргумент
    addresses = mongo_helper.get_addresses_from_db(message.chat.id)
    if message.text in addresses:
        address = message.text
        mongo_helper.remove_address_from_db(address, message.chat.id)
        await message.answer('%s Address `%s` removed' % (emoji_ok, address), reply_markup=main_keyboard,  parse_mode=types.ParseMode.MARKDOWN)
    else:
        await message.answer('Canceled', reply_markup=main_keyboard)
    await state.finish()


@dp.message_handler(lambda message: message.text == kb_threshold, state='*')
async def set_threshold_step_1(message: types.Message):
    await message.answer('Send me threshold in ETH:', reply_markup=remove_keyboard)
    await SetThreshold.waiting_for_new_threshold.set()


@dp.message_handler(state=SetThreshold.waiting_for_new_threshold, content_types=types.ContentTypes.TEXT)
async def set_threshold_step_2(message: types.Message, state: FSMContext):  # обратите внимание, есть второй аргумент
    threshold = validate_threshold(message.text.replace(',', '.'))
    if not threshold:
        await message.answer('%s Threshold `%s` is invalid' % (emoji_error, message.text), reply_markup=main_keyboard, parse_mode=types.ParseMode.MARKDOWN)
    else:
        mongo_helper.add_threshold_to_db(threshold, message.chat.id)
        await message.answer('%s Threshold `%s ETH` set' % (emoji_ok, threshold), reply_markup=main_keyboard, parse_mode=types.ParseMode.MARKDOWN)
    await state.finish()


@dp.message_handler(lambda message: message.text == kb_info)
async def get_info(message: types.Message):
    addresses = mongo_helper.get_addresses_from_db(message.chat.id)
    addresses = ('\n'.join([i for i in addresses]))
    info = '%s *Your addresses:*\n\n%s\n\n%s *Alert threshold:* %s ETH' % \
           (emoji_list, addresses, emoji_flag, mongo_helper.get_threshold_from_db(message.chat.id))
    await message.answer(info, reply_markup=main_keyboard, parse_mode=types.ParseMode.MARKDOWN)


if __name__ == '__main__':
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('web3').setLevel(logging.WARNING)
    logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s', level=logging.INFO,
                        filename=config.log_name, datefmt='%d.%m.%Y %H:%M:%S')
    checker = UnbondedEthChecker('UnbondedEthChecker')
    checker.start()
    executor.start_polling(dp, skip_updates=True)
