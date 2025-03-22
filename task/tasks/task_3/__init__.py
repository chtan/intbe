import yaml
from collections import defaultdict
from django.conf import settings
import pymongo
from pathlib import Path

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


# State/Condition Diagram


choiceSelectionSequence = defaultdict(list) # to be populated by data from db and vice versa

configuration_yaml_string = """
stateTree:
  root:
    page:
      - pageTransition
      - choiceSelectionSequence

# i in [0, 2]
page:
  - 0
  - 1
  - 2

# These will show up as choice on page
# i->j if |i-j| = 1 and i>=1, i<=N-2
# and (0, 1) and (N-1, N-1)
pageTransition:
  (0, 1): true
  (1, 2): true
  (1, 0): true
  (2, 1): true

choiceSelectionSequence:
  _: "active when empty, inactive when nonempty"
"""
configuration_data = yaml.safe_load(configuration_yaml_string)


statistics_yaml_string = """
for each player,

current page
selection sequence (unattempted, correct, incorrect)
percentage attempted


for each question,

number of attempts
percentage of correct
"""

# Store structure here!!
structure = [
  {
    'title': list(questions_data.keys())[0],
    'mcq': {
      'statement': list(questions_data.values())[0]['statement'],
      'choices': list(questions_data.values())[0]['choices'],
    },
    'navigablePages': [1],
  },
  {
    'title': list(questions_data.keys())[1],
    'mcq': {
      'statement': list(questions_data.values())[1]['statement'],
      'choices': list(questions_data.values())[1]['choices'],
    },
    'navigablePages': [0, 2],
  },
  {
    'title': list(questions_data.keys())[2],
    'mcq': {
      'statement': list(questions_data.values())[2]['statement'],
      'choices': list(questions_data.values())[2]['choices'],
    },
    'navigablePages': [1],
  },
]

# Read from database
state_default = {
  'page': 0,
  'pageState': [
    {
      'choiceSequence': [],
      'chooseState': True,
    },
    {
      'choiceSequence': [],
      'chooseState': True,
    },
    {
      'choiceSequence': [],
      'chooseState': True,
    },
  ],
}


def submitChoice(state, page, choice):
  state['pageState'][page]['choiceSequence'].append(choice)
  state['pageState'][page]['chooseState'] = False

  return state


def navigate(state, page):
  state['page'] = page

  return state


def getStatistics(state):
  statistics = {}

  for i, pageState in enumerate(state['pageState']):
    if pageState['choiceSequence']:
      statistics[structure[i]['title']] = 'attempted'
    else:
      statistics[structure[i]['title']] = 'not yet attempted'

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
  d['percentage correct per question'] = [
    sum([1 for item in dd.values() if item[i]]) / d['number of attempts per question'][i] for i in range(3)
  ]

  return d