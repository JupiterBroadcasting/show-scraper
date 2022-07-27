from json import JSONEncoder
from typing import Any, Dict, List, Optional
from pydantic import AnyHttpUrl, HttpUrl
from pydantic.dataclasses import dataclass as py_dataclass

@py_dataclass
class Jbd_Episode_Record:
    """
    JBDATA_Episode_Record
    for the JB_DATA dictionary of {<show>:{<episode_number>:{<this_info>}}}
    """
    # have to mark all optional, because they are populated at various times
    jb_url: Optional[HttpUrl] = None
    # Using AnyHttpUrl, because these tend to be longer and there
    #   is a hard cap on length of 2083 for HttpUrl
    mp3_audio: Optional[AnyHttpUrl] = None
    ogg_audio: Optional[HttpUrl] = None
    video: Optional[HttpUrl] = None
    hd_video: Optional[HttpUrl] = None
    mobile_video: Optional[HttpUrl] = None
    youtube: Optional[HttpUrl] = None
