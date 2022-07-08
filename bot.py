#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import pandas as pd
import re

from functools import *

# import time
# from concurrent.futures import ThreadPoolExecutor
# _executor = ThreadPoolExecutor(10)

# from protobuf_to_dict import protobuf_to_dict

import create_cache as cc
import findArrivalTime as fat

from datetime import date, datetime

# import asyncio

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
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
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
BOROUGH, STATION, LOCATION = range(3)


#async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_keyboard_borough) -> int:

    user = update.message.from_user
    """Starts the conversation and asks the user about their borough."""

    hour = datetime.now().hour
    greeting = "Good morning" if 5<=hour<12 else "Good afternoon" if hour<18 else "Good evening"
    await update.message.reply_text(
        greeting + f", {user.first_name} \U0001F44B\n\n"+
        "Select your borough from the list, or send /stop to stop talking to me.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard_borough, one_time_keyboard=True, input_field_placeholder="Manhattan, Brooklyn, Queens, The Bronx, or Staten Island?"
        ),
    )

    return BOROUGH


# Ask user for station
async def borough(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the borough and asks for the station."""
    context.user_data["borough"] = update.message.text

    match update.message.text:
        case 'Manhattan':
            df_stations = pd.read_csv('cache/stops_names/manhattan.txt',header=None).values.ravel()
        case 'Brooklyn':
            df_stations = pd.read_csv('cache/stops_names/brooklyn.txt',header=None).values.ravel()
        case 'Queens':
            df_stations = pd.read_csv('cache/stops_names/queens.txt',header=None).values.ravel()
        case 'The Bronx':
            df_stations = pd.read_csv('cache/stops_names/the_bronx.txt',header=None).values.ravel()
        case 'Staten Island':
            df_stations = pd.read_csv('cache/stops_names/staten_island.txt',header=None).values.ravel()

    context.user_data["stations"] = df_stations

    user = update.message.from_user
    logger.info("Borough of %s: %s", user.first_name, update.message.text)
    await update.message.reply_text(
        "Select your station",
        reply_markup=ReplyKeyboardMarkup(
            [[button] for button in df_stations], one_time_keyboard=True, input_field_placeholder=str(df_stations[0])+", "+str(df_stations[1])+", "+str(df_stations[2])+", "+str(df_stations[3])+", "+str(df_stations[4])+"..."
        ),
    )

    return STATION


# partial_findArrivalTime = partial(fat.findArrivalTime, update=Update, context=ContextTypes.bot_data)



# Process the borough and staion and find arrival times
async def station(update: Update, context: ContextTypes.DEFAULT_TYPE, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow) -> int:

    await update.message.reply_text(
        "Processing... \U0001F52E",
    )

    """Stores the selected station and find arrival time."""
    context.user_data["station"] = update.message.text
    user = update.message.from_user
    logger.info("Station of %s: %s", user.first_name, update.message.text)


    # tasks = [asyncio.to_thread(partial_findArrivalTime)]
    # trains, destinations, waiting_times, directions = await asyncio.gather(*tasks)
    
    # tasks = [asyncio.to_thread(partial_findArrivalTime)]
    # res = await asyncio.gather(*tasks)

    # trains, destinations, waiting_times, directions = await loop.run_in_executor(_executor, partial_findArrivalTime)

    # trains, destinations, waiting_times, directions = await ma.make_async(partial_findArrivalTime)

    trains, destinations, waiting_times, directions = await fat.findArrivalTime_async(update, context, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow)

    # trains, destinations, waiting_times, directions = fat.findArrivalTime_async(update, context)

    emoji_indication = [('\U0001F53C' if directions[i] == 'N' else ('\U0001F53D' if directions[i] == 'S' else directions[i])) for i in range(0,len(directions))]


    outStr = ""
    for i in range(0,len(trains)):
        outStr = outStr + emoji_indication[i] + " Train " + trains[i] + " (" + destinations[i] + ") - " + str(waiting_times[i]) + " min\n"


    await update.message.reply_text(
        outStr,
        reply_markup=ReplyKeyboardRemove(),
    )

    reply_keyboard = [
                        ["Manhattan","Brooklyn","Queens"],
                        ["The Bronx","Staten Island"]
                        ]

    await update.message.reply_text(
        "Select another borough and station, or send /stop if you don't want to \U0000270B",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder="Manhattan, Brooklyn, Queens, The Bronx, or Staten Island?"
        ),
    )

    return BOROUGH


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stops and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s stopped the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! \U0001F44B I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    await update.message.reply_text(
        "Use /start to start this bot and find New York City's realtime subway arrival times \U0001F687\U0001F5FD\n\nUse /stop to stop this bot \U0000270B"
    )


async def error_borough(update: Update, context: ContextTypes.DEFAULT_TYPE, reply_keyboard_borough) -> int:
    await update.message.reply_text(
        "Do not type the borough name. Select a borough from the list below.",
        reply_markup=ReplyKeyboardMarkup(
                reply_keyboard_borough, one_time_keyboard=True, input_field_placeholder="Manhattan, Brooklyn, Queens, The Bronx, or Staten Island?"
            ),
    )
    return BOROUGH


async def error_station(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Do not type the station name. Select a station from the list below.",
        reply_markup=ReplyKeyboardMarkup(
                [[button] for button in context.user_data["stations"]], one_time_keyboard=True, input_field_placeholder=str(context.user_data["stations"][0])+", "+str(context.user_data["stations"][1])+", "+str(context.user_data["stations"][2])+", "+str(context.user_data["stations"][3])+", "+str(context.user_data["stations"][4])+"..."
            ),
    )
    return STATION


def main() -> None:

    # Split the large txt files into smaller ones to fasten later processing
    cc.cache_stops()
    cc.cache_trips()
    cc.cache_stop_times()

    # Select how many incoming trains to show in output
    trainsToShow = 5
    
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

    # Keyboard borough buttons
    reply_keyboard_borough = [["Manhattan","Brooklyn","Queens"],["The Bronx","Staten Island"]]
    
    # partial start() function -> needed to pass additional arguments to it to avoid reading csv at each /start command
    partial_start = partial(start, reply_keyboard_borough=reply_keyboard_borough)

    # partial_station start() function -> needed to pass additional arguments to it to avoid reading csv at each /start command
    partial_station = partial(station, df_trips=df_trips, df_stops=df_stops, df_stop_times=df_stop_times, df_shapes=df_shapes, trainsToShow=trainsToShow)

    # partial error_borough() function -> needed to pass additional arguments to it
    partial_error_borough = partial(error_borough, reply_keyboard_borough=reply_keyboard_borough)


    """Run the bot."""

    # Add your personal Telegram bot's token.
    BOT_TOKEN = "***REMOVED***"

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    # Add conversation handler with the states BOROUGH, STATION, and LOCATION
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", partial_start)],
        states={ 
            BOROUGH: [MessageHandler(filters.Regex(re.compile('|'.join(re.escape(x) for x in [j for i in reply_keyboard_borough for j in i]))), borough, block=False),
                      CommandHandler("start", partial_start),
                      CommandHandler("help", help),
                      CommandHandler("stop", stop),
                      MessageHandler(filters.ALL, partial_error_borough, block=False),
            ],
            STATION: [MessageHandler(filters.Regex(re.compile('|'.join(re.escape(x) for x in sortedStations))), partial_station, block=False),
                      CommandHandler("start", partial_start),
                      CommandHandler("help", help),
                      CommandHandler("stop", stop),
                      MessageHandler(filters.ALL, error_station, block=False),
            ],
        },
        fallbacks=[CommandHandler("start", partial_start), CommandHandler("stop", stop)],
    )
    application.add_handler(conv_handler)

    # Add help handler 
    application.add_handler(CommandHandler("help", help))

    # Add stop handler 
    application.add_handler(CommandHandler("stop", stop))

    # Run the bot until Ctrl-C is pressed
    application.run_polling(timeout=10)


if __name__ == "__main__":
    main()
    
    # while True:
    #     try:
    #         logger.info("Starting bot")
    #         main()
    #     except Exception:
    #         logger.exception("Something bad happened. Restarting")


    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()