import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "static"


AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT","").strip().rstrip("/")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
AZURE_MODEL = os.getenv("AZURE_OPENAI_MODEL", "").strip()

CINEIA_INSTRUCTIONS = """
Você é o CineIA, um assistente especializado em recomendar filmes e séries.

Regras:
- Seja breve, simpático e objetivo.
- Sempre sugira pelo menos um título concreto.
- Explique em uma frase por que a recomendação combina com o pedido.
- Considere gênero, clima, estilo e referências mencionadas pelo usuário.
- Se o usuário pedir apenas um gênero, também responda normalmente.
- Não repita automaticamente a recomendação anterior quando o usuário fizer um novo pedido.
""".strip()

app = FastAPI(title="CineIA API", version="1.0.0")


class ChatRequest(BaseModel):
    message: str
    previous_response_id: str | None = None


class ChatResponse(BaseModel):
        message: str
        response_id: str | None = None


@app.get("/api/health")
async def health():
    configured = bool (AZURE_ENDPOINT and AZURE_API_KEY and AZURE_MODEL)
    return{
        "status":"ok",
        "azure_configured": configured
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not AZURE_ENDPOINT or not AZURE_API_KEY or not AZURE_MODEL:
        raise HTTPException(
            status_code=500,
            detail="Configure AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY e AZURE_OPENAI_MODEL no arquivo .env"
        )

    message = request.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")

    payload = {
        "model": AZURE_MODEL,
        "instructions": CINEIA_INSTRUCTIONS,
        "input":[
            {
                "role":"user",
                "content": [
                    {
                        "type":"input_text",
                        "text": message
                    }
                ]
            }
        ]
    }

    if request.previous_response_id:
        payload["previous_response_id"] = request.previous_response_id

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            azure_response = await client.post(
                AZURE_ENDPOINT,
                headers=headers,
                json=payload
            )
        if not azure_response.is_success:
            try:
                error_json = azure_response.json()
                error_message = error_json.get("error", {}).get(
                    "message", 
                    azure_response.text
                )
            except Exception:
                error_message = azure_response.text

            raise HTTPException(
                status_code=azure_response.status_code, 
                detail=f"Azure OpenAI: {error_message}"
            )

        data = azure_response.json()

        response_text = data.get("output_text")

        if not response_text:
            #Fallback para estruturas de output em que o texto
            #não esteja disponível diretamente em output_text.
            for item in data.get("output",[]):
                for content in item.get("content",[]):
                    if content.get("text"):
                        response_text = content["text"]
                        break
                if response_text:
                    break

        if not response_text:
            raise HTTPException(
                status_code=502,
                detail="A Azure respondeu, mas não foi possível localizar o texto da resposta."
            )
        return ChatResponse(
            response=response_text,
            response_id=data.get("id")
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="A Azure demorou muito para responder."
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Não foi possível conectar à Azure:{exc}"
        )

# Serve o frontend existente
# index.html, script.js e style.css ficam dentro de static/

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")