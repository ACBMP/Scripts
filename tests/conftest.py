"""Run the Scripts modules against mongomock, with a stand-in botconfig.

    uv run --no-project --with pytest --with 'pymongo<4.9' --with mongomock \
        --with flask_pymongo --with discord.py --with pydantic --with numpy pytest tests
"""

import sys
import types
from pathlib import Path

import mongomock
import pymongo
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if "botconfig" not in sys.modules:
    conf = types.ModuleType("botconfig")
    for name in ("e_channels", "mh_channels", "aa_channels", "do_channels", "dm_channels", "asb_channels",
                 "e_servers", "mh_servers", "aa_servers", "do_servers", "dm_servers", "asb_servers",
                 "synched_channels"):
        setattr(conf, name, [])
    conf.admin = []
    conf.RAU_FILE_PATH = ""
    conf.RAU_FILE_NAME = "matches.txt"
    conf.RAE_FILE_NAME = "edits.txt"
    conf.RAU_SPLIT_TOKEN = ", "
    conf.RAU_SECONDARY_TOKEN = "$"
    sys.modules["botconfig"] = conf

# every MongoClient in the scripts (they connect to localhost themselves) gets one shared store
_CLIENT = mongomock.MongoClient()
pymongo.MongoClient = lambda *args, **kwargs: _CLIENT


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("AN_MATCHOPS_LOCK", str(tmp_path / "lock"))
    import matchops

    monkeypatch.setattr(matchops, "LOCK_PATH", str(tmp_path / "lock"))
    database = _CLIENT.public
    for name in database.list_collection_names():
        database.drop_collection(name)
    return database
