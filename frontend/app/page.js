"use client";
import { useState, useRef, useEffect } from "react";

const CONVERSATION_ID = "web-session";

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    const loadHistory = async () => {
      const res = await fetch(`http://127.0.0.1:8000/history/${CONVERSATION_ID}`);
      const data = await res.json();
      setMessages(data.messages);
    };
    loadHistory();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    const res = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: input, conversation_id: CONVERSATION_ID }),
    });

    const data = await res.json();
    setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-white">
      <div className="p-4 border-b border-gray-800 text-center font-bold text-lg">
        🚀 Paid Media Assistant
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-xl px-4 py-2 rounded-2xl text-sm ${m.role === "user" ? "bg-blue-600" : "bg-gray-800"}`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 px-4 py-2 rounded-2xl text-sm text-gray-400">escribiendo...</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="p-4 border-t border-gray-800 flex gap-2">
        <input
          className="flex-1 bg-gray-800 rounded-xl px-4 py-2 text-sm outline-none"
          placeholder="Preguntá algo sobre tus campañas..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage} className="bg-blue-600 px-4 py-2 rounded-xl text-sm font-bold hover:bg-blue-500">
          Enviar
        </button>
      </div>
    </div>
  );
}