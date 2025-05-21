import yaml
from collections import defaultdict
from django.conf import settings
import pymongo
from pathlib import Path
import csv


questions_yaml_string = """
Question 1:
  statement: >
    What is 1 + 1?
  choices:
    - 2
    - 3
    - 4
    - 5
  answer: 0
Question 2:
  statement: >
    What is 1 + 2?
  choices:
    - 1
    - 2
    - 3
    - 4
  answer: 2
Question 3:
  statement: >
    What is 3 + 1?
  choices:
    - 1
    - 2
    - 3
    - 4
  answer: 3
"""
questions_data = yaml.safe_load(questions_yaml_string)


class McqTasklet:
  def __init__(self, title, mcq, navigablePages):
    self.title = title
    self.mcq = mcq
    self.navigablePages = navigablePages

  def pageState(self):
    d = {
      'choiceSequence': [],
      'chooseState': True,
    }

    return d

  def structure(self):
    d = {
      'title': self.title,
      'mcq': self.mcq,
      'navigablePages': self.navigablePages,
    }

    return d


# Read from database
tasklets = [
  McqTasklet(
    list(questions_data.keys())[0],
    {
      'statement': list(questions_data.values())[0]['statement'],
      'choices': list(questions_data.values())[0]['choices'],
    },
    [1]
  ), 
  McqTasklet(
    list(questions_data.keys())[1],
    {
      'statement': list(questions_data.values())[1]['statement'],
      'choices': list(questions_data.values())[1]['choices'],
    },
    [0, 2]
  ),
  McqTasklet(
    list(questions_data.keys())[2],
    {
      'statement': list(questions_data.values())[2]['statement'],
      'choices': list(questions_data.values())[2]['choices'],
    },
    [1]
  ),
]


structure_base = {}


def getStructure(x):
  if type(x) != type(0):
    i = x['page'] # x is state
  else:
    i = x # locally, input is index

  s = tasklets[i].structure()

  return structure_base | s


def state_default():
  sd = {
    'page': 0,
    'pageState': [],
  }

  for tasklet in tasklets:
    sd['pageState'].append(tasklet.pageState())

  sd['statistics'] = getStatistics(sd)

  return sd


def submitChoice(structure, state, tid, *args):
  page = state['page']
  #page = args[0] # question index
  choice = args[1]

  state['pageState'][page]['choiceSequence'].append(choice)
  state['pageState'][page]['chooseState'] = False 
  state['statistics'] = getStatistics(state)

  dbclient = pymongo.MongoClient(settings.MONGO_URI)
  db = dbclient[settings.MONGO_DB_NAME]
  collection = db["task_states"]

  query = {
      'tid': tid,
  }
  doc = collection.find_one(query)

  if doc:
   # doc['state']['pageState'][page] = state['pageState'][page]
    doc['state'] = state

    collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"state": doc["state"]}}
    )
  else:
    print("Document not found.")

  return structure, state


def navigate(structure, state, tid, *args):
  state['page'] = args[0]

  dbclient = pymongo.MongoClient(settings.MONGO_URI)
  db = dbclient[settings.MONGO_DB_NAME]
  collection = db["task_states"]

  query = {
      'tid': tid,
  }
  doc = collection.find_one(query)

  if doc:
    doc['state']['page'] = state['page']

    # In mongoshell:
    # db.task_states.updateOne({'tid':'aaaaaa70'}, {'$set': { 'state.page': 2 }})
    collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"state": doc["state"]}}
    )
  else:
    print("Document not found.")

  structure = getStructure(state['page'])

  return structure, state


def getStatistics(state):
  statistics = {}

  for i, pageState in enumerate(state['pageState']):
    if pageState['choiceSequence']:
      statistics[getStructure(i)['title']] = 'attempted'
    else:
      statistics[getStructure(i)['title']] = 'not yet attempted'

  return statistics


def computeGlobalStatistics():
  d = {}

  dbclient = pymongo.MongoClient(settings.MONGO_URI)
  db = dbclient[settings.MONGO_DB_NAME]
  collection = db["task_states"]

  # Get the directory containing the script
  script_dir = Path(__file__).parent

  # Get the folder name
  folder_name = script_dir.name

  ttid = folder_name[5:]

  query = {
      'ttid': ttid,
  }
  results = collection.find(query)

  dd = {}
  for doc in results:
    dd[doc['tid']] = []
    for i, pageState in enumerate(doc['state']['pageState']):
      if pageState['choiceSequence']:
        dd[doc['tid']].append(
          pageState['choiceSequence'][-1] == list(questions_data.values())[i]['answer']
        )
      else:
        dd[doc['tid']].append(None)

  d['number of taskers'] = len(dd)
  d['number of attempts per question'] = [
    sum([1 for item in dd.values() if item[i] is not None]) for i in range(3)
  ]

  d['percentage correct per question'] = []
  for i in range(3):
    if d['number of attempts per question'][i]:
      d['percentage correct per question'].append(
        sum([1 for item in dd.values() if item[i]]) / d['number of attempts per question'][i]
      )
    else:
      d['percentage correct per question'].append('undefined')

  return d


def get_download_data(s, uid, tid):
  if s == "statistics":
    data = computeGlobalStatistics()

    """
    data = {
        'number of taskers': 1,
        'number of attempts per question': [1, 1, 0],
        'percentage correct per question': [1.0, 1.0, 'undefined']
    }
    """

    # Flatten the dictionary for CSV
    flattened = {
        'number of taskers': data['number of taskers']
    }
    # Add list entries with indexed keys
    for i, val in enumerate(data['number of attempts per question']):
        flattened[f'attempts_q{i+1}'] = val
    for i, val in enumerate(data['percentage correct per question']):
        flattened[f'percent_correct_q{i+1}'] = val

    return flattened