import yaml
from collections import defaultdict
from django.conf import settings
import pymongo
from pathlib import Path
import csv



def state_default():
  return {}

