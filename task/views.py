from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import pymongo
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import importlib

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
        if result["ttid"] == '1':
            out = {
                "status": "ok",
                "state": result["state"],
                "tasktypeid": result["ttid"],
            }

        elif result["ttid"] == '3':
            module_name = "task.tasks.task_" + result["ttid"]
            task = importlib.import_module(module_name)

            statistics = task.getStatistics(result["state"])

            out = {
                "status": "ok",
                "state": result["state"],
                "structure": task.structure,
                "tasktypeid": result["ttid"],
                "statistics": statistics,
            }

        else:

            out = {
              "status": "ok",
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


def update_state2(request):
    tid = request.GET.get('tid', '')
    applyString = request.GET.get('applyString', '')
    applyObject = json.loads(applyString)
    print(applyObject)

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
        module_name = "task.tasks.task_" + result["ttid"]
        task = importlib.import_module(module_name)

        cid = result["cid"]

        args = [result["state"]] + applyObject[0][1]
        func = getattr(task, applyObject[0][0])
        state = func(*args)

        # Define the update
        update = {'$set': {
            'state': state
        }}

        # Update one document
        result2 = collection.update_one(
            {'tid': tid},
            update
        )

        statistics = task.getStatistics(state)

        if result2:
            out = {
                "status": "ok",
                "state": state,
                "structure": task.structure,
                "tasktypeid": result["ttid"],
                "statistics": statistics,
            }

            # Compute and send coordinator statistics
            # For future tuning, only some updates may cause the statistics to update.
            # e.g. here, navigation does not affect the statistics, and hence may be ignored.
            globalStatistics = task.computeGlobalStatistics()
            send_message_to_clients(tid, cid, "update statistics", globalStatistics)

    return JsonResponse(out)


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

#
# Task 3
# A sequence of MCQs.
# Configuration space to control flow.
# No communication.
# Statistics for performance
#
# Interaction:
# 2 sides - coordinator, learner
# angular -> django (2 streams) and possible intercom
# 
# Task definition - define in python and config files
# 
# Game - state space
# Configuration
# Statistics - player view, learner view
# Link to KB
# Players
# Agents
# 
