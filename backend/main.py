from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client
from datetime import datetime
import pytz

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

def clasificar_mensaje(mensaje: str, historial: list) -> tuple[str, bool]:
    contexto = f"Mensaje del usuario: {mensaje}\nMensajes previos: {len(historial)}"
    respuesta = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        system="""Eres un clasificador. Responde SOLO con dos palabras separadas por coma.
Primera palabra - complejidad: 'simple' o 'complejo'
Segunda palabra - web search: 'search' o 'nosearch'

'complejo' si requiere análisis, estrategia o conocimiento técnico de paid media.
'search' si necesita datos actuales como benchmarks, precios, estadísticas o noticias recientes.

Ejemplos:
'hola' → simple,nosearch
'cuál es mi ROAS ideal' → complejo,nosearch
'cuánto está el CPM en Meta ahorita' → complejo,search""",
        messages=[{"role": "user", "content": contexto}]
    )

    resultado = respuesta.content[0].text.strip().lower()
    print(f"🧠 Clasificación: {resultado}")

    partes = resultado.split(",")
    modelo = "claude-sonnet-4-6" if "complejo" in partes[0] else "claude-haiku-4-5-20251001"
    usar_search = len(partes) > 1 and "search" in partes[1] and "nosearch" not in partes[1]

    return modelo, usar_search

def chat_con_web_search(modelo: str, system_prompt: str, messages: list) -> str:
    response = claude.messages.create(
        model=modelo,
        max_tokens=2048,
        system=system_prompt,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search"
        }],
        messages=messages
    )

    final_messages = messages.copy()

    while response.stop_reason == "tool_use":
        tool_use_block = next(b for b in response.content if b.type == "tool_use")
        print(f"🌐 Buscando: {tool_use_block.input.get('query', '')}")

        final_messages.append({
            "role": "assistant",
            "content": response.content
        })

        final_messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": "Search completed"
            }]
        })

        response = claude.messages.create(
            model=modelo,
            max_tokens=2048,
            system=system_prompt,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }],
            messages=final_messages
        )

    for block in response.content:
        if hasattr(block, "text"):
            return block.text

    return "No pude generar una respuesta."

@app.get("/")
def root():
    return {"status": "Mr. Poolbot running 🚀"}

@app.post("/chat")
def chat(request: ChatRequest):
    supabase.table("messages").insert({
        "conversation_id": request.conversation_id,
        "role": "user",
        "content": request.message
    }).execute()

    history = supabase.table("messages")\
        .select("role, content")\
        .eq("conversation_id", request.conversation_id)\
        .order("created_at")\
        .limit(10)\
        .execute()

    messages = [{"role": m["role"], "content": m["content"]} for m in history.data]

    cr_time = datetime.now(pytz.timezone("America/Costa_Rica"))
    fecha = cr_time.strftime("%A %d de %B de %Y, %I:%M %p")

    system_prompt = f"""Eres Mr. Poolbot, un asistente especializado en paid media y marketing digital, creado por Karlos.
Hoy es {fecha} (hora Costa Rica).

IDENTIDAD: Tu nombre es Mr. Poolbot. No eres Claude ni una IA genérica. Si te preguntan quién eres o quién te creó, decís que sos Mr. Poolbot, el asistente de paid media de Karlos. Powered by Claude.

ROL: Analista senior de paid media siempre disponible.
PLATAFORMAS: Google Ads, Meta Ads, TikTok Ads, LinkedIn Ads.
MÉTRICAS: CPA, ROAS, CTR, CPL, CPM, CPC.
TONO: Casual, directo, con humor sutil. Entendés spanglish y abreviaciones.
ANÁLISIS: Siempre dás contexto (vs periodo anterior, vs benchmark industria).
IDIOMA: Siempre respondés en español.
WEB SEARCH: Si te preguntan por benchmarks, datos actuales o tendencias, usá web search para dar info actualizada."""

    modelo, usar_search = clasificar_mensaje(request.message, messages)
    print(f"🤖 Modelo: {modelo} | 🔍 Web search: {usar_search}")

    if usar_search:
        reply = chat_con_web_search(modelo, system_prompt, messages)
    else:
        response = claude.messages.create(
            model=modelo,
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )
        reply = response.content[0].text

    supabase.table("messages").insert({
        "conversation_id": request.conversation_id,
        "role": "assistant",
        "content": reply
    }).execute()

    return {
        "response": reply,
        "conversation_id": request.conversation_id,
        "model_used": modelo,
        "web_search_used": usar_search
    }

@app.get("/history/{conversation_id}")
def get_history(conversation_id: str):
    history = supabase.table("messages")\
        .select("role, content")\
        .eq("conversation_id", conversation_id)\
        .order("created_at")\
        .execute()
    return {"messages": history.data}