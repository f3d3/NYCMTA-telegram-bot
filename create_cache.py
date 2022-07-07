import os
import pandas as pd
import numpy as np


def cache_stops():
    #Caching system to split the stops.txt size
    if ((not os.path.isfile('cache/stops_names/sorted_stations.txt')) or (os.stat("cache/stops_names/sorted_stations.txt").st_size == 0)):
        os.makedirs('cache/stops_names', exist_ok=True)
        df_stations = pd.read_csv('gtfs static files/stops.txt')
        stations = pd.unique(df_stations[['stop_name']].sort_values(by="stop_name").values.ravel())
        np.savetxt('cache/stops_names/sorted_stations.txt', stations, delimiter=" ", fmt="%s") 


def cache_trips():
    #Caching system to split the trips.txt size
    if ((not os.path.isfile('cache/trips/weekday.csv')) or (os.stat("cache/trips/weekday.csv").st_size == 0)):
        os.makedirs('cache/trips', exist_ok=True)
        df_trips = pd.read_csv('trips.txt')
        df = df_trips.loc[(df_trips['trip_id'].str.contains("Weekday", case=False)),['trip_id','trip_headsign']]
        df.to_csv('cache/trips/weekday.csv')
    if ((not os.path.isfile('cache/trips/saturday.csv')) or (os.stat("cache/trips/saturday.csv").st_size == 0)):
        os.makedirs('cache/trips', exist_ok=True)
        df_trips = pd.read_csv('trips.txt')
        df = df_trips.loc[(df_trips['trip_id'].str.contains("Saturday", case=False)),['trip_id','trip_headsign']]
        df.to_csv('cache/trips/saturday.csv')
    if ((not os.path.isfile('cache/trips/sunday.csv')) or (os.stat("cache/trips/sunday.csv").st_size == 0)):
        os.makedirs('cache/trips', exist_ok=True)
        df_trips = pd.read_csv('trips.txt')
        df = df_trips.loc[(df_trips['trip_id'].str.contains("Sunday", case=False)),['trip_id','trip_headsign']]
        df.to_csv('cache/trips/sunday.csv')


def cache_stop_times():
    #Caching system to split the stop.time.txt size
    if ((not os.path.isfile('cache/stop_times/weekday.csv')) or (os.stat("cache/stop_times/weekday.csv").st_size == 0)):
        os.makedirs('cache/stop_times', exist_ok=True)
        df_stop_times = pd.read_csv('stop_times.txt')
        df = df_stop_times.loc[(df_stop_times['trip_id'].str.contains("Weekday", case=False)),['trip_id','stop_id','arrival_time']]
        df.to_csv('cache/stop_times/weekday.csv')
    if ((not os.path.isfile('cache/stop_times/saturday.csv')) or (os.stat("cache/stop_times/saturday.csv").st_size == 0)):
        os.makedirs('cache/stop_times', exist_ok=True)
        df_stop_times = pd.read_csv('stop_times.txt')
        df = df_stop_times.loc[(df_stop_times['trip_id'].str.contains("Saturday", case=False)),['trip_id','stop_id','arrival_time']]
        df.to_csv('cache/stop_times/saturday.csv')
    if ((not os.path.isfile('cache/stop_times/sunday.csv')) or (os.stat("cache/stop_times/sunday.csv").st_size == 0)):
        os.makedirs('cache/stop_times', exist_ok=True)
        df_stop_times = pd.read_csv('stop_times.txt')
        df = df_stop_times.loc[(df_stop_times['trip_id'].str.contains("Sunday", case=False)),['trip_id','stop_id','arrival_time']]
        df.to_csv('cache/stop_times/sunday.csv')
