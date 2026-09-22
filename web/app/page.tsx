"use client";

import { useState } from "react";

type Claim = {
  text: string;
  source: string;
  source_url: string;
  title: string | null;
  topics: string[];
  lang: string;
  translation_of: string | null;
};

type AskResponse = {
  claims: Claim[];
  conflicts: unknown[];
  answer: string | null;
};

export default function Home() {
  const [question, setQuestion] = useState("");
  const [lang, setLang] = useState<"de" | "en">("de");
  const [compose, setCompose] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);

  async function ask() {
    if (!question.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const r = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, lang, compose }),
      });
      if (!r.ok) throw new Error(`Backend: ${r.status}`);
      setResult(await r.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-semibold">bby_wise</h1>
      <p className="mt-1 text-sm text-stone-500">
        Everyday baby questions, answered from guidelines.
      </p>

      <div className="mt-6 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask();
            }
          }}
          placeholder={
            lang === "de"
              ? "z. B. Wie lange schlafen Babys?"
              : "e.g. How long do babies sleep?"
          }
          rows={3}
          className="w-full resize-none rounded-xl border border-stone-200 p-3 text-[15px] outline-none focus:border-stone-400"
        />
        <div className="mt-3 flex items-center gap-3">
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
          <label className="flex items-center gap-1.5 text-sm text-stone-600">
            <input
              type="checkbox"
              checked={compose}
              onChange={(e) => setCompose(e.target.checked)}
              className="accent-stone-900"
            />
            Compose answer
          </label>
          <button
            onClick={ask}
            disabled={loading || !question.trim()}
            className="ml-auto rounded-full bg-stone-900 px-5 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {loading ? "…" : "Ask"}
          </button>
        </div>
      </div>

      {error && (
        <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-6 space-y-4">
          {result.answer && (
            <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
              <p className="text-[15px] leading-relaxed whitespace-pre-line">
                {result.answer}
              </p>
            </div>
          )}
          {result.claims.length === 0 && (
            <p className="text-sm text-stone-500">
              No matching guidelines found. Try different words.
            </p>
          )}
          {result.claims.map((c) => (
            <article
              key={`${c.source_url}-${c.lang}`}
              className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
            >
              <h2 className="font-medium">{c.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-stone-700 whitespace-pre-line">
                {c.text}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs">
                <span className="rounded-full bg-stone-900 px-2 py-0.5 text-white">
                  {c.source.toUpperCase()}
                </span>
                {c.translation_of && (
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800">
                    translated
                  </span>
                )}
                {c.topics.map((t) => (
                  <span
                    key={t}
                    className="rounded-full bg-stone-100 px-2 py-0.5 text-stone-600"
                  >
                    {t}
                  </span>
                ))}
                <a
                  href={c.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-auto text-stone-400 underline"
                >
                  source ↗
                </a>
              </div>
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
