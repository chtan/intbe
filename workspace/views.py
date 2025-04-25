from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import pymongo
import importlib
import json

# Create your views here.

#def index(request, uid):
def index(request):
    uid = request.GET.get('uid', '')

    dbclient = pymongo.MongoClient(settings.MONGO_URI)
    db = dbclient[settings.MONGO_DB_NAME]
    collection = db["users"]

    #docs = collection.find()
    #for doc in docs:
    #    print(doc)

    exists = collection.find_one({"name": uid}) is not None

    if exists:
        collection = db["usertasks"]
        query = {"uid": uid}
        results = collection.find(query)

        out = {
          "status": "ok",
          "tids": [item['tid'] for item in results],
        }
    else:
        out = {
          "status": "not ok",
        }

    return JsonResponse(out)


def task(request):
    uid = request.GET.get('uid', '')
    tid = request.GET.get('tid', '')

    dbclient = pymongo.MongoClient(settings.MONGO_URI)
    db = dbclient[settings.MONGO_DB_NAME]

    controls = {}
    collection = db["usertasks"]
    query = {"tid": tid}
    doc = collection.find_one(query)
    if doc:
        try:
            controls = doc["controls"] # Need to manage these better - whether structural or data
        except:
            controls = {}

    collection = db["task_links"]
    #query = {"uid": uid}
    query = {"uid": uid, "taskid": tid}
    results = collection.find(query)

    out = {
      "status": "not ok",
    }

    #for result in results:
    #    print("$$$$", result)

    if results:
        links = [result['tasklink'] for result in results]

        state = {}

        for link in links:
            collection = db["task_states"]
            query = {"tid": link}
            result = collection.find_one(query)
            state[link] = result["state"]


        if tid == '3':
            module_name = "task.tasks.task_" + result["ttid"]
            task = importlib.import_module(module_name)
            globalStatistics = task.computeGlobalStatistics()
            out = {
              "status": "ok",
              "state": state,
              "statistics": globalStatistics,
            }
        elif tid == '6':
            module_name = "task.tasks.task_" + result["ttid"]
            task = importlib.import_module(module_name)
            globalStatistics = task.computeGlobalStatistics()

            out = {
              "status": "ok",
              "state": state,
              "controls": controls,
              "statistics": globalStatistics,
            }
        else:
            out = {
              "status": "ok",
              "state": state,
              "controls": controls,
            }

    return JsonResponse(out)


def update_state(request):
    uid = request.GET.get('uid', '')
    tid = request.GET.get('tid', '')
    applyString = request.GET.get('applyString', '')
    applyObject = json.loads(applyString)

    #print(uid, tid, applyString, "--------------------")

    module_name = "task.tasks.task_" + tid
    task = importlib.import_module(module_name)

    args = applyObject[0][1] + [uid, tid] # True/False, list of tid's
    func = getattr(task, applyObject[0][0])
    result = func(*args)

    if result:
        out = {
            "status": "ok",
        }
    else:
        out = {
          "status": "not ok",
        }

    return JsonResponse(out)