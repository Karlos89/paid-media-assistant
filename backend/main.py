from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

load_dotenv(Path(__file__).parent / ".env")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

@app.get("/")
def root():
    return {"status": "Paid Media Assistant running 🚀"}

@app.post("/chat")
def chat(request: ChatRequest):
    # Guardar mensaje del usuario
    supabase.table("messages").insert({
        "conversation_id": request.conversation_id,
        "role": "user",
        "content": request.message
    }).execute()

    # Cargar historial
    history = supabase.table("messages")\
        .select("role, content")\
        .eq("conversation_id", request.conversation_id)\
        .order("created_at")\
        .limit(10)\
        .execute()

    messages = [{"role": m["role"], "content": m["content"]} for m in history.data]

    # Llamar a Claude
    response = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=messages
    )

    reply = response.content[0].text

    # Guardar respuesta
    supabase.table("messages").insert({
        "conversation_id": request.conversation_id,
        "role": "assistant",
        "content": reply
    }).execute()

    return {
        "response": reply,
        "conversation_id": request.conversation_id
    }

@app.get("/history/{conversation_id}")
def get_history(conversation_id: str):
    history = supabase.table("messages")\
        .select("role, content")\
        .eq("conversation_id", conversation_id)\
        .order("created_at")\
        .execute()
    return {"messages": history.data}