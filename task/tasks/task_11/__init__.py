import yaml
from collections import defaultdict
from django.conf import settings
from mongoengine.connection import get_db
from pathlib import Path
import csv
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


TASKID = Path(__file__).resolve().parent.name.split("_")[-1]

def send_message_to_clients(sender, receivers, message, data, group):
  """
  This is using channel layer to send message.
  """
  channel_layer = get_channel_layer() # This is channel layer outside the context of consumers.
    
  # Ensure receivers is a list
  if not isinstance(receivers, list):
    receivers = [receivers]
    
  for receiver in receivers:
    async_to_sync(channel_layer.group_send)(
      #f"user_{receiver}", # this is the name of the group
      group,
      {
        "type": "chat_message", # this refers to the specific method in home/consumers.py
        "message": message,
        "sender": sender,
        "data": data,
      }
    )


structure = [
  {
    'audioUrl': 'tasks/task-5/boy+busstop.wav',
    'imageUrl': 'tasks/task-5/boy+busstop.png'
  },
  {
    'audioUrl': 'tasks/task-5/boy+busstop+q1.wav',
    'markdown': '''1. 小明在等公交车时，看到了什么？''',
    'options': [
      'A. 便利店的老板在开门',
      'B. 街道上有小贩在卖早餐',
      'C. 一群学生在跑步',
      'D. 公交车已经停在站牌前',
    ],
  },
  {
    'audioUrl': 'tasks/task-5/boy+busstop+q2.wav',
    'markdown': '''2. 在公交车上，小明做了什么好事？''',
    'options': [
      'A. 给别人让座',
      'B. 帮助老爷爷扶稳身体',
      'C. 帮司机收车费',
      'D. 递早餐给小朋友',
    ],
  }
]


def state_default():
  # mongodb require string keys
  sd = {
    '0': None,
    '1': None
  }

  return sd


def submitChoice(state, view, value):
  state[view] = value

  return state


def getCompositeOnStart(result, *args):
  #print("!!!!!!!!!!", result, args)

  state = result["state"]

  collection = get_db()["task_control_states"]
  result = collection.find_one(
      { 'taskid': TASKID },
  )
  controls = result["state"]
  # This is to be toggled by hand, hence not stored in state.
  controls["auto"] = True 

  composite = {
    "state": state,
    "structure": structure,
    "controls": controls,
  }

  return composite


def getGlobalStatistics(uid, taskid, format="listoflist"):
  pass


def setOption(res, choiceIndex, questionIndex, *args):
  #print(res, choiceIndex, questionIndex, args, "$$$$$$$")
  collection = get_db()["task_states"]

  tid = res['tid']
  query = {
      'tid': tid,
  }

  result = collection.update_one(
      query,  # filter
      { "$set": { f"state.{questionIndex}": choiceIndex } }  # update nested field
  )

  composite = {}

  if result.matched_count:
    res["state"][str(questionIndex)] = choiceIndex
    composite["state"] = res["state"]

  return composite


def toggleService(cid, *args):
  serviceState = args[0]

  collection1 = get_db()["task_control_states"]

  result = collection1.update_one(
      { 'taskid': TASKID },
      { '$set': { 'state.on': bool(int(serviceState))}}
  )

  collection2 = get_db()["task_links"]

  # Query and collect tasklink values
  tasklinks = collection2.find(
      { 'taskid': TASKID },
      { 'tasklink': 1, '_id': 0 }  # Project only tasklink field
  )

  # Extract tasklink values into a list
  #self.username = "anonymous_" + tasktoken + "_" + taskid
  tasklink_list = [
    "anonymous_" + doc['tasklink'] + "_" + TASKID 
    for doc in tasklinks if 'tasklink' in doc
  ]

  # "coordinator_" + self.scope["url_route"]["kwargs"]["username"] + "_" + taskid
  sender = "coordinator_" + cid + "_" + TASKID
  receivers = tasklink_list
  message = "toggle service"
  data = serviceState
  group = f"user_{sender}"

  send_message_to_clients(sender, receivers, message, data, group)

