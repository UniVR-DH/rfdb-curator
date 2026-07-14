from __future__ import annotations

from pydantic import BaseModel, Field


class PropertySchema(BaseModel):
    path: str
    pathUri: str
    name: str
    description: str = ""
    # text | lang-string | lang-string-list | temporal | year | number
    # | enum | entity-search | uri | nested
    type: str
    datatype: str | None = None
    datatypeOptions: list[str] = Field(default_factory=list)
    languageTagPolicy: str = "not-applicable"
    nodeKind: str | None = None
    nodeClass: str | None = None
    nestedShape: str | None = None
    minCount: int = 0
    maxCount: int | None = None
    pattern: str | None = None
    in_values: list[str] = Field(default_factory=list, alias="in")

    model_config = {"populate_by_name": True}


class ShapeSchema(BaseModel):
    id: str
    label: str
    description: str = ""
    targetClass: str | None = None
    targetClassUri: str | None = None
    properties: list[PropertySchema] = []
    additionalTypes: list[str] = []
    typeOptions: list[dict[str, str]] = []


class FormSchema(BaseModel):
    shape: ShapeSchema
    fields: list[PropertySchema]
