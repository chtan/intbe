import yaml
from collections import defaultdict
from django.conf import settings
from mongoengine.connection import get_db
from pathlib import Path
import csv
from copy import deepcopy
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json


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


default_state = {
  "pageState": [
      {
          "choiceSequence": [],
          "chooseState": True
      },
      {
          "choiceSequence": [],
          "chooseState": True
      },
      {
          "choiceSequence": [],
          "chooseState": True
      }
  ],
  "statistics": {
      "Question 1": "not yet attempted",
      "Question 2": "not yet attempted",
      "Question 3": "not yet attempted"
  }
}

structures = [
  {
    "title": "Question 1",
    "mcq": {
        "statement": "What is 1 + 1?\n",
        "choices": [
            2,
            3,
            4,
            5
        ]
    },
    "navigablePages": [
        1
    ]
  },
  {
    "title": "Question 2",
    "mcq": {
        "statement": "What is 1 + 2?\n",
        "choices": [
            2,
            3,
            4,
            5
        ]
    },
    "navigablePages": [
        0, 2
    ]
  },
  {
    "title": "Question 3",
    "mcq": {
        "statement": "What is 1 + 3?\n",
        "choices": [
            2,
            3,
            4,
            5
        ]
    },
    "navigablePages": [
        1
    ]
  },
]

selectedAnswers = [None, None, None]


def state_default():
  sd = default_state

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

  composite = {
    "state": state,
    "structure": structures[0],
    "controls": controls,
  }

  return composite


def getStructureAtIndex(result, *args):
  #print("!!!!!!!!!!2", result, args)

  state = result["state"]
  pageIndex = args[0]

  composite = {
    "state": state,
    "structure": structures[pageIndex],
  }

  return composite


def submitChoice(result, *args):
  #print("!!!!!!!!!!2", result, args) 

  tasktoken = result["tid"]
  state = result["state"]
  questionIndex, choiceIndex = args
  state["pageState"][questionIndex]['choiceSequence'].append(choiceIndex)
  state["pageState"][questionIndex]['chooseState'] = False
  state["statistics"][list(state["statistics"].keys())[questionIndex]] = "attempted"

  collection = get_db()["task_states"]
  collection.update_one(
      {"tid": tasktoken},
      {"$set": {"state": state}}
  )

  composite = {
    "state": state,
  }

  taskid = result["ttid"]
  cid = result["cid"]
  updateGlobalStatistics(tasktoken, cid, taskid)

  return composite


def updateGlobalStatistics(tasktoken, cid, taskid):
  #print("!!!!!!!!!!2", cid, taskid) 
  out = getGlobalStatistics(cid, taskid, format="json")

  sender = "anonymous_" + tasktoken + "_" + TASKID 
  receivers = ["coordinator_" + cid + "_" + TASKID]
  message = "update global statistics"
  data = json.dumps(out)
  group = f"user_{receivers[0]}"

  send_message_to_clients(sender, receivers, message, data, group)


def dict_of_dicts_to_list(data):
    # Get all unique inner keys
    all_fields = sorted({k for v in data.values() for k in v.keys()})
    header = ["Name"] + all_fields
    rows = []

    for outer_key, inner_dict in data.items():
        row = [outer_key] + [inner_dict.get(field, "") for field in all_fields]
        rows.append(row)

    return [header] + rows


def getGlobalStatistics(uid, taskid, format="listoflist"):
  collection = get_db()["task_states"]

  out = {}

  for question in ["Question 1", "Question 2", "Question 3"]:

    field = f"state.statistics.{question}"

    # Count "not yet attempted"
    not_attempted = collection.count_documents({
        "ttid": taskid,
        field: "not yet attempted"
    })

    # Count attempted (i.e., not "not yet attempted")
    attempted = collection.count_documents({
        "ttid": taskid,
        field: { "$ne": "not yet attempted" }
    })

    out[question] = {
      "attempted": attempted,
      "not_attempted": not_attempted,
    }

  if format == "listoflist":
    return dict_of_dicts_to_list(out)
  else:
    return out


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
  