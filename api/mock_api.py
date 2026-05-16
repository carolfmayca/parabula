from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

class DrugRequest(BaseModel):
    drugs: List[str]

@app.post("/drug-interactions/check")
def check_interactions(data: DrugRequest):
    print(data)

    return {
        "status": "request received"
    }