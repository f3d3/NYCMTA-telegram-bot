from datetime import date,datetime,timedelta
import pandas as pd
import asyncio


async def get_trip_destination_async(input_station, df_trips, df_stop_times):
    # loop = asyncio.get_event_loop()
    # return await loop.run_in_executor(
    #     None, lambda: get_trip_destination(input_station, df_trips, df_stop_times))

    loop = asyncio.get_event_loop()
    finaldestination, direction = await loop.run_in_executor(None, get_trip_destination, input_station, df_trips, df_stop_times)
    return finaldestination, direction

def get_trip_destination(input_station, df_trips, df_stop_times):

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

    return finaldestination, direction


