from typing import Dict, Set
from pydantic.dataclasses import dataclass as py_dataclass
from pydantic import HttpUrl, Extra


@py_dataclass
class ShowDetails:
    fireside_url: HttpUrl
    fireside_slug: str
    jb_url: HttpUrl
    acronym: str
    name: str

@py_dataclass
class ConfigData:
    class Config:
        extra = Extra.forbid
    shows: Dict[str,ShowDetails]
    usernames_map: Dict[str,Set[str]]
