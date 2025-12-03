"""This is General Response"""

from typing import Dict, Any
from pydantic import BaseModel
from uuid import UUID

class Successful_Query(BaseModel):
    msg : str
    id : UUID
    