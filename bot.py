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

import pandas as pd
import re

from functools import *

import functools
import operator

# import time
# from concurrent.futures import ThreadPoolExecutor
# _executor = ThreadPoolExecutor(10)

# from protobuf_to_dict import protobuf_to_dict

import create_cache as cc
import findArrivalTime as fat
import findAlerts as fa

from datetime import date, datetime

# import asyncio

import os

import logging

from telegram import Bot, ForceReply, __version__ as TG_VER

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



from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, Chat
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import make_async as ma


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States
BOROUGH, STATION, INITIAL_STATE, GIVE_ALERT_INFO, GIVE_ROUTE_INFO, FORWARD_USER_BUG_REPORT = range(6)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    user = update.message.from_user
    hour = datetime.now().hour
    greeting = "Good morning" if 5<=hour<12 else "Good afternoon" if hour<18 else "Good evening"
    await update.message.reply_text(
        greeting + f", {user.first_name}!\n\n" +
            "Use /track to start tracking New York City's subway arrival times \U0001F687\U0001F5FD\n\n"+
            "Use /alerts to get real time alert information \U000026A0\n\n"+
            "Use /route_info to get information on train operations \U00002139\n\n"+
            "Use /report_bug to report something broken within the bot \U0000274C\n\n"+
            "Use /donate to contribute to the bot expenses \U0001F680\n\n"+
            "Use /stop to stop this bot \U0000270B",
        reply_markup=ReplyKeyboardRemove()
    ),

    return INITIAL_STATE


#async def track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_keyboard_borough,input_field_placeholder) -> int:

    """Starts the tracking and asks the user about their borough."""

    await update.message.reply_text(
        "Select the borough from the list, or send /stop to stop talking to me.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard_borough, one_time_keyboard=True, input_field_placeholder=input_field_placeholder
        ),
    )

    return BOROUGH


# Ask user for station
async def borough(update: Update, context: ContextTypes.DEFAULT_TYPE, dictStations) -> int:
    """Stores the borough and asks for the station."""
    context.user_data["borough"] = update.message.text

    df_stations = dictStations[update.message.text]

    user = update.message.from_user
    logger.info("Borough of %s: %s", user.first_name, update.message.text)
    await update.message.reply_text(
        "Select the station from the list",
        reply_markup=ReplyKeyboardMarkup(
            [[button] for button in df_stations], one_time_keyboard=True, input_field_placeholder=df_stations[0]+", "+df_stations[1]+", "+df_stations[2]+", "+df_stations[3]+", "+df_stations[4]+"..."
        ),
    )

    return STATION


# partial_findArrivalTime = partial(fat.findArrivalTime, update=Update, context=ContextTypes.bot_data)


# Process the borough and station and find arrival times
async def station(update: Update, context: ContextTypes.DEFAULT_TYPE, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow, reply_keyboard_borough, input_field_placeholder) -> int:

    # await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text(
        "Processing... \U0001F52E",
    )

    """Stores the selected station and find arrival time."""
    userStation = update.message.text
    user = update.message.from_user
    logger.info("Station of %s: %s", user.first_name, update.message.text)

    """ Send warning about Broad Channel ---> Broad Channel fixed now by skipping H19 trains?"""
    if update.message.text == 'Broad Channel':
        await update.message.reply_markdown_v2(
            '__*Attention*__: Broad Channel train schedule might be incomplete and/or train headsigns might be wrong\.',
            reply_markup=ReplyKeyboardRemove(),
        )

    # tasks = [asyncio.to_thread(partial_findArrivalTime)]
    # trains, destinations, waiting_times, directions = await asyncio.gather(*tasks)
    
    # tasks = [asyncio.to_thread(partial_findArrivalTime)]
    # res = await asyncio.gather(*tasks)

    # trains, destinations, waiting_times, directions = await loop.run_in_executor(_executor, partial_findArrivalTime)

    # trains, destinations, waiting_times, directions = await ma.make_async(partial_findArrivalTime)

    trains, destinations, waiting_times, directions = await fat.findArrivalTime_async(update, context, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow, userStation)

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
        "This station is not currently served by any train. Use /train_alert to check the train status.",
    )

    await update.message.reply_text(
        "Select another borough and station, or send /stop if you don't want to \U0000270B",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard_borough, one_time_keyboard=True, input_field_placeholder=input_field_placeholder
        ),
    )

    return BOROUGH


