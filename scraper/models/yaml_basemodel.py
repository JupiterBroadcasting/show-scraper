from typing import TYPE_CHECKING, AbstractSet, Any, Mapping, Union

import yaml
from pydantic import BaseModel

if TYPE_CHECKING:
    IntStr = int | str
    AbstractSetIntStr = AbstractSet[IntStr]
    MappingIntStrAny = Mapping[IntStr, Any]


class YAMLBaseModel(BaseModel):
    def yaml(
        self,
        *,
        include: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,  # noqa
        exclude: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,  # noqa
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        default_flow_style: bool = False,
    ) -> str:
        """Generate a yaml representation of the model.

        This uses the underlying `self.json()` method of the Pydantic BaseModel, and
        `yaml.dump()` from `PyYAML`.
        """

        _json = self.json(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        return yaml.dump(
            yaml.load(_json, yaml.Loader), default_flow_style=default_flow_style
        )
