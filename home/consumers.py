import json
from channels.generic.websocket import AsyncWebsocketConsumer

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
        self.username = self.scope["url_route"]["kwargs"]["username"]
        self.group_name = f"user_{self.username}"  # Unique channel name for the user

        # Join the group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        connected_users[self.username] = self  # Store connection
        await self.accept()

        # Notify the user
        await self.send(text_data=json.dumps({"message": f"{self.username} connected!!"}))

        print("CONN", self.username)

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
