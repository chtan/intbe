from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from rest_framework.authentication import get_authorization_header#,TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from jwt import decode as jwt_decode, InvalidTokenError
from django.conf import settings
from django.http import HttpResponse
import json
import csv
from mongoengine.connection import get_db
import importlib


class MyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {"message": "Hello, world!"}
        return Response(data)  # Automatically returns JSON


class EchoView(APIView):
    permission_classes = [IsAuthenticated]  # Requires valid JWT
    #permission_classes = []

    def get(self, request):
        return Response({"message": "Hello from EchoView!"})

class IsAnonymousTokenUser(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "is_anonymous_token", False)

class AnonDataView(APIView):
    permission_classes = [IsAnonymousTokenUser]

    def get(self, request):
        tasktoken = request.headers.get('X-Anonymous-Token')

        collection = get_db()["task_links"]
        doc = collection.find_one({"tasklink": tasktoken})

        return Response({
            "message": "Welcome, anonymous user!",
            "taskid": doc["taskid"]
        })

class AnonDataHelloView(APIView):
    permission_classes = [IsAnonymousTokenUser]

    def get(self, request):
        return Response({"message": "Hello!"})


class AnonDataGetStateView(APIView):
    permission_classes = [IsAnonymousTokenUser]

    def get(self, request):
        tasktoken = request.headers.get('X-Anonymous-Token')
        applyString = request.GET.get('applyString', '')
        applyObject = json.loads(applyString)

        collection = get_db()["task_states"]
        query = {
            'tid': tasktoken,
        }
        result = collection.find_one(query)

        if result:
            module_name = "task.tasks.task_" + result["ttid"]
            task = importlib.import_module(module_name)

            cid = result["cid"]

        return Response({
            "message": "Hello!",
            "state": result["state"],
        })


class AnonDataSetStateView(APIView):
    permission_classes = [IsAnonymousTokenUser]

    def get(self, request):
        tasktoken = request.headers.get('X-Anonymous-Token')
        applyString = request.GET.get('applyString', '')
        applyObject = json.loads(applyString)

        collection = get_db()["task_states"]
        query = {
            'tid': tasktoken,
        }
        result = collection.find_one(query)

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
                {'tid': tasktoken},
                update
            )

        return Response({
            "message": "Hello!",
            "state": result["state"],
        })


# To port old code under task/ endpoint over to the current taskpad/,
# may need to code over state, controls, structure.
# May be good to wrap this into a dictionary for uniformity here.

class AnonDataApplyTaskMethodView(APIView):
    permission_classes = [IsAnonymousTokenUser]

    def get(self, request):

        tasktoken = request.headers.get('X-Anonymous-Token')
        applyString = request.GET.get('applyString', '')
        applyObject = json.loads(applyString)

        collection = get_db()["task_states"]
        query = {
            'tid': tasktoken,
        }
        result = collection.find_one(query)

        if result:
            try:
                module_name = "task.tasks.task_" + result["ttid"]
                task = importlib.import_module(module_name)

                args = [result] + applyObject[0][1]
                func = getattr(task, applyObject[0][0])
                composite = func(*args)
            except Exception as e:
                #print(str(e), "--------------------")
                composite = {}

        return Response({
            "message": "Hello!",
            "composite": composite,
        })


class WorkspaceDownloadDataView(APIView):
    #authentication_classes = [TokenAuthentication]  # without this, setting.py is consulted
    permission_classes = [IsAuthenticated]  # optional

    def get(self, request, format=None):
        uid = request.GET.get('uid', '')
        tid = request.GET.get('tid', '')
        applyString = request.GET.get('applyString', '')
        applyObject = json.loads(applyString)

        module_name = f"task.tasks.task_{tid}"
        task = importlib.import_module(module_name)

        if applyObject[0][0] == 'statistics':
            func = getattr(task, "getGlobalStatistics")
            args = [uid, tid]
            data = func(*args)
        else:
            data = []
            # Example data (replace with your actual logic/queryset)
            #data = [
            #    ['Name', 'Age'],
            #    ['Alice', 30],
            #    ['Bob', 25]
            #]

        # Create a CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="data.csv"'

        writer = csv.writer(response)
        for row in data:
            writer.writerow(row)

        return response


class WorkspaceTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uid = request.GET.get('uid', '')
        tid = request.GET.get('tid', '')

        controls = {}
        collection = get_db()["task_control_states"]
        query = {"taskid": tid}
        doc = collection.find_one(query)
        if doc:
            controls = doc["state"]
        else:
            controls = {}

        collection = get_db()["task_links"]
        query = {"uid": uid, "taskid": tid}
        results = collection.find(query)

        if results:
            state = {}

            links = [result['tasklink'] for result in results]

            for link in links:
                collection = get_db()["task_states"]
                query = {"tid": link}
                result = collection.find_one(query)
                state[link] = result["state"]

            module_name = "task.tasks.task_" + result["ttid"]
            task = importlib.import_module(module_name)
            globalStatistics = task.getGlobalStatistics(uid, tid, format="json")

            out = {
              "status": "ok",
              "state": state,
              "controls": controls,
              "statistics": globalStatistics,
            }

            return Response(out)
        else:
            return Response({ "status": "not ok" })


class WorkspaceApplyTaskMethodView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uid = request.GET.get('uid', '')
        tid = request.GET.get('tid', '')
        applyString = request.GET.get('applyString', '')
        applyObject = json.loads(applyString)
        #print(uid,tid,applyObject)

        module_name = "task.tasks.task_" + tid
        task = importlib.import_module(module_name)

        args = [uid] + applyObject[0][1]
        func = getattr(task, applyObject[0][0])
        composite = func(*args)

        return Response({
            "message": "ok",
            "composite": composite,
        })


class WorkspaceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uid = request.GET.get('uid', '')

        collection = get_db()["users"]
        query = {"username": uid}
        exists = collection.find_one(query) is not None

        if exists:
            collection = get_db()["usertasks"]
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

        return Response(out)
