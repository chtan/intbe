from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import pymongo
import importlib
import csv
import json

# Connect to MongoDB
dbclient = pymongo.MongoClient(settings.MONGO_URI)
db = dbclient[settings.MONGO_DB_NAME]
users_collection = db["users"]

# Create your views here.



#def index(request, uid):
def index(request):
    uid = request.GET.get('uid', '')

    #dbclient = pymongo.MongoClient(settings.MONGO_URI)
    #db = dbclient[settings.MONGO_DB_NAME]
    #users_collection = db["users"]

    #docs = users_collection.find()
    #for doc in docs:
    #    print(doc)

    exists = users_collection.find_one({"username": uid}) is not None

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

    #dbclient = pymongo.MongoClient(settings.MONGO_URI)
    #db = dbclient[settings.MONGO_DB_NAME]

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

            print(link, "-==================")

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
        elif tid in ['6', '7']:
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


def download_data(request):
    tid = request.GET.get('tid', '')
    uid = request.GET.get('uid', '')
    applyString = request.GET.get('applyString', '')
    applyObject = json.loads(applyString)

    module_name = "task.tasks.task_" + tid
    task = importlib.import_module(module_name)

    args = [applyObject[0][0]] + [uid, tid] # True/False, list of tid's
    func = getattr(task, 'get_download_data')
    result = func(*args)

    # Create the HttpResponse object with CSV headers
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="results.csv"'

    writer = csv.DictWriter(response, fieldnames=result.keys())
    writer.writeheader()
    writer.writerow(result)

    """
    # Write CSV content
    writer = csv.writer(response)
    writer.writerow(['Name', 'Age'])        # Header
    writer.writerow(['Alice', 30])
    writer.writerow(['Bob', 25])
    """

    return response


