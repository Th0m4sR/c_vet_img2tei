from pydantic import BaseModel, Field
from typing import Optional, Dict


class TransferObject(BaseModel):
    """
    This is just a placeholder to have an example what the baseModels look like
    """
    string_parameter: str = Field("Hello World", title='string_parameter')


class QueryParametersRegulation(BaseModel):
    text: Optional[str]
    dokumententitel: Optional[str]
    herausgeber: Optional[str]
    verlag: Optional[str]
    erscheinungsort: Optional[str]
    erscheinungsdatum: Optional[str]
    erscheinungsjahr: Optional[str]
    erlassdatum: Optional[str]
    inkrafttreten: Optional[str]
    seitenzahl: Optional[str]


class UpdatedRegulation(BaseModel):
    exist_name: str
    xml_regulation: str


class ProgressState(BaseModel):
    progress: int
    content: Dict
