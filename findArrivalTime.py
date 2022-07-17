import pandas as pd
import numpy as np
import time
import math
import requests
import asyncio
from datetime import date,datetime,timedelta
from functools import *

import google.transit.gtfs_realtime_pb2 as gtfs_realtime_pb2

import findDestination as fd
import make_async as ma

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
async def findArrivalTime_async(update, context, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow, userStation):
    # loop = asyncio.get_event_loop()
    # return await loop.run_in_executor(
    #     None, lambda: findArrivalTime(update, context, trips, stops, stop_times, trainsToShow))
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, findArrivalTime, update, context, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow, userStation)


def findArrivalTime(update: Update, context: ContextTypes.DEFAULT_TYPE, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow, userStation):
    
    MTA_API_key = "ymFcaLS9JBabZieClasw2XzdXnedgfE8QxBTUED0"
    
    subwayDict =	{
        "1-2-3-4-5-6-7-GS": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",       # 1,2,3,4,5,6,7
        "A-C-E-H-FS"      : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",   # A,C,E
        "B-D-F-M"         : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",  # B,D,F,M
        "G"               : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",     # G
        "N-Q-R-W"         : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",  # N,Q,R,W
        "J-Z"             : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",    # J,Z
        "L"               : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",     # L
        "SI"             : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si"     # SIR (Staten Island Railway)
    }

    # Find the selected station's stop_id
    stop_ids = (df_stops.loc[df_stops['stop_name']==userStation]['stop_id']).tolist()

    # Since train names can't be extracted from stop_ids reliably, get the selected station's coordinates 
    df_stops_coord = df_stops.loc[df_stops['stop_name']==userStation][['stop_lat','stop_lon']]
    df_stops_coord = df_stops_coord.drop_duplicates(subset=['stop_lat','stop_lon'])

    # Convert string coordinates to float coordinates
    df_stops_coord.stop_lat = df_stops_coord.stop_lat.astype(float); df_stops_coord.stop_lon = df_stops_coord.stop_lon.astype(float)
    df_shapes.shape_pt_lat = df_shapes.shape_pt_lat.astype(float); df_shapes.shape_pt_lon = df_shapes.shape_pt_lon.astype(float)
    
    # Since sometimes station coordinates differ between stops.txt and shapes.txt, don't do an inner join between the two but find closest station by Euclidean distance
    distances = [(((df_shapes['shape_pt_lat'].sub(df_stops_coord.iloc[i,0], axis=0))**2+(df_shapes['shape_pt_lon'].sub(df_stops_coord.iloc[i,1], axis=0))**2)**0.5).to_numpy() for i in range(len(df_stops_coord.index))]

    # Iterate on each station
    servingTrains = set()
    min_distance_shape_id = set()
    for i in range(len(df_stops_coord.index)):
        # Find indexes of stations with minimum distances (one index per each train serving the minimum distance station)
        min_distance_shape_id.update(df_shapes.iloc[np.where(distances[i]==distances[i].min())]['shape_id'])
        # Extract first char of the obtained shape_id's
        servingTrains.update([m.partition(".")[0] for m in min_distance_shape_id])

    # Convert set to list
    min_distance_shape_id = list(min_distance_shape_id)
    servingTrains = list(servingTrains)
    
    # Check only the serving trains GTFS feeds to save times
    feedsToCheck = [value for key, value in subwayDict.items() if any(st in key.split("-") for st in servingTrains)]

    # Request parameters
    headers = {'x-api-key': MTA_API_key}

    df = pd.DataFrame(columns=['Trip_ID', 'Train', 'Station', 'Time'], index=range(trainsToShow))
    df['Time'] = np.inf

    for i in feedsToCheck:
        # Get the train data from the MTA
        try:
            response = requests.get(i, headers=headers, timeout=30)
        except:
            return 'fail'

        # Parse the protocol buffer that is returned
        feed = gtfs_realtime_pb2.FeedMessage()
        
        try:
            feed.ParseFromString(response.content)
        except:
            return 'fail'
            
        # test = protobuf_to_dict(feed)
        
        for ent in feed.entity:
            if ent.HasField('trip_update'):
                if ent.trip_update.trip.HasField('route_id'):
                    train_name = ent.trip_update.trip.route_id
                    for j in range(0, len(ent.trip_update.stop_time_update)):
                        if (ent.trip_update.stop_time_update[j].stop_id in stop_ids):
                            # If the considered station is not the first stop, check the arrival time
                            if (ent.trip_update.stop_time_update[j].arrival.time < df['Time'].max()) and (ent.trip_update.stop_time_update[j].arrival.time >= int(time.time())):
                                trip_id = ent.trip_update.trip.trip_id
                                station_id = ent.trip_update.stop_time_update[j].stop_id
                                trip_time = ent.trip_update.stop_time_update[j].arrival.time
                                df.loc[df[['Time']].idxmax()] = [trip_id,train_name,station_id,trip_time] 
                            # otherwhise, check the departure time
                            elif (ent.trip_update.stop_time_update[j].departure.time < df['Time'].max()) and (ent.trip_update.stop_time_update[j].departure.time >= int(time.time())):
                                trip_id = ent.trip_update.trip.trip_id
                                station_id = ent.trip_update.stop_time_update[j].stop_id
                                trip_time = ent.trip_update.stop_time_update[j].departure.time
                                df.loc[df[['Time']].idxmax()] = [trip_id,train_name,station_id,trip_time] 

    # If there are less trains than trainsToShow, remove all unused rows
    df = df[df['Trip_ID'].notna()]

    # Remove trains going to the H19 stop (it is a "ghost" station, the real Broad Channel stop_id is H04)
    # ---> Is it correct to remove them though?
    df = df[df['Station'].str.contains('H19', regex=False) == False]    
    df.reset_index(drop=True, inplace=True)

    destinations = []; directions = []; waiting_times = []

    for i in range(min(trainsToShow,len(df.index))):

        # Filter for trips containing the considered trip_id
        input_trip_id = df.loc[i,'Trip_ID']
        df_trips_filtered = df_trips[df_trips['trip_id'].str.contains(input_trip_id, regex=False)]

        # Check if there is any info on the considered trip
        if len(df_trips_filtered.index)>0: # if yes, retrieve informations on destination and direction from the filtered dataframe
            dest = df_trips_filtered['trip_headsign'].values[0]
            t_id = (df_trips_filtered['trip_id'].values[0]).split("..")[-1]
            dir = t_id[0]
        else: # otherwise, find trip that has closest scheduled departure with respect to the considered trip and get its destination and direction
            input_station_id = df.loc[i,'Station']

            # if 'H19' in input_station_id:
            #     input_station_id.replace('H19','H04')


            # partial_findDestination = partial(fd.findDestination, input_station_id=df.loc[i,'Station'], df_trips=df_trips, df_stop_times=df_stop_times)
            # dest, dir = ma.make_async(partial_findDestination)

            # dest, dir = fd.findDestination_async(df.loc[i,'Station'], df_trips, df_stop_times)
            # dest, dir = fd.findDestination(input_station_id, df_trips, df_stop_times)

            df_trip_id = df_stop_times.loc[(df_stop_times['stop_id'] == input_station_id),['trip_id','arrival_time']]

            # Fix hour values greater than 24 (to correct MTA's bugs)
            twenty_fours = df_trip_id['arrival_time'].str[-8:-6].astype(int) >= 24
            df_trip_id.loc[twenty_fours, 'arrival_time'] = df_trip_id['arrival_time'].str[:-8] + '00' + df_trip_id['arrival_time'].str[-6:]
            df_trip_id.loc[:,'arrival_time'] = pd.to_datetime(df_trip_id.loc[:,'arrival_time'], format='%H:%M:%S')
            df_trip_id.loc[twenty_fours, 'arrival_time'] = df_trip_id.loc[twenty_fours, 'arrival_time'] + timedelta(days=1) # add 1 day to routes with hour that was greater than 24

            # Save current time as a datetime object
            reftime = datetime.utcnow().strftime('%H:%M:%S')
            reftime = datetime.strptime(reftime, "%H:%M:%S")

            df_trip_id = df_trip_id.sort_values(by=['arrival_time'])
            

            # Find trip with closest scheduled departure to current time
            # df_trip_id = df_trip_id.loc[[(abs(df_trip_id.iloc[:, 1]-reftime)).idxmin()]]
            df_trip_id = df_trip_id.iloc[[df_trip_id.arrival_time.searchsorted(reftime)]]

            # Select train headsign and direction corresponding to selected trip
            temp = df_trips[df_trips['trip_id'].isin(df_trip_id['trip_id'])]
            finaldestination = temp.iloc[0]['trip_headsign']
            direction = temp.iloc[0]['trip_id']
            direction = direction.split(".")[-1] 
            direction = direction[0] 

            dest = finaldestination
            dir = direction

        destinations.append(dest)
        directions.append(dir)

    for i in range(min(trainsToShow,len(df.index))):
        #waiting_times.append(round((int(df['Time'].values[i])-int(time.time()))/60 * 2)/2) # round waiting minutes to nearest 0.5
        waiting_times.append(math.ceil((int(df['Time'].values[i])-int(time.time()))/60)) # round up waiting minutes
 
    # Get train names and substitute shuttle train names with 'S'
    trains = df['Train'].values
    trains = ['S' if t=='GS' or t=='FS' or t=='H' else t for t in trains]

    waiting_times, trains, destinations, directions = zip(*sorted(zip(waiting_times, trains, destinations, directions), key=lambda x: x[0])) # sort the variables by waiting_times


    print("\n*** Upcoming Trains ***\n")
    for i in range(min(trainsToShow,len(df.index))):
        print("Train " + trains[i] + " (" + destinations[i] + ") - " + str(waiting_times[i]) + " min")

    return trains, destinations, waiting_times, directions