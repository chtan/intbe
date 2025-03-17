from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import pymongo

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

        out = {
          "status": "ok",
          #"links": links,
          "state": state,
        }

    #print("!!!!!!", out)

    return JsonResponse(out)
