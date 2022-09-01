from typing import Literal, Optional
from pydantic import BaseModel, HttpUrl, root_validator

PersonType = Literal["host", "guest"]

class Person(BaseModel):

    type: PersonType
    username: str  # Unique ID
    title: str
    bio: Optional[str]
    avatar: Optional[str]
    avatar_small: Optional[str]
    homepage: Optional[HttpUrl]
    twitter: Optional[HttpUrl]
    linkedin: Optional[HttpUrl]
    instagram: Optional[HttpUrl]
    youtube: Optional[HttpUrl]


    # TODO validate social links domain names
