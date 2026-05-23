from fastapi import FastAPI
from pydantic import BaseModel
from agent.agent import request_to_agent_sync

app = FastAPI()

class CommandRequest(BaseModel):
    commands: list[str]

@app.post("/run")
def run_agent_command(data: CommandRequest):
    response = request_to_agent_sync(data.commands)
    return {"response": response}