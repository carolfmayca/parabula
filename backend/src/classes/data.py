from dataclasses import dataclass
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


@dataclass
class Patient(BaseModel):
    age: Optional[int] = None
    biological_sex: Optional[Literal["female", "male", "other"]] = None
    is_pregnant: Optional[bool] = None
    comorbidities: Optional[List[str]] = None


class Drug(BaseModel):
    name: str
    via: Optional[str] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("via")
    @classmethod
    def normalize_via(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None


@dataclass
class DrugRequest(BaseModel):
    drugs: List[Drug]
    patient: Patient

    @model_validator(mode="before")
    @classmethod
    def normalize_drugs(cls, data):
        if not isinstance(data, dict):
            return data

        drugs = data.get("drugs")
        if not drugs:
            return data

        normalized = []
        for item in drugs:
            if isinstance(item, str):
                normalized.append({"name": item, "via": None})
            else:
                normalized.append(item)

        data["drugs"] = normalized
        return data


def montar_contexto_medicamentos(drugs: List[Drug]) -> str:
    linhas = []
    for drug in drugs:
        linha = f"- {drug.name}"
        if drug.via:
            linha += f" (via: {drug.via})"
        linhas.append(linha)
    return "\n".join(linhas)
