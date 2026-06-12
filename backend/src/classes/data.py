from dataclasses import dataclass
from typing import List, Literal
from pydantic import BaseModel

@dataclass
class Patient(BaseModel):
    age: int
    biological_sex: Literal["female", "male", "other"]
    is_pregnant: bool
    comorbidities: List[str]

@dataclass
class DrugRequest(BaseModel):
    drugs: List[str]
    patient: Patient