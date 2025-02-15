from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import pymongo
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

# Create your views here.

def index(request):
    tid = request.GET.get('tid', '')

    dbclient = pymongo.MongoClient(settings.MONGO_URI)
    db = dbclient[settings.MONGO_DB_NAME]
    collection = db["task_states"]

    query = {
        'tid': tid,
    }
    result = collection.find_one(query)

    out = {
      "status": "not ok",
    }

    if result:
        out = {
            "status": "ok",
            "state": result["state"],
            "tasktypeid": result["ttid"],
        }

    return JsonResponse(out)


def send_message_to_clients(sender, receiver, message, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "user_" + receiver,
        {
            "type": "chat_message",
            "message": message,
            "sender": sender,
            "data": data,
        }
    )


def update_state(request):
    tid = request.GET.get('tid', '')
    n = int(request.GET.get('n', ''))

    myclient = pymongo.MongoClient(settings.MONGO_URI)
    mydb = myclient[settings.MONGO_DB_NAME]
    collection = mydb["task_states"]

    # Define the filter
    filter = {'tid': tid}
    state = {
        'n': n,
    }

    # Define the update
    update = {'$set': {
        'state': state
    }}

    # Update one document
    result = collection.update_one(filter, update)

    out = {
      "status": "not ok",
    }

    #print("!!!!", tid, n, result.matched_count)
    send_message_to_clients(tid, "chtan", "update state", state)

    #if result.matched_count > 0:
    if result.acknowledged:
        out = {
          "status": "ok",
          "state": state,
        }

    return JsonResponse(out, safe=False)
