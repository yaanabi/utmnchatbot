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
 
GENDER, SUBJECTSTRONG, SUBJECTWEAK, BIO = range(4)
 
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
 
 
async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
 
    reply_keyboard = [["Algebra", 'Calculus', 'Programming',
                       'Chemistry', 'History', 'Philosophy', 'Physics', 'Economics']]
 
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
                       'Chemistry', 'History', 'Philosophy', 'Physics', 'Economics']]
    user = update.message.from_user
    logger.info(
        f'User: {user.first_name}, Strong Subject: {update.message.text}')
    reply_keyboard[0].remove(update.message.text)
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
        'Okay, now write briefly about yourself!',
        reply_markup=ReplyKeyboardRemove()
    )
    return BIO
 
 
async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
 
    logging.info(f'User: {user.first_name}, BIO: {update.message.text}')
 
    context.user_data['user_bio'] = update.message.text
 
    await update.message.reply_text('Done! Now i type /match to find somebody based on your subjects.')
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
 
async def edit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db_find_user(update.effective_user.username):
        if db_delete_user(update.effective_user.id):
            await update.message.reply_text("You successfully removed your information! Do /start to fill it again!")
        else:
            await update.message.reply_text('Sorry there was an error, try later!')
    else:
        await update.message.reply_text("There is no information about you. Do /start")

async def show_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = db_find_user(update.effective_user.username)
        if user:
            user = user[0]
            await update.message.reply_text(f'Gender: {user[-1]}\nStrong subject: {user[-3]}\nWeak subject: {user[-2]}\nBIO: {user[-4]}')
        else:
            await update.message.reply_text('There is no data of you. Do /start  first')
    except Exception as e: 
        logger.error(f'Error while showing user-{update.effective_user}: {e}')
        await update.message.reply_text('Cant\'t show your profile, try another time!')
 
async def match_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = db_find_user(update.effective_user.username)
        if user:
            user = user[0]
            user_subject_strong = user[-3]
            user_subject_weak = user[-2]
            matched_users = db_matched_users(user_subject_strong, user_subject_weak)
            if matched_users:
                await update.message.reply_text('Here is matched users based on your subjects.')
                for match in matched_users:
                    await update.message.reply_text(f"TG: @{match[-5]}\nName: {match[2]}\nGender: {match[-1]}\nSubject strong: {match[-3]}\nSubject weak: {match[-2]}\nBIO: {match[-4]}")
            else:
                await update.message.reply_text('There is no matching users for you 😕')
        else:
            await update.message.reply_text('There is no data of you. Do /start  first')
    except Exception as e: 
        logger.error(f'Error while matching user-{update.effective_user}: {e}')
        await update.message.reply_text('There was an error while trying to find you a matching person, try another time!')
 
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info(f'User {user.first_name} canceled the conversation')
    await update.message.reply_text('Goodbye!', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
 
 
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, i didn't understand that command")
 
 
# DB functions 
 
def db_delete_user(user_id: int):
    try: 
        cursor.execute(f"DELETE FROM chatusers WHERE user_id = {user_id}")
        conn.commit()
        return True
    except Exception as e:
        logger.error(f'Error while deleting user-{user_id} from db: {e}')
        return False
 
def db_table_add_user(user_id: int, user_name: str, user_surname: str, username: str, user_bio: str, subject_strong: str, subject_weak: str, user_gender: str):
    cursor.execute('INSERT INTO chatusers (user_id, user_name, user_surname, username, user_bio, subject_strong, subject_weak, user_gender) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                   (user_id, user_name, user_surname, username, user_bio, subject_strong, subject_weak, user_gender))
    conn.commit()
 
 
def db_table_edit_user(user_id: int, db_key: str, db_value):
    try:
        cursor.execute(
            f"Update chatusers set {db_key} = '{db_value}' where user_id = {user_id}")
        return True
    except Exception as e:
        print('Failed to update sqlite table. ', e)
        return None
 
def db_matched_users(subject_strong: str, subject_weak: str):
    print(f"SELECT * FROM chatusers WHERE subject_strong = '{subject_weak}' AND subject_weak = '{subject_strong}'")
    users_found = cursor.execute(f"SELECT * FROM chatusers WHERE subject_strong = '{subject_weak}' AND subject_weak = '{subject_strong}'")
    users_found = users_found.fetchall()
    if len(users_found) > 0:
        return users_found
    else:
        print("Users not found!")
        return None
 
 
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
 
 
if __name__ == '__main__':
    conn = sqlite3.connect('database.sqlite3', check_same_thread=False)
    cursor = conn.cursor()
 
    app = ApplicationBuilder().token(
        '6593288094:AAEaoKHSXV_sQDGSj6C2W9lCF6bjL5f3Bmg').build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(filters.Regex('^(Male|Female)$'), get_gender)],
            SUBJECTSTRONG: [MessageHandler(filters.Regex('^(Algebra|Calculus|Programming|Chemistry|History|Philosophy|Physics|Economics)$'), get_subjectstrong)],
            SUBJECTWEAK: [MessageHandler(filters.Regex('^(Algebra|Calculus|Programming|Chemistry|History|Philosophy|Physics|Economics)$'), get_subjectweak)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('edit_info', edit_info))
    app.add_handler(CommandHandler('me', show_user))
    app.add_handler(CommandHandler('match', match_user))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    app.run_polling(allowed_updates=Update.ALL_TYPES)
