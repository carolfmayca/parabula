from typing import Any, List, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


MAX_DRUGS = 20
MAX_DRUG_NAME_LENGTH = 120
MAX_VIA_LENGTH = 80
MAX_COMORBIDITIES = 20
MAX_COMORBIDITY_LENGTH = 120


class Patient(BaseModel):
    age: Optional[int] = None
    biological_sex: Optional[Literal["female", "male", "other"]] = None
    is_pregnant: Optional[bool] = None
    comorbidities: Optional[List[str]] = None

    @field_validator("age")
    @classmethod
    def validate_age(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if value < 0 or value > 130:
            raise ValueError("Idade deve estar entre 0 e 130.")
        return value

    @field_validator("comorbidities")
    @classmethod
    def normalize_comorbidities(
        cls,
        value: Optional[List[str]],
    ) -> Optional[List[str]]:
        if value is None:
            return None
        if len(value) > MAX_COMORBIDITIES:
            raise ValueError(f"Informe no máximo {MAX_COMORBIDITIES} comorbidades.")

        normalized = []
        for item in value:
            item_normalizado = item.strip()
            if not item_normalizado:
                continue
            if len(item_normalizado) > MAX_COMORBIDITY_LENGTH:
                raise ValueError(
                    "Cada comorbidade deve ter no máximo "
                    f"{MAX_COMORBIDITY_LENGTH} caracteres."
                )
            normalized.append(item_normalizado.lower())

        return normalized or None


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
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Nome do medicamento não pode ser vazio.")
        if len(normalized) > MAX_DRUG_NAME_LENGTH:
            raise ValueError(
                f"Nome do medicamento deve ter no máximo {MAX_DRUG_NAME_LENGTH} caracteres."
            )
        return normalized

    @field_validator("via")
    @classmethod
    def normalize_via(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if len(normalized) > MAX_VIA_LENGTH:
            raise ValueError(f"Via deve ter no máximo {MAX_VIA_LENGTH} caracteres.")
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
        if isinstance(drugs, list) and len(drugs) > MAX_DRUGS:
            raise ValueError(f"Informe no máximo {MAX_DRUGS} medicamentos.")

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
