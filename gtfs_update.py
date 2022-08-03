import os
import pandas as pd
import zipfile
import urllib.request
import shutil
from datetime import date, datetime
import pickle

from telegram.ext import ContextTypes

import create_cache

import utils


async def storeContext(context: ContextTypes.DEFAULT_TYPE, dir):
        # Store routes file in bot_data to avoid further access to local storage
        context.bot_data["df_routes"] = pd.read_csv(dir+'routes.txt')

        # Store stops file in bot_data to avoid further access to local storage
        context.bot_data["df_stops"] = pd.read_csv(dir+'stops.txt')

        # Store shapes file in bot_data to avoid further access to local storage
        context.bot_data["df_shapes"] = pd.read_csv(dir+'shapes.txt')

        # Store both stop_times and trips for current day in bot_data to avoid further access to local storage
        if date.today().weekday() == 5: # Saturday
            context.bot_data["df_stop_times"] = pd.read_csv(os.getcwd()+'/cache/stop_times/Saturday.csv')
            context.bot_data["df_trips"] = pd.read_csv(os.getcwd()+'/cache/trips/Saturday.csv')
        elif date.today().weekday() == 6: # Sunday
            context.bot_data["df_stop_times"] = pd.read_csv(os.getcwd()+'/cache/stop_times/Sunday.csv')
            context.bot_data["df_trips"] = pd.read_csv(os.getcwd()+'/cache/trips/Sunday.csv')
        else: # Weekday
            context.bot_data["df_stop_times"] = pd.read_csv(os.getcwd()+'/cache/stop_times/Weekday.csv')
            context.bot_data["df_trips"] = pd.read_csv(os.getcwd()+'/cache/trips/Weekday.csv')




# async def gtfs_update(context: ContextTypes.DEFAULT_TYPE) -> None:
async def gtfs_update(*args):

    if len(args)==2: # we are at the beginning of the program execution and not inside a job in the JobQueue
        dir = args[0]
        filename = args[1]
    elif len(args)==1: # we are inside a job in the JobQueue
        context = args[0]
        dir = context.job.data[0]
        filename = context.job.data[1]

    try:
        dbfile = open('my_persistence', 'rb')     
        db = pickle.load(dbfile)
        last_gtfs_update = db['last_gtfs_update']
        dbfile.close()
    except:
        db = utils.makeNestedDict()
        last_gtfs_update = datetime(2000, 1, 1, 0, 0, 0)

    if (len(args)==1 and context.job.name=='gtfs_daily_update') or (len(args)==2 and datetime.now()-last_gtfs_update).total_seconds()<86400 and (os.path.isdir(dir)) and (os.path.isdir("cache/stop_times")) and (os.path.isdir("cache/trips")):

        # await context.bot.send_message(context.job.chat_id, text=f"We are updating the database. Please try again in a couple of minutes.")

        print("*** GTFS file download started ***")

        # create temporary directory if it does not exist
        os.makedirs('temp', exist_ok=True)

        # download MTA's supplemented GTFS
        urllib.request.urlretrieve('http://web.mta.info/developers/files/google_transit_supplemented.zip', os.getcwd()+'/'+filename)
                
        print("*** GTFS file download completed ***")

        # unzip the downloaded file to the temporary directory
        with zipfile.ZipFile(filename, 'r') as zip_ref:
            zip_ref.extractall(dir)

        # delete the downloaded file and the temporary directory containing it
        shutil.rmtree('temp', ignore_errors=True)

        ## If file exists, delete it ##
        if os.path.isfile(filename):
            os.remove(filename)
        else:    ## Show an error ##
            print("Error: %s file not found" % filename)
        
        # Split the large downloaded txt files into smaller ones to fasten later processing
        await create_cache.create_cache(dir)

        # database
        db['last_gtfs_update'] = datetime.now() 

        # Its important to use binary mode
        dbfile = open('my_persistence', 'wb')
        
        # source, destination
        pickle.dump(db, dbfile)                     
        dbfile.close()

    if len(args)==1:
        await storeContext(context, dir)
    
