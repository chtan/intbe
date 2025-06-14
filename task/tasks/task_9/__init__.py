import yaml
from collections import defaultdict
from django.conf import settings
import pymongo
from pathlib import Path
import csv


TASKID = Path(__file__).resolve().parent.name.split("_")[-1]


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


def getGlobalStatistics(uid, taskid, format="listoflist"):
  return {}