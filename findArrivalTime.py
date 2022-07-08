import pandas as pd
import numpy as np
import time
import math
import requests
import google.transit.gtfs_realtime_pb2 as gtfs_realtime_pb2

from datetime import date,datetime,timedelta


import findDestination as fd

from telegram import __version__ as TG_VER
from telegram import Update
from telegram.ext import (
    ContextTypes,
)

import asyncio

import make_async as ma

async def findArrivalTime_async(update, context, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow):
    # loop = asyncio.get_event_loop()
    # return await loop.run_in_executor(
    #     None, lambda: findArrivalTime(update, context, trips, stops, stop_times, trainsToShow))
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, findArrivalTime, update, context, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow)


from functools import *
import findDestination as fd


def findArrivalTime(update: Update, context: ContextTypes.DEFAULT_TYPE, df_trips, df_stops, df_stop_times, df_shapes, trainsToShow):
    
    MTA_APIKey = "***REMOVED***"
    
    subwayDict =	{
        "BDFM"   : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",  # B,D,F,M
        "ACEH"   : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",   # A,C,E,H
        "1234567": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",       # 1,2,3,4,5,6,7
        "G"      : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",     # G
        "NQRW"   : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",  # N,Q,R,W
        "JZ"     : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",    # J,Z
        "L"      : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",     # L
        "SIR"    : "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si"     # SIR (Staten Island Railway)
    }

    # Find the selected station's stop_id
    stop_ids = (df_stops.loc[df_stops['stop_name']==context.user_data["station"]]['stop_id']).tolist()
    
    # Since train names can't be extracted from stop_ids reliably, get the selected station's coordinates 
    df_stops_coord = df_stops.loc[df_stops['stop_name']==context.user_data["station"]][['stop_lat','stop_lon']]
    df_stops_coord = df_stops_coord.drop_duplicates(subset=['stop_lat','stop_lon'])

    # Merge stops and shapes dataframes on lat and lon coordinates
    df_stops_coord_shapes = pd.merge(df_stops_coord, df_shapes, left_on=['stop_lat','stop_lon'], right_on=['shape_pt_lat','shape_pt_lon'], how='left')
    
    # Find the serving train names
    servingTrains = list(set([st[0] for st in df_stops_coord_shapes['shape_id'].tolist()]))
    
    # Check only the serving train GTFS feeds to save times
    feedsToCheck = [value for key, value in subwayDict.items() if any(substring in key for substring in servingTrains)]

    # request parameters
    headers = {'x-api-key': MTA_APIKey}

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
                    trainname = ent.trip_update.trip.route_id
                    for j in range(0, len(ent.trip_update.stop_time_update)):
                        if (ent.trip_update.stop_time_update[j].stop_id in stop_ids) and (ent.trip_update.stop_time_update[j].arrival.time < df['Time'].max()) and (ent.trip_update.stop_time_update[j].arrival.time >= int(time.time())):
                            trip_id = ent.trip_update.trip.trip_id
                            station_codename = ent.trip_update.stop_time_update[j].stop_id
                            station_arrival_time = ent.trip_update.stop_time_update[j].arrival.time
                            df.loc[df[['Time']].idxmax()] = [trip_id,trainname,station_codename,station_arrival_time] 

    df_final = df[df['Trip_ID'].notna()]
    
    destinations = []; directions = []; waiting_times = []

    for i in range(0,min(trainsToShow,len(df_final.index)-1)):

        input_station = df_final.loc[i,'Station']

        # partial_findDestination = partial(fd.findDestination, input_station=df_final.loc[i,'Station'], df_trips=df_trips, df_stop_times=df_stop_times)
        # dest, dir = ma.make_async(partial_findDestination)

        # dest, dir = fd.findDestination_async(df_final.loc[i,'Station'], df_trips, df_stop_times)
        # dest, dir = fd.findDestination(input_station, df_trips, df_stop_times)



        # Select trips that match the current day of the week to speed up later processing
        if date.today().weekday() == 5: # Saturday
            df_trip_id = df_stop_times.loc[(df_stop_times['stop_id'] == input_station),['trip_id','arrival_time']]
        elif date.today().weekday() == 6: # Sunday
            df_trip_id = df_stop_times.loc[(df_stop_times['stop_id'] == input_station),['trip_id','arrival_time']]
        else:
            df_trip_id = df_stop_times.loc[(df_stop_times['stop_id'] == input_station),['trip_id','arrival_time']]

        # Fix hour values greater than 24 (MTA's bug)
        twenty_fours = df_trip_id['arrival_time'].str[-8:-6].astype(int) >= 24
        df_trip_id.loc[twenty_fours, 'arrival_time'] = df_trip_id['arrival_time'].str[:-8] + '00' + df_trip_id['arrival_time'].str[-6:]
        df_trip_id.loc[:,'arrival_time'] = pd.to_datetime(df_trip_id.loc[:,'arrival_time'], format='%H:%M:%S')
        df_trip_id.loc[twenty_fours, 'arrival_time'] = df_trip_id.loc[twenty_fours, 'arrival_time'] + timedelta(days=1) # add 1 day to routes with hour that was greater than 24

        # Save current time as a datetime object
        reftime = datetime.now().strftime('%H:%M:%S')
        reftime = datetime.strptime(reftime, "%H:%M:%S")

        # Find trip with closest scheduled departure to current time
        df_trip_id = df_trip_id.iloc[[df_trip_id.arrival_time.searchsorted(reftime)]]

        # Select train headsign and direction corresponding to selected trip
        temp = df_trips[df_trips['trip_id'].isin(df_trip_id['trip_id'])]
        finaldestination = temp.iloc[0]['trip_headsign']
        direction = temp.iloc[0]['trip_id']
        direction = direction[-4]

        dest = finaldestination
        dir = direction


        
        destinations.append(dest)
        directions.append(dir)

    for i in range(0,min(trainsToShow,len(df_final.index)-1)):
        #waiting_times.append(round((int(df_final['Time'].values[i])-int(time.time()))/60 * 2)/2) # round waiting minutes to nearest 0.5
        waiting_times.append(math.ceil((int(df_final['Time'].values[i])-int(time.time()))/60)) # round up waiting minutes
 

    trains = df_final['Train'].values

    waiting_times, trains, destinations, directions = zip(*sorted(zip(waiting_times, trains, destinations, directions), key=lambda x: x[0]))


    print("*** Upcoming Trains ***\n")
    for i in range(0,min(trainsToShow,len(df_final.index)-1)):
        print("Train " + trains[i] + " (" + destinations[i] + ") - " + str(waiting_times[i]) + " min\n")

    return trains, destinations, waiting_times, directions