import logging


from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    Application,
    ConversationHandler,
    MessageHandler,
    filters
)
import sqlite3


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s-%(message)s',
    level=logging.INFO
)


logger = logging.getLogger(__name__)


GENDER, SUBJECTSTRONG, SUBJECTWEAK, PHOTO, BIO = range(5)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    if db_find_user(user.username):
        await update.message.reply_text(
            f'Hello {user.first_name}! Glad to see you again'
        )
    else:
        context.user_data['user_id'] = user.id
        context.user_data['user_name'] = user.first_name
        context.user_data['user_surname'] = user.last_name
        context.user_data['username'] = user.username
        reply_keyboard = [['Male', 'Female']]
        await update.message.reply_text(
            f'Hello! Let\'s get you a study partner.'
            'Send /cancel to stop talking to me.\n\n'
            'Are you male of a female?',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder='Male or Female?'
            )
        )

    return GENDER


async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user

    reply_keyboard = [["Algebra", 'Calculus', 'Programming',
                       'Chemistry', 'History', 'Philosophy', 'Physics', 'Ecomonics']]

    logger.info(f'User: {user.first_name}, Gender: {update.message.text}')

    context.user_data['user_gender'] = update.message.text.lower()

    await update.message.reply_text(
        'Wonderful! Now let\'s choose a subject you are skilled in. ',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your strong subject.'
        ))
    
    return SUBJECTSTRONG


async def get_subjectstrong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["Algebra", 'Calculus', 'Programming',
                       'Chemistry', 'History', 'Philosophy', 'Physics', 'Ecomonics']]
    user = update.message.from_user
    logger.info(
        f'User: {user.first_name}, Strong Subject: {update.message.text}')
    context.user_data['subject_strong'] = update.message.text

    await update.message.reply_text(
        'Great! Now let\'s choose your lacking subject',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your weak subject.'
        )
    )
    return SUBJECTWEAK


async def get_subjectweak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    logger.info(
        f'User: {user.first_name}, Weak Subject: {update.message.text}')
    context.user_data['subject_weak'] = update.message.text

    await update.message.reply_text(
        'Okay, now upload your photo!',
        reply_markup=ReplyKeyboardRemove()
    )
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive(f'{user.username}_photo.jpg')
    logger.info(f'User: {user.first_name}, Photo: {user.username}_photo.jpg')
    await update.message.reply_text(
        'Gorgeous! Now write briefly about yourself.'
    )
    return BIO


async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    
    logging.info(f'User: {user.first_name}, BIO: {update.message.text}')

    context.user_data['user_bio'] = update.message.text

    await update.message.reply_text('Done! Now i will find somebody for you based on your subjects.')
    # Add user data to db
    userdata = context.user_data
    try:
        db_table_add_user(userdata['user_id'], userdata['user_name'], userdata['user_surname'], userdata['username'],
                          userdata['user_bio'], userdata['subject_strong'], userdata['subject_weak'], userdata['user_gender'])
        logger.info(
            f"User: {userdata['username']} added to the db succesfully.")
    except Exception as e:
        logger.error(
            f'Failed to add user: {userdata["username"]} to the db. ERROR: {e}')
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info(f'User {user.first_name} canceled the conversation')
    await update.message.reply_text('Goodbye!', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def match_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


def db_table_add_user(user_id: int, user_name: str, user_surname: str, username: str, user_bio: str, subject_strong: str, subject_weak: str, user_gender: str):
    cursor.execute('INSERT INTO chatusers (user_id, user_name, user_surname, username, user_bio, subject_strong, subject_weak, user_gender) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                   (user_id, user_name, user_surname, username, user_bio, subject_strong, subject_weak, user_gender))
    conn.commit()


def db_table_edit_user(user_id: int, db_key, db_value):
    try:
        cursor.execute(
            f"Update chatusers set {db_key} = {db_value} where user_id = {user_id}")
    except Exception as e:
        print('Failed to update sqlite table. ', e)


def db_find_user(username):
    try:
        user_found = cursor.execute(
            "SELECT * FROM chatusers WHERE username = ?", (username, ))
        user_found = user_found.fetchall()
        if len(user_found) > 0:
            return user_found
        else:
            print("User not found!")
            return None
    except Exception as e:
        print("Failed to find user in sqlite table: ", e)


if __name__ == 'main':
    conn = sqlite3.connect('database', check_same_thread=False)
    cursor = conn.cursor()

    app = ApplicationBuilder().token(
        '6593288094:AAEaoKHSXV_sQDGSj6C2W9lCF6bjL5f3Bmg').build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(filters.Regex('^(Male|Female)$'), get_gender)],
            SUBJECTSTRONG: [MessageHandler(filters.Regex('^(Algebra|Calculus|Programming|Chemistry|History|Philosophy|Physics|Ecomonics)$'), get_subjectstrong)],
            SUBJECTWEAK: [MessageHandler(filters.Regex('^(Algebra|Calculus|Programming|Chemistry|History|Philosophy|Physics|Ecomonics)$'), get_subjectweak)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)
