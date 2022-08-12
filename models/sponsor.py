from typing import Literal, Optional
from pydantic import BaseModel, HttpUrl, root_validator


class Sponsor(BaseModel):
    shortname: str
    title: str
    description: str
    link: HttpUrl
