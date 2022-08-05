from pydantic import BaseModel, HttpUrl


class Sponsor(BaseModel):
    shortname: str
    name: str
    description: str
    link: HttpUrl
