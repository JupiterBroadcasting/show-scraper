from typing import Literal, Optional
from pydantic import BaseModel, HttpUrl, root_validator


class Person(BaseModel):

    type: Literal["host", "guest"]
    username: str  # Unique ID
    name: str
    bio: Optional[str]
    avatar: Optional[str]
    avatar_small: Optional[str]
    homepage: Optional[HttpUrl]
    twitter: Optional[HttpUrl]
    linkedin: Optional[HttpUrl]
    instagram: Optional[HttpUrl]
    gplus: Optional[HttpUrl]
    youtube: Optional[HttpUrl]


    # TODO validate social links domain names
