from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from intbe.utils import redis_client
import json
from mongoengine.connection import get_db
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import AuthenticationFailed
from users.authentication import MongoJWTAuthentication, AnonymousTokenAuthentication


"""
Concepts:

sync, async
scope
group
channel layer

a group is created implicitly when group_add is used

"""

"""
1 consumer each for logged in and anonymous
AllowedHostsOriginValidator
logged-in must go with taskid to define a group

"""

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

# This is module level (i.e. this file) which persists as the server starts
# and ends when the server ends.
connected_users = {}  # Store active WebSocket connections

# Old code used by tasks <= 9
class ChatConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def get_coordinator(self, username):
        collection = get_db()["task_links"]
        doc = collection.find_one({"tasklink": username}, {"uid": 1})  # Only return 'uid' field
        if doc and "uid" in doc:
            return doc["uid"]
        return None

    @database_sync_to_async
    def get_task_tokens(self, username, taskid):
        collection = get_db()["task_links"]
        query = {
            "uid": username,
            "taskid": taskid
        }
        projection = {
            "tasklink": 1,
            "_id": 0
        }
        results = collection.find(query, projection)
        return [doc["tasklink"] for doc in results if "tasklink" in doc]

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

        # This comes from home/routing.py
        self.username = self.scope["url_route"]["kwargs"]["username"]
        self.group_name = f"user_{self.username}"  # Unique channel name for the user


        # Either authenticated user or anonymous user access this.
        # Either task_tokens or coordinator should be used later to control messaging requests.
        user = None
        anon_user = None

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
                await self.close()
                return

        # Obtain the list of tokens for this logged-in user and taskid
        self.task_tokens = []
        if user is not None:
            self.task_tokens = await self.get_task_tokens(self.username, taskid)




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
            self.coordinator = await self.get_coordinator(self.username)




        # Join the group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        connected_users[self.username] = self  # Store connection

        await self.accept()



        # Notify the user
        await self.send(text_data=json.dumps({"message": f"{self.username} connected!!"}))

        # Custom checking...
        print("CONN", 
            self.username, self.group_name, self.channel_name, token, 
            self.coordinator, self.task_tokens
        )

    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        connected_users.pop(self.username, None)

        print("DISCONN", self.username)

    # This corresponds to the receive message.
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

    # This corresponds to the chat.message message,
    # _ is replaced by .
    async def chat_message(self, event):
        print("%%%%", event)

        await self.send(text_data=json.dumps({
            "sender": event["sender"],
            "message": event["message"],
            "data": event["data"],
        }))




# Sample from ChatGPT
class ChatConsumer0(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "chatroom"

        # Join group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message", "")

        # Send message to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
            }
        )

    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "message": message
        }))




class ChatConsumer1(AsyncWebsocketConsumer):
    #@database_sync_to_async
    #def get_task_tokens(self, username, taskid):
    #    collection = get_db()["task_links"]
    #    query = {
    #        "uid": username,
    #        "taskid": taskid
    #    }
    #    projection = {
    #        "tasklink": 1,
    #        "_id": 0
    #    }
    #    results = collection.find(query, projection)
    #    return [doc["tasklink"] for doc in results if "tasklink" in doc]


    async def connect(self):
        query_string = self.scope["query_string"].decode()
        params = dict(x.split("=") for x in query_string.split("&") if "=" in x)
        token = params.get("token") # this is access token
        taskid = params.get("taskid")

        # This comes from home/routing.py
        self.username = "coordinator_" + self.scope["url_route"]["kwargs"]["username"] + "_" + taskid
        self.group_name = f"user_{self.username}"  # Unique channel name for the user

        # Authentication
        user = None
        jwt_auth = MongoJWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
        except Exception as e:
            print(str(e))
            await self.close()
            return

        # Obtain the list of tokens for this logged-in user and taskid
        # Use this to send message to members in the task individually.
        # Below, I'm using django channels group to do so.
        #self.task_tokens = await self.get_task_tokens(self.username, taskid)

        # Create/join the group
        redis_client.sadd(self.group_name, self.channel_name)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        # Add members back to the group (if they were previously in there, persisted in redis)
        members = redis_client.smembers(self.group_name)
        for channel_name in members:
            if channel_name != self.channel_name:
                await self.channel_layer.group_add(self.group_name, channel_name)

        # Keep an in-code module level record
        connected_users[self.username] = self  # Store connection

        # Accept
        await self.accept()

        # Notifications
        await self.send(text_data=json.dumps({"message": f"{self.username} connected!!"}))
        print("CONN", 
            self.username, self.group_name, self.channel_name
        )


    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        connected_users.pop(self.username, None)

        # The group should be persisted - until the coordinator destroys the group,
        # then it has to be removed.
        # !!!!!!!!!!!!!
        # TODO!!!!!!!
        # !!!!!!!!!!!!!
        #redis_client.srem(f"group:{self.group_name}:members", self.channel_name)

        # Notifications
        print("DISCONN", self.username)


    # This is executed when .send is executed by the other end of the web socket to here.
    async def receive(self, text_data):
        """
        We're currently just listening to messages from a channel layer -
        refer to chat_message below.
        """

        """
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
        """
        pass


    # This corresponds to the chat.message message,
    # _ is replaced by .
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "sender": event["sender"],
            "message": event["message"],
            "data": event["data"],
        }))




class ChatConsumer2(AsyncWebsocketConsumer):
    @database_sync_to_async
    def get_coordinator(self, tasktoken):
        collection = get_db()["task_links"]
        doc = collection.find_one({"tasklink": tasktoken}, {"uid": 1})  # Only return 'uid' field
        if doc and "uid" in doc:
            return doc["uid"]
        return None


    async def connect(self):
        query_string = self.scope["query_string"].decode()
        params = dict(x.split("=") for x in query_string.split("&") if "=" in x)
        taskid = params.get("taskid")

        # This comes from home/routing.py
        tasktoken = self.scope["url_route"]["kwargs"]["tasktoken"]
        self.username = "anonymous_" + tasktoken + "_" + taskid
        
        # Authentication
        anon_user = None
        factory = APIRequestFactory()
        request = factory.get('/fake-url/', HTTP_X_ANONYMOUS_TOKEN=tasktoken)  # header key is capitalized with HTTP_ prefix
        auth = AnonymousTokenAuthentication()
        try:
            anon_user, _ = auth.authenticate(Request(request))
            if anon_user and getattr(anon_user, "is_anonymous_token", False):
                print("Anonymous user authenticated:", anon_user.token)
            else:
                print("Token invalid or user not anonymous.")
        except AuthenticationFailed as e:
            print("Authentication failed:", str(e))
            await self.close()

        # Join the group of the coordinator
        self.coordinator = None
        if anon_user is not None:
            self.coordinator = await self.get_coordinator(tasktoken)
        coordinator_username = "coordinator_" + self.coordinator + "_" + taskid
        self.group_name = f"user_{coordinator_username}"  # Unique channel name for the user
        members = redis_client.smembers(self.group_name)
        if self.channel_name not in members:
            redis_client.sadd(f"group:{self.group_name}:members", self.channel_name)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        
        # Keep an in-code module level record
        connected_users[self.username] = self  # Store connection

        # Accept
        await self.accept()

        # Notifications
        await self.send(text_data=json.dumps({"message": f"{self.username} connected!!"}))
        #print("CONN", 
        #    self.username, self.group_name, self.channel_name, self.coordinator,
        #)


    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        connected_users.pop(self.username, None)
        redis_client.srem(f"group:{self.group_name}:members", self.channel_name)

        # Notifications
        print("DISCONN", self.username)

