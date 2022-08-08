#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /track to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import os
import pandas as pd
import re

from functools import *

import functools
import operator

import gtfs_update
import google_drive_backup

import get_arrivals_departures
import get_alerts
import get_stops
import utils
import config

from datetime import datetime, timedelta
import pytz

import asyncio
import pickle

import logging

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )


from telegram import (
    constants,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    Defaults,
    PicklePersistence,
    PersistenceInput,
    CallbackQueryHandler,
    ApplicationHandlerStop,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# States
BOROUGH, STATION, GIVE_ALERT_INFO, GIVE_ROUTE_INFO, GIVE_SHOW_STOPS, SEND_USER_BUG_REPORT, SET_FAVOURITE, SET_FAVOURITE_DIRECTION = range(8)


# Keyboard borough buttons
reply_keyboard_borough = [["The Bronx","Manhattan","Queens"],["Staten Island","Brooklyn"]]
# reply_keyboard_borough = [["The Bronx \U0001F9F1","Manhattan \U0001F34E","Queens \U0001F310"],["Staten Island \U000026F4","Brooklyn \U0001F333"]]

# Convert list of lists into a flat list
boroughs = functools.reduce(operator.iconcat, reply_keyboard_borough, [])

# Make input field placeholder for borough choice
input_field_boroughs = boroughs[0]+", "+boroughs[1]+", "+boroughs[2]+", "+boroughs[3]+", or "+boroughs[4]+"?"

# Dictionary of various borough stations
dictStations = {
    "Manhattan": pd.read_csv(os.getcwd()+'/cache/stops_names/manhattan.txt',header=None).values.ravel(),
    "Brooklyn": pd.read_csv(os.getcwd()+'/cache/stops_names/brooklyn.txt',header=None).values.ravel(),
    "Queens": pd.read_csv(os.getcwd()+'/cache/stops_names/queens.txt',header=None).values.ravel(),
    "The Bronx": pd.read_csv(os.getcwd()+'/cache/stops_names/the_bronx.txt',header=None).values.ravel(),
    "Staten Island": pd.read_csv(os.getcwd()+'/cache/stops_names/staten_island.txt',header=None).values.ravel()
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the bot and welcomes the user."""
    user = update.message.from_user
    hour = datetime.now(pytz.timezone('America/New_York')).hour
    greeting = "Good morning" if 5<=hour<12 else "Good afternoon" if 12<=hour<18 else "Good evening" if 18<=hour<22 else "Good night"
    await update.message.reply_text(
        greeting + f", {user.mention_markdown_v2()}\! \U0001F5FD\n\n" +
            "Use /track to start tracking New York City's subway arrival times \U0001F687\n\n"+
            "Use /track\_favourite to quickly track your favourite station \U0001F680\n\n" +
            "Use /alerts to get real time alert information \U000026A0\n\n"+
            "Use /show\_stops to check train stops \U000024C2\n\n"+
            "Use /route\_info to get information on train operations \U00002139\n\n"+
            "Use /report\_bug to report something broken within the bot \U0000274C\n\n"+
            "Use /set\_favourite to set your favourite subway station \U00002B50\n\n"+
            "Use /help to get info on bot functionalities \U0001F64F\n\n"+
            "Use /donate to contribute to the bot expenses \U0001F680\n\n"+
            "Use /stop to stop this bot \U0000270B",
        parse_mode='MarkdownV2',
        reply_markup=ReplyKeyboardRemove()
    ),

    utils.recordUserInteraction(update, context)

    return ConversationHandler.END


async def track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the tracking and asks the user about their borough."""
    await update.effective_message.reply_text( # effective_message can be used if we are here from both a CommandHandler (in case of /track) and CallbackQueryHandler (in case of /set_favourite)
        "Select the borough from the list.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard_borough, one_time_keyboard=True, selective=True, input_field_placeholder=input_field_boroughs
        ),
    )

     # store wheather we are here from /track or /set_favourite commands
     # note that this is needed because if we went straight to borough, we would not know from which command we came from,
     # thus not knowing if we would need to show trains or store user preference 
    if hasattr(update.message, 'text'):
        context.user_data["setting_favourites"] = False # here from /track
    else:
        context.user_data["setting_favourites"] = True # here from /set_favourite

    return BOROUGH


# Ask user for station
async def borough(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the borough and asks for the station."""
    context.user_data["borough"] = update.effective_message.text
    df_stations = dictStations[update.effective_message.text]
    user = update.effective_message.from_user
    logger.info("Borough of %s: %s", user.first_name, update.effective_message.text)
    await update.effective_message.reply_text( # effective_message can be used if we are here from both a CommandHandler (in case of /track) and CallbackQueryHandler (in case of /set_favourite)
        "Select the station from the list",
        reply_markup=ReplyKeyboardMarkup(
            [[button] for button in df_stations], one_time_keyboard=True, selective=True, input_field_placeholder=df_stations[0]+", "+df_stations[1]+", "+df_stations[2]+", "+df_stations[3]+", "+df_stations[4]+"..."
        ),
    )

    utils.recordUserInteraction(update, context)
    
    if context.user_data["setting_favourites"]: # here from /set_favourite
        # try to open pickle file, otherwise create it
        try:
            dbfile = open('my_persistence', 'rb')     
            db = pickle.load(dbfile)
            dbfile.close()
        except:
            db = utils.makeNestedDict()
        # Store favourite borough
        db['users'][update.effective_user.id]['favourite_borough'] = update.effective_message.text
        # Its important to use binary mode
        dbfile = open('my_persistence', 'wb')
        # source, destination
        pickle.dump(db, dbfile)                     
        dbfile.close()
    
    return STATION



# Process the borough and station and find arrival times
async def station(update: Update, context: ContextTypes.DEFAULT_TYPE, trainsToShow) -> int:

    if context.user_data["setting_favourites"]: # here from /set_favourite
        # try to open pickle file, otherwise create it
        try:
            dbfile = open('my_persistence', 'rb')     
            db = pickle.load(dbfile)
            dbfile.close()
        except:
            db = utils.makeNestedDict()
        # Store favourite station
        db['users'][update.effective_user.id]['favourite_station'] = update.message.text
        # Its important to use binary mode
        dbfile = open('my_persistence', 'wb')
        # source, destination
        pickle.dump(db, dbfile)                     
        dbfile.close()

        # await update.message.reply_text(
        #     "Favourite station set correctly.",
        #     reply_markup=ReplyKeyboardRemove()
        # ),
        return await set_favourite_direction(update, context)

    else:

        """Stores the selected station and find arrival time."""

        # await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_text(
            "Processing... \U0001F52E",
        )

        # Load stops file
        df_stops = context.bot_data["df_stops"]

        # Load shapes file
        df_shapes = context.bot_data["df_shapes"]

        # Load stop_times and trips for current day
        df_stop_times = context.bot_data["df_stop_times"]
        df_trips = context.bot_data["df_trips"]


        userStation = update.message.text
        user = update.message.from_user

        logger.info("Station of %s: %s", user.first_name, update.message.text)

        # """ Send warning about Broad Channel ---> Broad Channel fixed now by skipping H19 trains?"""
        # if update.message.text == 'Broad Channel':
        #     await update.message.reply_markdown_v2(
        #         '__*Attention*__: Broad Channel train schedule might be incomplete and/or train headsigns might be wrong\.',
        #         reply_markup=ReplyKeyboardRemove(),
        #     )



        # tasks = [asyncio.to_thread(partial_get_arrivals_departures)]
        # trains, destinations, waiting_times, directions = await asyncio.gather(*tasks)
        
        # tasks = [asyncio.to_thread(partial_get_arrivals_departures)]
        # res = await asyncio.gather(*tasks)

        # trains, destinations, waiting_times, directions = await loop.run_in_executor(_executor, partial_get_arrivals_departures)

        # trains, destinations, waiting_times, directions = await ma.make_async(partial_get_arrivals_departures)

        trains, destinations, waiting_times, directions = await get_arrivals_departures.get_arrivals_departures(update, context, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow, userStation, favourite=False)

        # If the considered station is served by some train
        if (trains is not None) and (destinations is not None) and (waiting_times is not None) and (directions is not None):

            emoji_indication = [('\U0001F53C' if directions[i] == 'N' else ('\U0001F53D' if directions[i] == 'S' else directions[i])) for i in range(0,len(directions))]

            outStr = ""
            for i in range(0,len(trains)):
                outStr = outStr + emoji_indication[i] + " Train " + trains[i] + " (" + destinations[i] + ") - " + str(waiting_times[i]) + " min\n"

            await update.message.reply_text(
                outStr,
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await update.message.reply_text(
            "This station is not currently served by any train. Use /alerts to check the train status.",
        )

        if context.user_data["setting_favourites"]: # here from /set_favourite
            return
        else:
            await update.message.reply_text(
                "Select another borough and station, or send /stop if you don't want to \U0000270B",
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard_borough, one_time_keyboard=True, selective=True, input_field_placeholder=input_field_boroughs
                ),
            )
            return BOROUGH


async def track_favourite(update: Update, context: ContextTypes.DEFAULT_TYPE, trainsToShow) -> int:
        
        """Stores the selected station and find arrival time."""

        # try to open pickle file, otherwise create it
        try:
            dbfile = open('my_persistence', 'rb')     
            db = pickle.load(dbfile)
            dbfile.close()
        except:
            db = utils.makeNestedDict()

        if 'favourite_borough' not in db['users'][update.effective_user.id] or 'favourite_station' not in db['users'][update.effective_user.id]:
            await update.message.reply_text(
            "You first need to set your favourite station with /set_favourite.",
            )
            return ConversationHandler.END

    
        await update.message.reply_text(
            "Processing... \U0001F52E",
        )
        await update.message.reply_text(
            "Tracking favourite station: " + db['users'][update.effective_user.id]['favourite_borough'] + " - " + db['users'][update.effective_user.id]['favourite_station']
        )

        # Load stops file
        df_stops = context.bot_data["df_stops"]

        # Load shapes file
        df_shapes = context.bot_data["df_shapes"]

        # Load stop_times and trips for current day
        df_stop_times = context.bot_data["df_stop_times"]
        df_trips = context.bot_data["df_trips"]


        userStation = db['users'][update.effective_user.id]['favourite_station']


        trains, destinations, waiting_times, directions = await get_arrivals_departures.get_arrivals_departures(update, context, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow, userStation, favourite=True)

        # If the considered station is served by some train
        if (trains is not None) and (destinations is not None) and (waiting_times is not None) and (directions is not None):

            emoji_indication = [('\U0001F53C' if directions[i] == 'N' else ('\U0001F53D' if directions[i] == 'S' else directions[i])) for i in range(0,len(directions))]

            outStr = ""
            for i in range(0,len(trains)):
                outStr = outStr + emoji_indication[i] + " Train " + trains[i] + " (" + destinations[i] + ") - " + str(waiting_times[i]) + " min\n"

            await update.message.reply_text(
                outStr,
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await update.message.reply_text(
            "This station is not currently served by any train. Use /alerts to check the train status.",
        )

        if context.user_data["setting_favourites"]: # here from /set_favourite
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "Select another borough and station, or send /stop if you don't want to \U0000270B",
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard_borough, one_time_keyboard=True, selective=True, input_field_placeholder=input_field_boroughs
                ),
            )
            return BOROUGH





async def ask_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prints MTA's alert of selected route."""

    df_routes = context.bot_data["df_routes"]
    routes = df_routes['route_id'].values
    routes = ["42nd Street Shuttle (S)" if r=='GS' else "Franklin Avenue Shuttle (S)" if r=='FS' else "Rockaway Park Shuttle (S)" if r=='H' else r for r in routes]

    await update.message.reply_text(
        "Which train are you interested in?",
        reply_markup=ReplyKeyboardMarkup(
            [[button] for button in routes], one_time_keyboard=True, selective=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
        ),
    )

    utils.recordUserInteraction(update, context)

    return GIVE_ALERT_INFO


async def give_alert_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    """Prints MTA's alert of selected route."""
    user = update.message.from_user

    if update.message.text=="42nd Street Shuttle (S)":
        selected_train='GS'
    elif update.message.text=="Franklin Avenue Shuttle (S)":
        selected_train='FS'
    elif update.message.text=="Rockaway Park Shuttle (S)":
        selected_train='H'
    else:
        selected_train=update.message.text

    logger.info("Train of %s: %s", user.first_name, selected_train)

    alert = await get_alerts.get_alerts(update, context, selected_train)
    
    if len(alert)==0:
        await update.message.reply_text("No alerts provided for " + selected_train +' trains.')
    else:
        for i in range(len(alert)):
            alert_msg = ''
            for j in range(len(alert[i])):
                alert_msg = alert_msg + alert[i][j]+'\n\n'
            await update.message.reply_text(alert_msg,
                reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


async def ask_show_stops(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    """Prints stops of selected route."""

    df_routes = context.bot_data["df_routes"]
    routes = df_routes['route_id'].values
    routes = [x for x in routes if x not in ['5X','6X','7X','FX','W','Z']] # EXPRESS TRAINS ARE NOT IN routes.txt (WHAT TO DO?)
    routes = ["42nd Street Shuttle (S)" if r=='GS' else "Franklin Avenue Shuttle (S)" if r=='FS' else "Rockaway Park Shuttle (S)" if r=='H' else r for r in routes]

    await update.message.reply_text(
        "Which train are you interested in?",
        reply_markup=ReplyKeyboardMarkup(
            [[button] for button in routes], one_time_keyboard=True, selective=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
        ),
    )

    utils.recordUserInteraction(update, context)

    return GIVE_SHOW_STOPS


async def give_show_stops(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    if update.message.text=="42nd Street Shuttle (S)":
        selected_train='GS'
    elif update.message.text=="Franklin Avenue Shuttle (S)":
        selected_train='FS'
    elif update.message.text=="Rockaway Park Shuttle (S)":
        selected_train='H'
    else:
        selected_train=update.message.text

    stops_list = await get_stops.get_stops(update, context, selected_train)

    stops_msg = '*'+update.message.text + ' Train Stops*\n\n'
    for i in range(len(stops_list)):
        if i == 0 or i == len(stops_list)-1:
            stops_msg = stops_msg + "\U000025CF " + stops_list[i] + '\n'
        else:
            stops_msg = stops_msg + "\U00002523 " + stops_list[i] + '\n'
    stops_msg = stops_msg.replace("-", "\-"); stops_msg = stops_msg.replace("(", "\("); stops_msg = stops_msg.replace(")", "\)")

    await update.message.reply_markdown_v2(stops_msg,
        reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


async def ask_route_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prints MTA's information of selected route."""

    df_routes = context.bot_data["df_routes"]
    routes = df_routes['route_id'].values
    routes = ["42nd Street Shuttle (S)" if r=='GS' else "Franklin Avenue Shuttle (S)" if r=='FS' else "Rockaway Park Shuttle (S)" if r=='H' else r for r in routes]

    await update.message.reply_text(
        "Which train are you interested in?",
        reply_markup=ReplyKeyboardMarkup(
            [[button] for button in routes], one_time_keyboard=True, selective=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
        ),
    )

    utils.recordUserInteraction(update, context)
    
    return GIVE_ROUTE_INFO


async def give_route_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prints MTA's information of selected route."""

    df_routes = context.bot_data["df_routes"]

    user = update.message.from_user

    if update.message.text=="42nd Street Shuttle (S)":
        selected_train='GS'
    elif update.message.text=="Franklin Avenue Shuttle (S)":
        selected_train='FS'
    elif update.message.text=="Rockaway Park Shuttle (S)":
        selected_train='H'
    else:
        selected_train=update.message.text

    logger.info("Train of %s: %s", user.first_name, selected_train)

    await update.message.reply_text(
        df_routes[df_routes['route_id'].str.contains(selected_train)]['route_desc'].values[0],
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def get_user_bug_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    if update.message.chat.type == constants.ChatType.GROUP or update.message.chat.type == constants.ChatType.SUPERGROUP:  # can't report bugs when using bot in groups without admin rights
        chat_member = await context.bot.get_chat_member(chat_id=update.effective_chat.id,user_id=context.bot.id)
        if chat_member.status!=constants.ChatMemberStatus.ADMINISTRATOR:
            await update.message.reply_text(
                "This bot must be a group administrator to use this command \U000026D4",
                reply_markup=ReplyKeyboardRemove()
            )
            return

    # otherwise allow users to report bugs with the bot
    await update.message.reply_text(
        "This command is intended for bug reporting only. Send your message below with as many details as possible.",
        reply_markup=ReplyKeyboardRemove(),
    )

    utils.recordUserInteraction(update, context)

    return SEND_USER_BUG_REPORT


async def send_user_bug_report(update: Update, context: ContextTypes.DEFAULT_TYPE, max_daily_reports) -> int:

    # try to open pickle file, otherwise create it
    try:
        dbfile = open('my_persistence', 'rb')     
        db = pickle.load(dbfile)
        dbfile.close()
    except:
        db = utils.makeNestedDict()
    
    
    if update.effective_user.id in db['users'] and 'last_bug_report' in db['users'][update.effective_user.id] and 'total_bug_reports' in db['users'][update.effective_user.id]:
        if (datetime.now()-db['users'][update.effective_user.id]['last_bug_report']).total_seconds()<86400 and db['users'][update.effective_user.id]['total_bug_reports']>=max_daily_reports:
            await update.message.reply_text(
                "Bug reports limit reached. Please, try again tomorrow.",
            )
            return ConversationHandler.END
        else:
            if (datetime.now()-db['users'][update.effective_user.id]['last_bug_report']).total_seconds()>=86400: # if last bug report was sent more than 24 hours ago
                db['users'][update.effective_user.id]['last_bug_report'] = datetime.now()
                db['users'][update.effective_user.id]['total_bug_reports'] = 1
            else:
                db['users'][update.effective_user.id]['total_bug_reports'] += 1
    else:
        db['users'][update.effective_user.id]['last_bug_report'] = datetime.now()
        db['users'][update.effective_user.id]['total_bug_reports'] = 1


    # Its important to use binary mode
    dbfile = open('my_persistence', 'wb')
    
    # source, destination
    pickle.dump(db, dbfile)                     
    dbfile.close()

    """Forward user bug reports to private channel"""
    await update.message.forward(chat_id='-1001708464995')

    await update.message.reply_text(
        "Thank you for reporting a bug. We are doing our best to fix them as soon as possible \U0001F64F"
    )

    return ConversationHandler.END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stops and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s stopped the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! \U0001F44B I hope we can talk again some day.",
        reply_markup=ReplyKeyboardRemove()
    )

    utils.recordUserInteraction(update, context)

    return ConversationHandler.END


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays info on how to use the bot."""
    user = update.message.from_user
    hour = datetime.now(pytz.timezone('America/New_York')).hour
    greeting = "Good morning" if 5<=hour<12 else "Good afternoon" if 12<=hour<18 else "Good evening" if 18<=hour<22 else "Good night"
    await update.message.reply_text(
        greeting + f", {user.mention_markdown_v2()}\! \U0001F5FD\n\n" +
            "Use /track to start tracking New York City's subway arrival times \U0001F687\n\n"+
            "Use /track\_favourite to quickly track your favourite station \U0001F680\n\n" +
            "Use /alerts to get real time alert information \U000026A0\n\n"+
            "Use /show\_stops to check train stops \U000024C2\n\n"+
            "Use /route\_info to get information on train operations \U00002139\n\n"+
            "Use /report\_bug to report something broken within the bot \U0000274C\n\n"+
            "Use /set\_favourite to set your favourite subway station \U00002B50\n\n"+
            "Use /help to get info on bot functionalities \U0001F64F\n\n"+
            "Use /donate to contribute to the bot expenses \U0001F680\n\n"+
            "Use /stop to stop this bot \U0000270B",
        parse_mode='MarkdownV2',
        reply_markup=ReplyKeyboardRemove()
    )

    utils.recordUserInteraction(update, context)

    return ConversationHandler.END


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays info on donate."""
    await update.message.reply_text(
        "If you find this bot useful, please chip in\! Your support will help to keep this bot accessible to everyone \U0001F4AA\n\n"+
        "Thank you\!\n\n"+
        "[PayPal donation link](https://www.paypal.com/donate/?business=53MCWVS8WMAM4&no_recurring=0&currency_code=USD)",
        parse_mode='MarkdownV2',
        reply_markup=ReplyKeyboardRemove()
    )

    utils.recordUserInteraction(update, context)

    return ConversationHandler.END



@utils.restricted # only accessible if `user_id` is in `LIST_OF_ADMINS`
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # try to open pickle file, otherwise create it
    try:
        dbfile = open('my_persistence', 'rb')     
        db = pickle.load(dbfile)
        dbfile.close()
    except:
        db = utils.makeNestedDict()

    total_bot_interactions = 0
    last_bot_usage = datetime.min
    now = datetime.now()
    daily_active_users = 0
    daily_bot_interactions = 0
    for (key, value) in db['users'].items():
        total_bot_interactions += value['total_interactions']
        if value['last_bot_usage'] > last_bot_usage:
            last_bot_usage = value['last_bot_usage']
        if (now-value['last_bot_usage']).total_seconds()<86400:
            daily_active_users += 1
            daily_bot_interactions += value['daily_interactions']
    
    await update.message.reply_text(
        "*Total users:*\n    " + str(len(db['users'].keys())) + "\n" +
        "*Total bot interactions:*\n    " + str(total_bot_interactions) + "\n" +
        "*Daily active users:*\n    " + str(daily_active_users) + "\n" +
        "*Daily bot interactions:*\n    " + str(daily_bot_interactions) + "\n" +
        "*Last bot usage:*\n    " + last_bot_usage.strftime("%d/%m/%Y, %H:%M:%S") + "\n" +
        "*Last GTFS update:*\n    " + db['last_gtfs_update'].strftime("%d/%m/%Y, %H:%M:%S"),
        parse_mode='MarkdownV2',
        reply_markup=ReplyKeyboardRemove()
    )
    


async def error_borough(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    await update.message.reply_text(
        "Do not type the borough name. Select a borough from the list below, or send /stop if you don't want to \U0000270B",
        reply_markup=ReplyKeyboardMarkup(
                reply_keyboard_borough, one_time_keyboard=True, selective=True, input_field_placeholder=input_field_boroughs
            ),
    )
    return BOROUGH


async def error_station(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    df_stations = dictStations[context.user_data["borough"]]

    await update.message.reply_text(
        "Do not type the station name. Select a station from the list, or send /stop if you don't want to \U0000270B",
        reply_markup=ReplyKeyboardMarkup(
                [[button] for button in df_stations], one_time_keyboard=True, selective=True, input_field_placeholder=df_stations[0]+", "+df_stations[1]+", "+df_stations[2]+", "+df_stations[3]+", "+df_stations[4]+"..."
            ),
    )
    return STATION


async def error_alert_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    df_routes = context.bot_data["df_routes"]
    routes = df_routes['route_id'].values

    await update.message.reply_text(
        "Do not type the train name. Select a train from the list below, or send /stop if you don't want to \U0000270B",
        reply_markup=ReplyKeyboardMarkup(
                [[button] for button in routes], one_time_keyboard=True, selective=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
            ),
    )
    return GIVE_ALERT_INFO


async def error_show_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    df_routes = context.bot_data["df_routes"]
    routes = df_routes['route_id'].values

    await update.message.reply_text(
        "Do not type the train name. Select a train from the list below, or send /stop if you don't want to \U0000270B",
        reply_markup=ReplyKeyboardMarkup(
                [[button] for button in routes], one_time_keyboard=True, selective=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
            ),
    )
    return GIVE_SHOW_STOPS


async def error_route_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    df_routes = context.bot_data["df_routes"]
    routes = df_routes['route_id'].values

    await update.message.reply_text(
        "Do not type the train name. Select a train from the list below, or send /stop if you don't want to \U0000270B",
        reply_markup=ReplyKeyboardMarkup(
                [[button] for button in routes], one_time_keyboard=True, selective=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
            ),
    )
    return GIVE_ROUTE_INFO





async def set_favourite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with inline buttons attached."""
    keyboard = [
        [
            InlineKeyboardButton("\U0001F44D", callback_data="Yes"),
            InlineKeyboardButton("\U0001F44E", callback_data="No"),
        ],
    ]

    await update.message.reply_text("Do you want to set a favourite subway station for quick train tracking?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SET_FAVOURITE


async def set_favourite_direction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with inline buttons attached."""
    keyboard = [
        [
            InlineKeyboardButton("Uptown only", callback_data="N"),
            InlineKeyboardButton("Downtown only", callback_data="S"),
            InlineKeyboardButton("Both", callback_data="NS"),
        ],
    ]

    await update.message.reply_text("Which train direction are you interested in?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SET_FAVOURITE_DIRECTION




async def button_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    if query.data == 'Yes':
        await query.edit_message_text(text="Great!")
        await track(update,context)
    elif query.data == 'No':
        await query.edit_message_text("That's okay.")

    return BOROUGH


async def button_pressed_direction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    dir_text = "northbound trains only" if query.data=='N' else "southbound trains only" if query.data=='S' else "both northbound and southbound trains"
    dir_emoji = "\U0001F53C" if query.data=='N' else "\U0001F53D" if query.data=='S' else "\U0001F53C\U0001F53D"
    await query.edit_message_text(text=f"Alright! Tracking {dir_text} {dir_emoji}\n\nYou can track your favourite train with the /track_favourite command.")

    # try to open pickle file, otherwise create it
    try:
        dbfile = open('my_persistence', 'rb')     
        db = pickle.load(dbfile)
        dbfile.close()
    except:
        db = utils.makeNestedDict()
    # Store favourite borough
    db['users'][update.effective_user.id]['favourite_direction'] = query.data
    # Its important to use binary mode
    dbfile = open('my_persistence', 'wb')
    # source, destination
    pickle.dump(db, dbfile)                     
    dbfile.close()
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    await update.message.reply_text("Invalid command. Press /help to see the bot commands.",
        reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END



async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([('track','Track real time subway arrival times'),
                                           ('track_favourite','Quick train tracking in favourite station'),
                                           ('alerts','Retrieve real time service alerts'),
                                           ('show_stops','Check train stops'),
                                           ('route_info','Get information on train operations'),
                                           ('report_bug','Send a message to report a bug'),
                                           ('set_favourite','Set favourite subway station'),
                                           ('help','Get info on bot functionalities'),
                                           ('donate','Contribute to the bot expenses'),
                                           ('stop','Stop the bot')
                                          ])


def main() -> None:

    dir = os.getcwd()+'/gtfs static files/'
    filename = 'google_transit_supplemented.zip'

    googleDriveFolderName = 'NYC Subway Train Tracker Telegram Bot - persistence files backup'


    # Select how many incoming trains to show in output
    trainsToShow = 5

    # Maximum number od daily bug reports per user (to prevent spam messages)
    max_daily_reports = 3


    # Perform initial download/update of local files if needed
    loop = asyncio.get_event_loop()
    gtfs_update_coroutine = gtfs_update.gtfs_update(dir,filename)
    loop.run_until_complete(gtfs_update_coroutine)


    # Load routes file
    df_routes = pd.read_csv(os.getcwd()+'/gtfs static files/routes.txt')

    # Load alphabetically sorted stations file
    sortedStations = pd.read_csv(os.getcwd()+'/cache/stops_names/sorted_stations.txt',header=None).values.ravel().tolist()

    # partial functions needed to pass additional arguments to them in order to avoid reading csv files each time
    partial_station = partial(station, trainsToShow=trainsToShow)
    partial_track_favourite = partial(track_favourite, trainsToShow=trainsToShow)
    partial_forward_user_bug_report = partial(send_user_bug_report, max_daily_reports=max_daily_reports)

    """Run the bot."""

    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    """Instantiate a Defaults object"""
    defaults = Defaults(disable_web_page_preview=True, tzinfo=pytz.timezone('America/New_York'))


    # Pickle persistence file to make context data survive bot restarts
    bot_persistence = PicklePersistence(filepath ='PicklePersistence',store_data=PersistenceInput(bot_data=False, chat_data=True, user_data=True)) # don't save bot_data to save storage space
    
    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)
        .defaults(defaults)
        .persistence(persistence=bot_persistence)
        .build()
    )

    # Add job that daily updates the database 
    job_queue = application.job_queue

    nyc_time_gtfs_update = datetime(2000, 1, 1, 4, 0, 0) # day is not important, just write correct time for NYC timezone
    nyc_time_google_drive_backup = datetime(2000, 1, 1, 4, 30, 0) # day is not important, just write correct time for NYC timezone

    # This job is an hack to store GTFS supplemented .csv files in context.bot_data during initial code execution
    job_once = job_queue.run_once(gtfs_update.gtfs_update,when=datetime.now(pytz.timezone('America/New_York'))+timedelta(seconds=5),data=(dir,filename),name='gtfs_store_context') # use data to pass arguments to callback
    
    # This job updates the GTFS supplemented .csv files daily
    job_daily = job_queue.run_daily(gtfs_update.gtfs_update,time=nyc_time_gtfs_update,days=(0,1,2,3,4,5,6),data=(dir,filename),name='gtfs_daily_update') # use data to pass arguments to callback
    job_daily = job_queue.run_daily(google_drive_backup.google_drive_backup,time=nyc_time_google_drive_backup,days=(0,1,2,3,4,5,6),data=(googleDriveFolderName),name='google_drive_daily_backup') # use data to pass arguments to callback


    # Add conversation handler with the states BOROUGH, STATION, GIVE_ALERT_INFO, GIVE_SHOW_STOPS, GIVE_ROUTE_INFO, and SEND_USER_BUG_REPORT
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("track", track),
            CommandHandler("track_favourite", partial_track_favourite),
            CommandHandler("alerts", ask_alerts),
            CommandHandler("show_stops", ask_show_stops),
            CommandHandler("route_info", ask_route_info),
            CommandHandler("report_bug", get_user_bug_report),
            CommandHandler("set_favourite", set_favourite),
        ],
        states={ 
            BOROUGH: [
                MessageHandler(filters.Text([j for i in reply_keyboard_borough for j in i]), borough, block=False),
                MessageHandler(~filters.COMMAND, error_borough, block=False),
            ],
            STATION: [
                MessageHandler(filters.Text(sortedStations), partial_station, block=False),
                MessageHandler(~filters.COMMAND, error_station, block=False),
            ],
            GIVE_ALERT_INFO: [
                MessageHandler(filters.Text(df_routes['route_id'].tolist()+["42nd Street Shuttle (S)","Franklin Avenue Shuttle (S)","Rockaway Park Shuttle (S)"]), give_alert_info, block=False),
                MessageHandler(~filters.COMMAND, error_alert_info, block=False),
            ],
            GIVE_SHOW_STOPS: [
                MessageHandler(filters.Text(df_routes['route_id'].tolist()+["42nd Street Shuttle (S)","Franklin Avenue Shuttle (S)","Rockaway Park Shuttle (S)"]), give_show_stops, block=False),
                MessageHandler(~filters.COMMAND, error_show_info, block=False),
            ],
            GIVE_ROUTE_INFO: [
                MessageHandler(filters.Text(df_routes['route_id'].tolist()+["42nd Street Shuttle (S)","Franklin Avenue Shuttle (S)","Rockaway Park Shuttle (S)"]), give_route_info, block=False),
                MessageHandler(~filters.COMMAND, error_route_info, block=False),
            ],
            SEND_USER_BUG_REPORT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, partial_forward_user_bug_report, block=False),
            ],
            SET_FAVOURITE: [
                CallbackQueryHandler(button_pressed),
            ],
            SET_FAVOURITE_DIRECTION: [
                CallbackQueryHandler(button_pressed_direction),
            ]
        },
        fallbacks=[CommandHandler('stop', stop), MessageHandler(filters.COMMAND, cancel)],
        persistent=True,
        name='ConversationHandler',
        allow_reentry = True
    )

    # Add handlers 
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    application.add_handler(CommandHandler('donate', donate))
    application.add_handler(CommandHandler('stop', stop)) # added here to let the user use it even if there is no active conversation 
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(conv_handler)



    # Heroku webhook implementation
    PRODUCTION = False
    if PRODUCTION:
        PORT = int(os.environ.get('PORT', 5000))
        # add handlers
        application.run_webhook(
            listen = "0.0.0.0",
            port = PORT,
            url_path = BOT_TOKEN,
            webhook_url = "https://nyc-subway-train-tracker.herokuapp.com/" + BOT_TOKEN
        )
    else:
        # Run the bot until Ctrl-C is pressed
        application.run_polling(timeout=30)




if __name__ == "__main__":

    # Add your personal MTA API key
    os.environ["MTA_API_key"] = config.MTA_API_key

    # Add your personal Telegram bot's token.
    os.environ["BOT_TOKEN"] = config.BOT_TOKEN

    main()

    # while True:
    #     try:
    #         logger.info("Starting bot")
    #         main()
    #     except Exception:
    #         logger.exception("Something bad happened. Restarting bot.")