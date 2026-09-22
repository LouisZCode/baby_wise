"use client";

import { useState } from "react";

type Msg = {
  id: string;
  role: string;
  content: string;
  lang: string;
  sources: string[];
  route?: { topic: string; urgent: boolean } | null;
};

export default function Home() {
  const [cid, setCid] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [question, setQuestion] = useState("");
  const [lang, setLang] = useState<"de" | "en">("de");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function newChat() {
    setCid(null);
    setMsgs([]);
    setError(null);
  }

  async function send() {
    if (!question.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      let id = cid;
      if (!id) {
        const r = await fetch("/api/conversations", { method: "POST" });
        if (!r.ok) throw new Error(`Backend: ${r.status}`);
        id = (await r.json()).id;
        setCid(id);
      }
      const r = await fetch(`/api/conversations/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, lang }),
      });
      if (!r.ok) throw new Error(`Backend: ${r.status}`);
      const turn = await r.json();
      const asst = {
        ...turn.assistant_message,
        route: turn.route ?? null,
      };
      setMsgs((m) => [...m, turn.user_message, asst]);
      setQuestion("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex h-dvh max-w-2xl flex-col px-4 py-6">
      <div className="flex items-center">
        <div>
          <h1 className="text-2xl font-semibold">bby_wise</h1>
          <p className="mt-0.5 text-sm text-stone-500">
            Everyday baby questions, answered from guidelines.
          </p>
        </div>
        <button
          onClick={newChat}
          className="ml-auto rounded-full border border-stone-200 px-4 py-1.5 text-sm text-stone-600"
        >
          New chat
        </button>
      </div>

      <div className="mt-4 flex flex-1 flex-col gap-3 overflow-y-auto pb-4">
        {msgs.map((m) => (
          <div
            key={m.id}
            className={`max-w-[85%] rounded-2xl p-3 text-[15px] leading-relaxed whitespace-pre-line ${
              m.role === "user"
                ? "self-end bg-stone-900 text-white"
                : "self-start border border-stone-200 bg-white shadow-sm"
            }`}
          >
            {m.content}
            {m.role === "assistant" && m.route?.urgent && (
              <p className="mt-2 rounded-xl bg-red-50 p-2 text-sm text-red-700">
                {m.lang === "de"
                  ? "Das klingt möglicherweise dringend — bei Unsicherheit wende dich an deine Kinderarztpraxis oder den ärztlichen Bereitschaftsdienst (116 117)."
                  : "This sounds potentially urgent — if unsure, contact your pediatrician or local emergency care."}
              </p>
            )}
            {m.role === "assistant" && m.sources.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {m.sources.map((s) => (
                  <a
                    key={s}
                    href={s}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-500 underline"
                  >
                    source ↗
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="self-start rounded-2xl border border-stone-200 bg-white p-3 text-sm text-stone-400">
            …
          </div>
        )}
      </div>

      {error && (
        <p className="mb-2 rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="rounded-2xl border border-stone-200 bg-white p-3 shadow-sm">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          rows={2}
          className="w-full resize-none rounded-xl border border-stone-200 p-3 text-[15px] outline-none focus:border-stone-400"
        />
        <div className="mt-2 flex items-center gap-3">
          <div className="flex rounded-full border border-stone-200 p-0.5 text-sm">
            {(["de", "en"] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                className={`rounded-full px-3 py-1 font-medium ${
                  lang === l ? "bg-stone-900 text-white" : "text-stone-500"
                }`}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
          <button
            onClick={send}
            disabled={loading || !question.trim()}
            className="ml-auto rounded-full bg-stone-900 px-5 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </main>
  );
}