async def ask_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE, df_trains) -> int:
    
    """Prints MTA's alert of selected route."""

    context.user_data["trains"] = df_trains
    routes = df_trains['route_id'].values

    routes = ["42nd Street Shuttle (S)" if r=='GS' else "Franklin Avenue Shuttle (S)" if r=='FS' else "Rockaway Park Shuttle (S)" if r=='H' else r for r in routes]

    await update.message.reply_text(
        "Which train are you interested in?",
        reply_markup=ReplyKeyboardMarkup(
            [[button] for button in routes], one_time_keyboard=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
        ),
    )

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

    alert = await fa.findAlerts_async(update, context, selected_train)
    
    if len(alert)==0:
        await update.message.reply_text("No alerts provided for " + selected_train +' trains.',
              reply_markup=ReplyKeyboardRemove())
    else:
        for i in range(len(alert)):
            alert_msg = ''
            for j in range(len(alert[i])):
                alert_msg = alert_msg + alert[i][j]+'\n\n'
            await update.message.reply_text(
                  alert_msg,
                  reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


async def ask_route_info(update: Update, context: ContextTypes.DEFAULT_TYPE, df_trains) -> int:
    
    """Prints MTA's information of selected route."""

    context.user_data["trains"] = df_trains
    routes = df_trains['route_id'].values

    routes = ["42nd Street Shuttle (S)" if r=='GS' else "Franklin Avenue Shuttle (S)" if r=='FS' else "Rockaway Park Shuttle (S)" if r=='H' else r for r in routes]

    await update.message.reply_text(
        "Which train are you interested in?",
        reply_markup=ReplyKeyboardMarkup(
            [[button] for button in routes], one_time_keyboard=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
        ),
    )
    
    return GIVE_ROUTE_INFO


async def give_route_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    df_trains = context.user_data["trains"]

    """Prints MTA's information of selected route."""
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
        df_trains[df_trains['route_id'].str.contains(selected_train)]['route_desc'].values[0],
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def get_user_bug_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    """Allow users to report bug with the bot"""
    await update.message.reply_text(
        "This command is intended for bug reporting only. Send your message below with as many details as possible.",
        reply_markup=ReplyKeyboardRemove(remove_keyboard=True),
    )

    return FORWARD_USER_BUG_REPORT


async def forward_user_bug_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    """Forward user bug reports to private channel"""
    await update.message.forward(chat_id='-1001708464995')

    await update.message.reply_text(
        "Thank you for reporting a bug. We are doing our best to fix them as soon as possible \U0001F64F",
        reply_markup=ReplyKeyboardRemove()
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

    return ConversationHandler.END


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays info on how to use the bot."""
    await update.message.reply_text(
        "Use /track to start tracking New York City's subway arrival times \U0001F687\U0001F5FD\n\nUse /stop to stop this bot \U0000270B",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays info on donate."""
    await update.message.reply_text(
        "If you find this bot useful, please chip in\! Your support will help us keep this bot accessible to everyone \U0001F680\n\n"+
        "Thank you\!\n\n"+
        "[PayPal donation link](https://www.paypal.com/donate/?business=53MCWVS8WMAM4&no_recurring=0&currency_code=USD)",
        parse_mode='MarkdownV2',
        disable_web_page_preview=True,
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def error_borough(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_keyboard_borough,input_field_placeholder) -> int:

    await update.message.reply_text(
        "Do not type the borough name. Select a borough from the list below.",
        reply_markup=ReplyKeyboardMarkup(
                reply_keyboard_borough, one_time_keyboard=True, input_field_placeholder=input_field_placeholder
            ),
    )
    return BOROUGH


async def error_station(update: Update, context: ContextTypes.DEFAULT_TYPE, dictStations) -> int:

    df_stations = dictStations[context.user_data["borough"]]

    await update.message.reply_text(
        "Do not type the station name. Select a station from the list.",
        reply_markup=ReplyKeyboardMarkup(
                [[button] for button in df_stations], one_time_keyboard=True, input_field_placeholder=df_stations[0]+", "+df_stations[1]+", "+df_stations[2]+", "+df_stations[3]+", "+df_stations[4]+"..."
            ),
    )
    return STATION


async def error_alert_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    df_trains = context.user_data["trains"]
    routes = df_trains['route_id'].values

    await update.message.reply_text(
        "Do not type the train name. Select a train from the list below.",
        reply_markup=ReplyKeyboardMarkup(
                [[button] for button in routes], one_time_keyboard=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
            ),
    )
    return GIVE_ALERT_INFO


async def error_route_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    df_trains = context.user_data["trains"]
    routes = df_trains['route_id'].values

    await update.message.reply_text(
        "Do not type the train name. Select a train from the list below.",
        reply_markup=ReplyKeyboardMarkup(
                [[button] for button in routes], one_time_keyboard=True, input_field_placeholder=routes[0]+", "+routes[1]+", "+routes[2]+", "+routes[3]+", "+routes[4]+"..."
            ),
    )
    return GIVE_ROUTE_INFO



async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([('start','Start the bot'),
                                           ('track','Track real time subway arrival times'),
                                           ('alerts','Retrieve real time service alerts'),
                                           ('route_info','Get information on train operations'),
                                           ('report_bug','Send a message to report a bug'),
                                           ('help','Get info on bot functionalities'),
                                           ('donate','Contribute to the bot expenses'),
                                           ('stop','Stop the bot')
                                          ])


def main() -> None:

    # Split the large txt files into smaller ones to fasten later processing
    cc.cache_stops()
    cc.cache_trips()
    cc.cache_stop_times()

    # Select how many incoming trains to show in output
    trainsToShow = 5

    # Load routes file
    df_trains = pd.read_csv('gtfs static files/routes.txt')
    
    # Load stops file
    df_stops = pd.read_csv('gtfs static files/stops.txt')

    # Load shapes file
    df_shapes = pd.read_csv('gtfs static files/shapes.txt')

    # Load alphabetically sorted stations file
    sortedStations = pd.read_csv('cache/stops_names/sorted_stations.txt',header=None).values.ravel()

    # Load stop_times and trips for current day
    if date.today().weekday() == 5: # Saturday
        df_stop_times = pd.read_csv('cache/stop_times/saturday.csv')
        df_trips = pd.read_csv('cache/trips/saturday.csv')
    elif date.today().weekday() == 6: # Sunday
        df_stop_times = pd.read_csv('cache/stop_times/sunday.csv')
        df_trips = pd.read_csv('cache/trips/sunday.csv')
    else: # Weekday
        df_stop_times = pd.read_csv('cache/stop_times/weekday.csv')
        df_trips = pd.read_csv('cache/trips/weekday.csv')

    dictStations = {
        "Manhattan": pd.read_csv('cache/stops_names/manhattan.txt',header=None).values.ravel(),
        "Brooklyn": pd.read_csv('cache/stops_names/brooklyn.txt',header=None).values.ravel(),
        "Queens": pd.read_csv('cache/stops_names/queens.txt',header=None).values.ravel(),
        "The Bronx": pd.read_csv('cache/stops_names/the_bronx.txt',header=None).values.ravel(),
        "Staten Island": pd.read_csv('cache/stops_names/staten_island.txt',header=None).values.ravel()
    }

    # Keyboard borough buttons
    reply_keyboard_borough = [["Manhattan","Brooklyn","Queens"],["The Bronx","Staten Island"]]

    # Convert list of lists into a flat list
    boroughs = functools.reduce(operator.iconcat, reply_keyboard_borough, [])

    # Make input field placeholder for borough choice
    input_field_placeholder = boroughs[0]+", "+boroughs[1]+", "+boroughs[2]+", "+boroughs[3]+", or "+boroughs[4]+"?"

    # partial functions needed to pass additional arguments to them in order to avoid reading csv each time
    partial_track = partial(track, reply_keyboard_borough=reply_keyboard_borough, input_field_placeholder=input_field_placeholder)
    partial_borough = partial(borough, dictStations=dictStations)
    partial_station = partial(station, df_trips=df_trips, df_stops=df_stops, df_stop_times=df_stop_times, df_shapes=df_shapes, trainsToShow=trainsToShow, reply_keyboard_borough=reply_keyboard_borough, input_field_placeholder=input_field_placeholder)
    partial_error_borough = partial(error_borough, reply_keyboard_borough=reply_keyboard_borough, input_field_placeholder=input_field_placeholder)
    partial_error_station = partial(error_station, dictStations=dictStations)
    partial_ask_alerts = partial(ask_alerts, df_trains=df_trains)
    partial_ask_route_info = partial(ask_route_info, df_trains=df_trains)

    """Run the bot."""

    # Add your personal Telegram bot's token.
    BOT_TOKEN = "5321607170:AAGGp0yky4-A45WTylsod8KvLxBGo0uW5gU"

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).concurrent_updates(True).build()

    # application.bot.set_my_commands(commands={
    #     "commands": [
    #         {
    #         "command": "start",
    #         "description": "Start using bot"
    #         },
    #         {
    #         "command": "help",
    #         "description": "Display help"
    #         },
    #         {
    #         "command": "menu",
    #         "description": "Display menu"
    #         }
    #         ]
    #     }
    # )


    # Add conversation handler with the states BOROUGH, STATION, ASK_ROUTE_INFO ,and GIVE_ROUTE_INFO
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("track", partial_track),
            CommandHandler("alerts", partial_ask_alerts),
            CommandHandler("route_info", partial_ask_route_info),
            CommandHandler("report_bug", get_user_bug_report)
                      ],
        states={ 
            INITIAL_STATE: [
                CommandHandler("start", start),
                CommandHandler("track", partial_track),
                CommandHandler("alerts", partial_ask_alerts),
                CommandHandler("route_info", partial_ask_route_info),
                CommandHandler("report_bug", get_user_bug_report),
                CommandHandler("help", help),
                CommandHandler("donate", donate),
                CommandHandler("stop", stop),
            ],
            BOROUGH: [
                MessageHandler(filters.Regex(re.compile(r'|'.join(x for x in [j for i in reply_keyboard_borough for j in i]))), partial_borough, block=False),
                CommandHandler("start", start),
                CommandHandler("track", partial_track),
                CommandHandler("alerts", partial_ask_alerts),
                CommandHandler("route_info", partial_ask_route_info),
                CommandHandler("report_bug", get_user_bug_report),
                CommandHandler("help", help),
                CommandHandler("donate", donate),
                CommandHandler("stop", stop),
                MessageHandler(~filters.COMMAND, partial_error_borough, block=False),
            ],
            STATION: [
                MessageHandler(filters.Regex(re.compile(r'|'.join(x for x in sortedStations))), partial_station, block=False),
                CommandHandler("start", start),
                CommandHandler("track", partial_track),
                CommandHandler("alerts", partial_ask_alerts),
                CommandHandler("route_info", partial_ask_route_info),
                CommandHandler("report_bug", get_user_bug_report),
                CommandHandler("help", help),
                CommandHandler("donate", donate),
                CommandHandler("stop", stop),
                MessageHandler(~filters.COMMAND, partial_error_station, block=False),
            ],
            GIVE_ALERT_INFO: [
                MessageHandler(filters.Regex(re.compile(r'|'.join(x for x in ["42nd Street Shuttle (S)" if r=='GS' else "Franklin Avenue Shuttle (S)" if r=='FS' else "Rockaway Park Shuttle (S)" if r=='H' else r for r in df_trains['route_id'].array]))), give_alert_info, block=False),
                CommandHandler("start", start),
                CommandHandler("track", partial_track),
                CommandHandler("alerts", partial_ask_alerts),
                CommandHandler("route_info", partial_ask_route_info),
                CommandHandler("report_bug", get_user_bug_report),
                CommandHandler("help", help),
                CommandHandler("donate", donate),
                CommandHandler("stop", stop),
                MessageHandler(~filters.COMMAND, error_alert_info, block=False),
            ],
            GIVE_ROUTE_INFO: [
                MessageHandler(filters.Regex(re.compile(r'|'.join(x for x in ["42nd Street Shuttle (S)" if r=='GS' else "Franklin Avenue Shuttle (S)" if r=='FS' else "Rockaway Park Shuttle (S)" if r=='H' else r for r in df_trains['route_id'].array]))), give_route_info, block=False),
                CommandHandler("start", start),
                CommandHandler("track", partial_track),
                CommandHandler("alerts", partial_ask_alerts),
                CommandHandler("route_info", partial_ask_route_info),
                CommandHandler("report_bug", get_user_bug_report),
                CommandHandler("help", help),
                CommandHandler("donate", donate),
                CommandHandler("stop", stop),
                MessageHandler(~filters.COMMAND, error_route_info, block=False),
            ],
            FORWARD_USER_BUG_REPORT: [
                MessageHandler(~filters.COMMAND, forward_user_bug_report, block=False),
                CommandHandler("start", start),
                CommandHandler("track", partial_track),
                CommandHandler("alerts", partial_ask_alerts),
                CommandHandler("route_info", partial_ask_route_info),
                CommandHandler("report_bug", get_user_bug_report),
                CommandHandler("help", help),
                CommandHandler("donate", donate),
                CommandHandler("stop", stop),
            ],
        },
        fallbacks=[CommandHandler("track", partial_track), CommandHandler("stop", stop)],
    )
    application.add_handler(conv_handler)

    # Add start handler 
    application.add_handler(CommandHandler("start", start))

    # Add route_info handler 
    application.add_handler(CommandHandler("alerts", partial_ask_alerts))

    # Add route_info handler 
    application.add_handler(CommandHandler("route_info", partial_ask_route_info))

    # Add get_user_bug_report handler 
    application.add_handler(CommandHandler("report_bug", get_user_bug_report))

    # Add help handler 
    application.add_handler(CommandHandler("help", help))

    # Add donation handler 
    application.add_handler(CommandHandler("donate", donate))

    # Add stop handler 
    application.add_handler(CommandHandler("stop", stop))



    # Heroku webhook implementation
    PRODUCTION = True
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





from threading import Thread
import gtfs_download as gtfs_download

def background_task(dir,filename):
    # run forever
    while True:
        gtfs_download.gtfs_download(dir,filename,True)
            




if __name__ == "__main__":
    
    dir = 'gtfs static files'
    filename = 'google_transit_supplemented.zip'

    if not os.path.isdir(dir):
        gtfs_download.gtfs_download(dir,filename,False)
    
    print("*** Starting daemon ***")
    daemon = Thread(target=background_task, daemon=True, args=(dir,filename), name='Background')
    daemon.start()  
    print("*** Daemon running ***")


    main()
    # while True:
    #     try:
    #         logger.info("Starting bot")
    #         main()
    #     except Exception:
    #         logger.exception("Something bad happened. Restarting bot.")



    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()