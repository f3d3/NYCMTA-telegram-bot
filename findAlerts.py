import os
import time
import requests

import google.transit.gtfs_realtime_pb2 as gtfs_realtime_pb2

from telegram import __version__ as TG_VER
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ContextTypes,
)

import utils


# @utils.send_action(ChatAction.TYPING)
# async def findAlerts_async(update, context, userTrain):
#     loop = asyncio.get_event_loop()
#     return await loop.run_in_executor(None, findAlerts, update, context, userTrain)


# import asyncio
@utils.send_action(ChatAction.TYPING)
async def findAlerts(update: Update, context: ContextTypes.DEFAULT_TYPE, userTrain):    
    
    MTA_API_key = os.environ.get("MTA_API_key")
    
    alertsURL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts"

    # Request parameters
    headers = {'x-api-key': MTA_API_key}

    # Get the train data from the MTA
    try:
        response = requests.get(alertsURL, headers=headers, timeout=30)
    except:
        return 'Failed to retreive train data from MTA'

    # Parse the protocol buffer that is returned
    feed = gtfs_realtime_pb2.FeedMessage()
        
    try:
        feed.ParseFromString(response.content)
    except:
        return 'Failed while parsing train data'
            
    alert = []
        
    for ent in feed.entity:
        if ent.HasField('alert') and hasattr(ent, 'is_deleted'):
            if not ent.is_deleted:
                if hasattr(ent.alert, 'informed_entity') and hasattr(ent.alert, 'active_period'):
                    for i in range(0, len(ent.alert.informed_entity)):
                        for j in range(0, len(ent.alert.active_period)):
                            if ent.alert.informed_entity[i].route_id==userTrain and ent.alert.active_period[j].start < int(time.time()):
                                    if (not ent.alert.active_period[j].end) or (ent.alert.active_period[j].end and (ent.alert.active_period[j].end >= int(time.time()))):
                                        if hasattr(ent.alert,'description_text'):
                                            if len(ent.alert.description_text.translation):
                                                if hasattr(ent.alert.description_text.translation[0],'text'):
                                                    alert.append([ent.alert.header_text.translation[0].text, ent.alert.description_text.translation[0].text])
                                        else:
                                            alert.append([ent.alert.header_text.translation[0].text])

        

    return alert