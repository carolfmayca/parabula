from typing import Any, List, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


class Patient(BaseModel):
    age: Optional[int] = None
    weight: Optional[tuple[int, int]] = None
    biological_sex: Optional[Literal["female", "male", "other"]] = None
    is_pregnant: Optional[bool] = None
    comorbidities: Optional[List[str]] = None

    def toString(self):
        perfil_pat = []
        if self.age is not None:
            perfil_pat.append(f"- Idade: {self.age} anos")

        if self.weight:
            perfil_pat.append(
                f"- Peso: {self.weight[0]} kg e {self.weight[1]}g"
            )

        if self.biological_sex:
            perfil_pat.append(f"- Sexo biológico: {self.biological_sex}")

        if self.is_pregnant is not None:
            perfil_pat.append(f"- Grávida: {self.is_pregnant}")

        if self.comorbidities:
            perfil_pat.append(
                f"- Comorbidades: {', '.join(self.comorbidities)}"
            )

        return "\n".join(perfil_pat)

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

    @field_validator("dose")
    @classmethod
    def validate_dose(cls, value: Optional[Any]):
        if value is None:
            return None

        import re

        normalized = str(value).strip().lower()
        if not re.fullmatch(r"\d+(?:[.,]\d+)?\s?(ml|mg|u)", normalized):
            raise ValueError(
                "dose deve estar no formato numero + unidade, ex: 10mg, 5 ml, 2u"
            )
        return normalized

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

    def montar_contexto_medicamentos(
        self,
        valid_drugs: Optional[List[str]] = None,
    ) -> Optional[str]:
        drugs_names = [name.lower() for name in valid_drugs] if valid_drugs else []

        linhas = []
        for drug in self.drugs:
            if drugs_names and drug.name not in drugs_names:
                continue

            linha = f"- {drug.name}"
            details = []
            if drug.via:
                details.append(f"via: {drug.via}")
            if drug.dose is not None:
                details.append(f"dose: {drug.dose}")
            if details:
                linha += f" ({', '.join(details)})"
            linhas.append(linha)

        if not linhas:
            return None

        return "\n".join(linhas)
