from dataclasses import dataclass
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator, model_validator



class Patient(BaseModel):
    age: Optional[int] = None
    weight: Optional[tuple[int,int]] = None
    biological_sex: Optional[Literal["female", "male", "other"]] = None
    is_pregnant: Optional[bool] = None
    comorbidities: Optional[List[str]] = None

class Drug(BaseModel):
    name: str
    via: Optional[str] = None
    dose: Optional[str] = None


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
    def validate_dose(cls, value: Optional[str]):
        if value is None:
            return None

        import re
        if not re.fullmatch(r"\d+(?:[.,]\d+)?\s?(ml|mg|u)", value.strip().lower()):
            raise ValueError("dose deve estar no formato numero + unidade, ex: 10mg, 5 ml, 2u")
        return value.strip().lower


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

    def montar_contexto_medicamentos(self, valid_drugs:List[str]) -> str:
        
        drugs_names = [name.lower() for name in valid_drugs]
        if not drugs_names:
                return None

        linhas = []
        for drug in self.drugs:
            if drug.name not in drugs_names:
                continue 

            linha = f"- {drug.name}"
            if drug.via:
                linha += f" (via: {drug.via})"
            if drug.dose:
                linha += f"\n (dose: {drug.dose})"
            linhas.append(linha)
        
        return "\n".join(linhas)

# def montar_contexto_medicamentos_considerados(
#     drogas_requisitadas,
#     drugs_considerados: list[str],
# ) -> str:
#     nomes_considerados = {drug.lower() for drug in drugs_considerados}
#     linhas = []

#     for drug in drogas_requisitadas:
#         if drug.name not in nomes_considerados and drug.name.lower() not in nomes_considerados:
#             continue

#         linha = f"- {drug.name}"
#         if drug.via:
#             linha += f" (via: {drug.via})"
#         linhas.append(linha)

#     if linhas:
#         return "\n".join(linhas)

#     return "\n".join(f"- {drug}" for drug in drugs_considerados)