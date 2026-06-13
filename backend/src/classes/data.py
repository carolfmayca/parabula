from dataclasses import dataclass
from typing import List, Literal
from pydantic import BaseModel
from typing import Optional

@dataclass
class Patient(BaseModel):
    age: Optional[int] = None
    biological_sex: Optional[Literal["female", "male", "other"]] = None
    is_pregnant: Optional[bool] = None
    comorbidities: Optional[List[str]] = None

@dataclass
class DrugRequest(BaseModel):
    drugs: List[str]
    patient: Patient