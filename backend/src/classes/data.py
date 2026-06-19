from typing import Any, List, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator



class Patient(BaseModel):
    age: Optional[int] = None
    biological_sex: Optional[Literal["female", "male", "other"]] = None
    is_pregnant: Optional[bool] = None
    comorbidities: Optional[List[str]] = None


class Drug(BaseModel):
    name: str
    via: Optional[str] = None
    dose: Optional[Any] = None
    doses: Optional[Any] = None

    @model_validator(mode="after")
    def normalize_dose_alias(self):
        if self.dose is None and self.doses is not None:
            self.dose = self.doses
        return self

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

    def model_dump_for_log(self) -> dict:
        data = self.model_dump(exclude_none=True)
        if data.get("doses") == data.get("dose"):
            data.pop("doses", None)
        return data



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

    def montar_contexto_medicamentos(self) -> str:
        linhas = []
        for drug in self.drugs:
            linha = f"- {drug.name}"
            details = []
            if drug.via:
                details.append(f"via: {drug.via}")
            if drug.dose is not None:
                details.append(f"dose: {drug.dose}")
            if details:
                linha += f" ({', '.join(details)})"
            linhas.append(linha)
        return "\n".join(linhas)
