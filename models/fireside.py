from datetime import datetime
from typing import List
from uuid import UUID
from pydantic.dataclasses import dataclass as py_dataclass
from pydantic import AnyHttpUrl, BaseModel, Extra, Field, HttpUrl, PositiveInt

@py_dataclass
class FsShowItemAttachment:
    url: HttpUrl
    mime_type: str
    size_in_bytes: PositiveInt
    duration_in_seconds: PositiveInt

@py_dataclass
class FsShowItem:
    id: UUID
    title: str
    url: HttpUrl
    content_text: str
    content_html: str
    summary: str
    date_published: datetime
    attachments: List[FsShowItemAttachment]

@py_dataclass
class PrivateFireside:
    subtitle: str
    pubdate: datetime
    explicit: bool
    copyright: str
    owner: str
    image: AnyHttpUrl

class ShowJson(BaseModel):
    # https://stackoverflow.com/a/71838453
    class Config:
        extra = Extra.forbid
    version: HttpUrl
    title: str
    home_page_url: HttpUrl
    feed_url: HttpUrl
    description: str
    fireside: PrivateFireside = Field(None, alias='_fireside')
    items: List[FsShowItem]
