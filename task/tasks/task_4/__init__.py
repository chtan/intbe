import yaml
from collections import defaultdict
from django.conf import settings
import pymongo
from pathlib import Path

# Read from database
state_default = {
}

