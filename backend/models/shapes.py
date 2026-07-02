from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PropertySchema(BaseModel):
    path: str
    pathUri: str
    name: str
    description: str = ""
    type: str  # text | lang-string | lang-string-list | temporal | year | number | enum | entity-search | uri | nested
    datatype: Optional[str] = None
    datatypeOptions: list[str] = Field(default_factory=list)
    languageTagPolicy: str = "not-applicable"
    nodeKind: Optional[str] = None
    nodeClass: Optional[str] = None
    nestedShape: Optional[str] = None
    minCount: int = 0
    maxCount: Optional[int] = None
    pattern: Optional[str] = None
    in_values: list[str] = Field(default_factory=list, alias="in")

    model_config = {"populate_by_name": True}


class ShapeSchema(BaseModel):
    id: str
    label: str
    description: str = ""
    targetClass: Optional[str] = None
    targetClassUri: Optional[str] = None
    properties: list[PropertySchema] = []
    additionalTypes: list[str] = []


class FormSchema(BaseModel):
    shape: ShapeSchema
    fields: list[PropertySchema]
