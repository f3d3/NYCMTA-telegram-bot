import os
import pandas as pd
import numpy as np


# Caching system to split the stops.txt size
async def cache_stops(dir):
    os.makedirs('cache/stops_names', exist_ok=True)
    df_stations = pd.read_csv(dir+'stops.txt')
    stations = pd.unique(df_stations[['stop_name']].sort_values(by="stop_name").values.ravel())
    np.savetxt('cache/stops_names/sorted_stations.txt', stations, delimiter=" ", fmt="%s") 


# Caching system to split the trips.txt size
async def cache_trips(dir):
    os.makedirs('cache/trips', exist_ok=True)
    df_trips = pd.read_csv(dir+'trips.txt')
    days = ["Weekday","Saturday","Sunday"]
    for day in days:
        df = df_trips[(df_trips['trip_id'].str.contains(day, case=False)==True) | (df_trips['trip_id'].str.contains('|'.join(x for x in days), case=False)==False)][['trip_id','trip_headsign']]
        df.to_csv('cache/trips/'+day+'.csv', index=False)


# Caching system to split the stop_time.txt size
async def cache_stop_times(dir):
    os.makedirs('cache/stop_times', exist_ok=True)
    df_stop_times = pd.read_csv(dir+'stop_times.txt')
    days = ["Weekday","Saturday","Sunday"]
    for day in days:
        df = df_stop_times[(df_stop_times['trip_id'].str.contains(day, case=False)==True) | (df_stop_times['trip_id'].str.contains('|'.join(x for x in days), case=False)==False)][['trip_id','stop_id','arrival_time']]
        df.to_csv('cache/stop_times/'+day+'.csv', index=False)


# Split the large txt files into smaller ones to fasten later processing
async def createCache(dir):
    
    print("*** Cache creation started ***")
    await cache_stops(dir)
    await cache_trips(dir)
    await cache_stop_times(dir)
    print("*** Cache creation completed ***")