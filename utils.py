from functools import wraps
import constants
import collections

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
)

from datetime import datetime
import pickle


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=action)
            return await func(update, context,  *args, **kwargs)
        return command_func
    
    return decorator


LIST_OF_ADMINS = constants.LIST_OF_ADMINS
def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print(f"Unauthorized access denied for {user_id}.")
            await update.message.reply_text(
                "You are not authorized to use this command.",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


def makeNestedDict():
    return collections.defaultdict(makeNestedDict)


def recordUserInteraction(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # try to open pickle file, otherwise create it
    try:
        dbfile = open('my_persistence', 'rb')     
        db = pickle.load(dbfile)
        dbfile.close()
    except:
        db = makeNestedDict()
    

    if 'total_interactions' in db['users'][update.effective_user.id]:
        db['users'][update.effective_user.id]['total_interactions'] += 1
    else:
        db['users'][update.effective_user.id]['total_interactions'] = 1

    if 'daily_interactions' in db['users'][update.effective_user.id] and db['users'][update.effective_user.id]['last_bot_usage'].day==datetime.today().day:
        db['users'][update.effective_user.id]['daily_interactions'] += 1
    else:
        db['users'][update.effective_user.id]['daily_interactions'] = 1


    db['users'][update.effective_user.id]['last_bot_usage'] = datetime.now()


    # Its important to use binary mode
    dbfile = open('my_persistence', 'wb')
    
    # source, destination
    pickle.dump(db, dbfile)                     
    dbfile.close()