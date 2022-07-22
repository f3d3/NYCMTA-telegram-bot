from functools import wraps

from telegram import __version__ as TG_VER
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ContextTypes,
)


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=action)
            return await func(update, context,  *args, **kwargs)
        return command_func
    
    return decorator


@send_action(ChatAction.TYPING)
async def findStops(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_train):

    df_stop_times = context.bot_data["df_stop_times"]
    df_stops = context.bot_data["df_stops"]
    
    if len(selected_train)==1:
        df_stop_times_filtered = df_stop_times[df_stop_times['trip_id'].str.contains(selected_train+"..S", regex=False)]
    else:
        df_stop_times_filtered = df_stop_times[df_stop_times['trip_id'].str.contains(selected_train+".S", regex=False)]

    stop_ids = sorted(df_stop_times_filtered['stop_id'].unique())

    ret = df_stops.set_index('stop_id').loc[stop_ids].reset_index(inplace=False)
    stops_list = ret["stop_name"].tolist()

    return stops_list