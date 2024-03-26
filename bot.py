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
  user_data = context.user_data
  user_id = user_data['user_id']
  matched_users = db_find_match(user_data)
  if not matched_users:
      await update.message.reply_text("Unfortunately, no suitable partners have been found at the moment. Try again later!")
      return

  best_match = select_best_match(matched_users, user_data)  # Implement this function

  if not best_match:
      await update.message.reply_text("Couldn't find a better match for your preference. We picked up someone for you anyway. You can repeat the search if you want!")
  
  partner_data = cursor.execute("SELECT * FROM chatusers WHERE user_id = ?", (best_match['user_id'],)).fetchone()
  await notify_users(user_data, partner_data)
  await update.message.reply_text("Great news! We found a match for you. Check your messages to start chatting!")
  return ConversationHandler.END


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
def db_find_match(user_data):
    try:
        matched_users = cursor.execute("""
            SELECT * FROM chatusers 
            WHERE (subject_strong = ? AND subject_weak = ?) 
            OR (subject_strong = ? AND subject_weak = ?)
            """,
            (user_data['subject_weak'], user_data['subject_strong'],
             user_data['subject_strong'], user_data['subject_weak'])).fetchall()
        return matched_users
    except Exception as e:
        print("Failed to find match in sqlite table: ", e)
        return None
def select_best_match(matched_users, user_data):
   
    # Implement a scoring system based on compatibility factors
    # Consider gender preferences, subject strength/weakness, and other factors

    if not matched_users:
        return None

    best_match = matched_users[0]
    for user in matched_users:
        if user['user_gender'] == user_data['user_gender_pref']:
            best_match = user
        elif user['subject_strong'] == user_data['subject_weak']:
            best_match = user

    return best_match
def notify_users(user_data, partner_data):
    """
    Sends messages to both the user and the matched user to initiate communication.

    Args:
        user_data: The user's data.
        partner_data: The matched user's data.
    """
    # Use Telegram Bot API to send messages to specific users
    # Include introductions or contact information in the messages

    from telegram import Bot

    bot = Bot(token='6593288094:AAEaoKHSXV_sQDGSj6C2W9lCF6bjL5f3Bmg')

    message = f"Привет! \n\n" \
              f"Я нашел тебе партнера для учебы: {partner_data['user_name']}.\n" \
              f"Его/ее сильная сторона - {partner_data['subject_strong']}, а слабая - {partner_data['subject_weak']}.\n" \
              f"Начните общаться, чтобы помочь друг другу!\n\n" \
              f"**Контактная информация:**\n" \
              f"{partner_data['username']}"

    bot.send_message(chat_id=user_data['user_id'], text=message)

    message = f"Привет! \n\n" \
              f"Я нашел тебе партнера для учебы: {user_data['user_name']}.\n" \
              f"Его/ее сильная сторона - {user_data['subject_strong']}, а слабая - {user_data['subject_weak']}.\n" \
              f"Начните общаться, чтобы помочь друг другу!\n\n" \
              f"**Контактная информация:**\n" \
              f"{user_data['username']}"

    bot.send_message(chat_id=partner_data['user_id'], text=message)



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
