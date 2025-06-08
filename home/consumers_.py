import json
from channels.generic.websocket import AsyncWebsocketConsumer
from users.authentication import MongoJWTAuthentication, AnonymousTokenAuthentication
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import AuthenticationFailed
from mongoengine.connection import get_db

"""
For logged-in user:
const ws = new WebSocket("ws://localhost:8000/ws/chat/?token=JWT_TOKEN");

For anonymous users:
const ws = new WebSocket("ws://localhost:8000/ws/chat/?token=aaa1&username=aaa");
"""

"""
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({"message": "Connected"}))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message", "")

        # Echo message back to client
        await self.send(text_data=json.dumps({"message": message}))
"""

# Ref:
# https://chatgpt.com/c/679daa1f-7ea0-8001-a7f9-2e4e50da1580

connected_users = {}  # Store active WebSocket connections

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope["query_string"].decode()
        params = dict(x.split("=") for x in query_string.split("&") if "=" in x)
        token = params.get("token") # this is access token
        taskid = params.get("taskid")

        # Currently, I have 3 websockets on angular side:
        # 1- old one
        # 2- new one for logged-in user
        # 3- new one for anonymous user
        # For 2, I send the access_token as token.
        # For 3, I don't. So token will be None.
        #
        # Notes and TODO:
        # - For 2, I can further send the refresh token.
        # - Read more about this Python module to be better at web socket management on server side, e.g. rooms.
        # - Possible to have more than one endpoint (correspondingly consumer)
        # - Just this consumer, I can user logic to authenticate as follows:
        #   - authenticate those with (access) tokens, add the taskid as part of the url too
        #     and retrieve the list of tokens for that taskid as allowed targets.
        #   - url without (access) token has task token. authenticate this.
        #     Then allow only messaging if target is coordinator.

        #print("@@@@@", token, taskid)

        # Either authenticated user or anonymous user access this.
        # Either task_tokens or coordinator should be used later to control messaging requests.
        user = None
        anon_user = None

        self.username = self.scope["url_route"]["kwargs"]["username"]
        self.group_name = f"user_{self.username}"  # Unique channel name for the user

        #
        # Case: Authenticated user
        #
        if token: # if access token is present, indicating logged-in user
            jwt_auth = MongoJWTAuthentication()
            try:
                validated_token = jwt_auth.get_validated_token(token)
                user = jwt_auth.get_user(validated_token)
                #print("444444", user, user.id)
            except Exception as e:
                print(str(e))
                #pass

        # Obtain the list of tokens for this logged-in user and taskid
        self.task_tokens = []
        if user is not None:
            collection = get_db()["task_links"]

            # Query filter
            query = {
                "uid": self.username,
                "taskid": taskid
            }

            # Only return the `tasklink` field (1 = include, 0 = exclude `_id`)
            projection = {
                "tasklink": 1,
                "_id": 0
            }

            # Perform query
            results = collection.find(query, projection)

            # Extract tasklink into a list
            self.task_tokens = [doc["tasklink"] for doc in results if "tasklink" in doc]


        #
        # Case: Anonymous user
        #
        if not token: # if access token is not present, indicating anonymous user
            factory = APIRequestFactory()
            request = factory.get('/fake-url/', HTTP_X_ANONYMOUS_TOKEN=self.username)  # header key is capitalized with HTTP_ prefix
            auth = AnonymousTokenAuthentication()

            try:
                anon_user, _ = auth.authenticate(Request(request))
                if anon_user and getattr(anon_user, "is_anonymous_token", False):
                    print("Anonymous user authenticated:", anon_user.token)
                else:
                    print("Token invalid or user not anonymous.")
            except AuthenticationFailed as e:
                print("Authentication failed:", str(e))

        # Get the coordinator for the anonymous user
        self.coordinator = None
        if anon_user is not None:
            collection = get_db()["task_links"]
            doc = collection.find_one({"tasklink": self.username}, {"uid": 1})  # Only return 'uid' field
            if doc and 'uid' in doc:
                self.coordinator = doc['uid']




        # Join the group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        connected_users[self.username] = self  # Store connection
        await self.accept()

        # Notify the user
        await self.send(text_data=json.dumps({"message": f"{self.username} connected!!"}))


        # Custom checking...
        print("CONN", self.username, self.group_name, self.channel_name, token, self.coordinator, self.task_tokens)


    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        connected_users.pop(self.username, None)

        print("DISCONN", self.username)

    async def receive(self, text_data):
        data = json.loads(text_data)
        recipients = data.get("recipients", [])  # List of users to send the message
        message = data.get("message", "")
        data_ = data.get("data", None)

        for recipient in recipients:
            recipient_group = f"user_{recipient}"  # Target recipient group
            await self.channel_layer.group_send(
                recipient_group,
                {
                    "type": "chat_message",
                    "sender": self.username,
                    "message": message,
                    "data": data_
                }
            )

    async def chat_message(self, event):
        print("%%%%", event)

        await self.send(text_data=json.dumps({
            "sender": event["sender"],
            "message": event["message"],
            "data": event["data"],
        }))
