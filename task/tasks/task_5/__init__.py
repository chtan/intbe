import yaml
from collections import defaultdict
from django.conf import settings
import pymongo
from pathlib import Path
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# structure to state
# it depends on what is changing and what is fixed
# dependency basis: app > page > tid (user)
# state dependent on app is structure
# state dependent on tid is state
# state dependent on page is hybrid


def send_message_to_clients(sender, receivers, message, data):
  channel_layer = get_channel_layer()
    
  # Ensure receivers is a list
  if not isinstance(receivers, list):
    receivers = [receivers]
    
  for receiver in receivers:
    async_to_sync(channel_layer.group_send)(
      f"user_{receiver}",
      {
        "type": "chat_message",
        "message": message,
        "sender": sender,
        "data": data,
      }
    )


# This is to be called by coordinator
def set_auto(boolValue, cid, tid):
  #print("Hello!!!!!!!!!!!!!!!!!", bool(boolValue), cid, tid)

  dbclient = pymongo.MongoClient(settings.MONGO_URI)
  db = dbclient[settings.MONGO_DB_NAME]
  collection = db["usertasks"]
  query = {"uid": cid, "tid": tid}
  result = collection.update_one(
      query,  # filter
      { "$set": { f"controls.auto": bool(boolValue) } }  # update nested field
  )

  if result:
    collection = db["task_links"]
    query = {"taskid": tid}
    results = collection.find(query)
    tids = [item['tasklink'] for item in results]

    sender = cid
    receivers = tids
    message = "set auto"
    data = bool(boolValue)

    send_message_to_clients(sender, receivers, message, data)

  return result


# This is page-dependent structure
def getContent(page):
  if page == 0:
    d = {
      'audioUrl': 'tasks/task-5/boy+busstop.wav',
      'imageUrl': 'tasks/task-5/boy+busstop.png'
    }

    return d

  elif page == 1:
    d = {
      'audioUrl': 'tasks/task-5/boy+busstop+q1.wav',
      'markdown': '''1. 小明在等公交车时，看到了什么？''',
      'options': [
        'A. 便利店的老板在开门',
        'B. 街道上有小贩在卖早餐',
        'C. 一群学生在跑步',
        'D. 公交车已经停在站牌前',
      ],
    }

    return d

  elif page == 2:
    d = {
      'audioUrl': 'tasks/task-5/boy+busstop+q2.wav',
      'markdown': '''2. 在公交车上，小明做了什么好事？''',
      'options': [
        'A. 给别人让座',
        'B. 帮助老爷爷扶稳身体',
        'C. 帮司机收车费',
        'D. 递早餐给小朋友',
      ],
    }

    return d

  return {}



def restart(structure, state, tid, *args):
  dbclient = pymongo.MongoClient(settings.MONGO_URI)
  db = dbclient[settings.MONGO_DB_NAME]
  collection = db["task_states"]

  query = {
      'tid': tid,
  }

  doc = collection.find_one(query)

  if doc:
      current_value = doc["ostate"]["restart"]
      new_value = current_value + 1

      result = collection.update_one(
          query,
          { 
            "$set": { 
              "ostate.restart": new_value,
              "state.page": -1,
            } 
          }
      )
  else:
      print("Field not found or document doesn't match query.")

  state['page'] = -1
  structure = getStructure(state)

  return structure, state



def getOption(structure, state, tid, *args):
  dbclient = pymongo.MongoClient(settings.MONGO_URI)
  db = dbclient[settings.MONGO_DB_NAME]
  collection = db["task_states"]

  query = {
      'tid': tid,
  }
  doc = collection.find_one(query)

  if doc:
     return doc['state']['selectedOptions'][state['page'] - 1]
  else:
    # throw exception
    pass


def submit(structure, state, tid, *args):
  return increasePage(structure, state, tid)

def start(structure, state, tid, *args):
  return increasePage(structure, state, tid)

def setOption(structure, state, tid, *args):
  option = args[0]

  dbclient = pymongo.MongoClient(settings.MONGO_URI)
  db = dbclient[settings.MONGO_DB_NAME]
  collection = db["task_states"]

  query = {
      'tid': tid,
  }

  result = collection.update_one(
      query,  # filter
      { "$set": { f"ostate.selectedOptions.{state['page'] - 1}": option } }  # update nested field
  )

  #print("Matched:", result.matched_count)
  #print("Modified:", result.modified_count)

  state['selectedOption'] = option

  return structure, state


# app > page > user (tid)

# app structure
structure_base = {
  'maxPageIndex': 2,
}

# state for page
state_default = {
  'page': -1,
}

# overall state
ostate_default = {
  'selectedOptions': [None, None],
  'restart': 0,
}


def getStructure(state):
  structure = structure_base | getContent(state['page'])

  return structure


def increasePage(structure, state, tid, *args):
  """
  Note that dependency:
  structure depends on state (via page)
  state depends on tid
  """
  state['page'] += 1

  dbclient = pymongo.MongoClient(settings.MONGO_URI)
  db = dbclient[settings.MONGO_DB_NAME]
  collection = db["task_states"]

  query = {
      'tid': tid,
  }
  doc = collection.find_one(query)

  if doc:
    doc['state']['page'] = state['page']

    if state['page'] not in [1, 2]:
      state.pop('selectedOption', None)
    else:
      state['selectedOption'] = doc['ostate']['selectedOptions'][state['page'] - 1]
    
    collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"state": doc["state"]}}
    )
  else:
    print("Document not found.")
    
  structure = getStructure(state)

  return structure, state


def decreasePage(structure, state, tid, *args):
  state['page'] -= 1

  dbclient = pymongo.MongoClient(settings.MONGO_URI)
  db = dbclient[settings.MONGO_DB_NAME]
  collection = db["task_states"]

  query = {
      'tid': tid,
  }
  doc = collection.find_one(query)

  if doc:
    doc['state']['page'] = state['page']

    if state['page'] not in [1, 2]:
      state.pop('selectedOption', None)
    else:
      state['selectedOption'] = doc['ostate']['selectedOptions'][state['page'] - 1]
    
    collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"state": doc["state"]}}
    )
  else:
    print("Document not found.")
    
  structure = getStructure(state)

  return structure, state