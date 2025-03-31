import yaml
from collections import defaultdict
from django.conf import settings
import pymongo
from pathlib import Path

def getContent(page):
  content = {
    0: 'a',
    1: 'b',
    2: 'c',
    3: 'd',
    4: 'e',
    5: 'f',
  }

  return content[page]

# Read from database
state_default = {
  'page': 0,
  'content': getContent(0),
}

def increasePage(state):
  state['page'] += 1
  state['content'] = getContent(state['page'])

  return state

def decreasePage(state):
  state['page'] -= 1
  state['content'] = getContent(state['page'])

  return state