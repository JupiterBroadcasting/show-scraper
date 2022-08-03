from typing import Dict, List
from pydantic.dataclasses import dataclass as py_dataclass
from pydantic import HttpUrl


@py_dataclass
class ShowDetails:
    fireside_url: HttpUrl
    fireside_slug: str
    jb_url: HttpUrl
    acronym: str
    name: str

@py_dataclass
class ConfigData:
    shows: Dict[str,ShowDetails]
    usernames_map: Dict[str,str]
