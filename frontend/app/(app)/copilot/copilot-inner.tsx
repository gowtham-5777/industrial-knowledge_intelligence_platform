"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AppHeader } from "@/components/layout/app-header";
import {
  chatCopilot,
  createCopilotSession,
  streamCopilotChat,
  submitCopilotFeedback,
  type ChatResponse,
  type Citation,
} from "@/lib/industrial-api";
import { fetchHeroMotors, fetchMotors } from "@/lib/motors-api";
import { cn } from "@/lib/utils";

type ChatTurn = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  intent?: string | null;
  confidence?: number | null;
  messageId?: string;
  reasoning?: string | null;
};

const DEMO_QUESTIONS = [
  "What is the efficiency and temperature rise for this motor per its latest test report?",
  "What LOTO procedure applies before maintaining this motor?",
  "What ATEX certifications does this motor have and which regulation do they satisfy?",
];

export default function CopilotPageInner() {
  const params = useSearchParams();
  const motorFromUrl = params.get("motor_id");

  const [motorId, setMotorId] = useState<string | null>(motorFromUrl);
  const [motors, setMotors] = useState<{ id: string; code: string; name: string }[]>(
    [],
  );
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [lastMessageId, setLastMessageId] = useState<string | null>(null);
  const [useStream, setUseStream] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [list, hero] = await Promise.all([
          fetchMotors({ limit: 50 }),
          fetchHeroMotors().catch(() => null),
        ]);
        if (cancelled) return;
        setMotors(
          list.items.map((m) => ({ id: m.id, code: m.code, name: m.name })),
        );
        if (!motorFromUrl && hero?.hero?.id) {
          setMotorId(hero.hero.id);
        }
      } catch {
        /* empty motor list is fine */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [motorFromUrl]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const session = await createCopilotSession(motorId);
        if (!cancelled) {
          setSessionId(session.id);
          setTurns([]);
        }
      } catch {
        if (!cancelled) setSessionId(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [motorId]);

  const motorLabel = useMemo(() => {
    const m = motors.find((x) => x.id === motorId);
    return m ? `${m.name} (${m.code})` : motorId || "Global (no motor scope)";
  }, [motors, motorId]);

  const send = useCallback(
    async (message: string) => {
      const text = message.trim();
      if (!text || streaming) return;
      setInput("");
      setTurns((prev) => [...prev, { role: "user", content: text }]);
      setStreaming(true);
      setStatus("Routing…");

      try {
        if (useStream) {
          let draft = "";
          setTurns((prev) => [...prev, { role: "assistant", content: "" }]);
          for await (const evt of streamCopilotChat({
            message: text,
            sessionId,
            motorId,
          })) {
            if (evt.event === "status") {
              const stage = (evt.data as { stage?: string })?.stage;
              setStatus(stage ? `Stage: ${stage}` : null);
            } else if (evt.event === "route") {
              const intent = (evt.data as { intent?: string })?.intent;
              setStatus(intent ? `Intent: ${intent}` : null);
            } else if (evt.event === "token") {
              draft += (evt.data as { text?: string })?.text || "";
              setTurns((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = {
                  role: "assistant",
                  content: draft,
                };
                return copy;
              });
            } else if (evt.event === "final") {
              const final = evt.data as ChatResponse;
              setLastMessageId(final.message_id);
              setSessionId(final.session_id);
              setTurns((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = {
                  role: "assistant",
                  content: final.answer,
                  citations: final.citations,
                  intent: final.intent,
                  confidence: final.confidence,
                  messageId: final.message_id,
                  reasoning: final.reasoning,
                };
                return copy;
              });
            }
          }
        } else {
          const res = await chatCopilot({
            message: text,
            sessionId,
            motorId,
          });
          setSessionId(res.session_id);
          setLastMessageId(res.message_id);
          setTurns((prev) => [
            ...prev,
            {
              role: "assistant",
              content: res.answer,
              citations: res.citations,
              intent: res.intent,
              confidence: res.confidence,
              messageId: res.message_id,
              reasoning: res.reasoning,
            },
          ]);
        }
      } catch {
        setTurns((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              "Copilot could not complete this turn. Check API connectivity and try again.",
          },
        ]);
      } finally {
        setStreaming(false);
        setStatus(null);
      }
    },
    [motorId, sessionId, streaming, useStream],
  );

  return (
    <>
      <AppHeader
        title="Industrial Copilot"
        description="Motor-aware industrial Q&A with evidence citations."
      />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="border-b border-border bg-gradient-to-r from-[#e8f2f3] via-background to-[#f2efe8] px-5 py-3">
          <div className="mx-auto flex max-w-4xl flex-wrap items-end gap-3">
            <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-xs">
              <span className="font-medium text-muted-foreground">Motor scope</span>
              <select
                className="rounded-md border border-border bg-card px-3 py-2 text-sm"
                value={motorId || ""}
                onChange={(e) => setMotorId(e.target.value || null)}
              >
                <option value="">Global (no motor)</option>
                {motors.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.code})
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 pb-2 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={useStream}
                onChange={(e) => setUseStream(e.target.checked)}
              />
              Stream answers
            </label>
            <p className="pb-2 text-xs text-muted-foreground">
              Active: <span className="text-foreground">{motorLabel}</span>
            </p>
          </div>
        </div>

        <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-3 overflow-y-auto px-5 py-4">
          <div className="flex flex-wrap gap-2">
            {DEMO_QUESTIONS.map((q) => (
              <button
                key={q}
                type="button"
                disabled={streaming}
                onClick={() => send(q)}
                className="rounded-md border border-border bg-card px-3 py-1.5 text-left text-xs text-foreground transition hover:border-accent hover:bg-accent/5"
              >
                {q}
              </button>
            ))}
          </div>

          {turns.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border px-4 py-10 text-center text-sm text-muted-foreground">
              Ask a motor-scoped question. Answers include citations when evidence
              is indexed.
            </div>
          ) : null}

          {turns.map((t, idx) => (
            <article
              key={`${t.role}-${idx}`}
              className={cn(
                "rounded-lg border px-4 py-3 text-sm",
                t.role === "user"
                  ? "ml-8 border-accent/30 bg-accent/5"
                  : "mr-8 border-border bg-card",
              )}
            >
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {t.role === "user" ? "You" : "Industrial Copilot"}
                {t.intent ? ` · ${t.intent}` : ""}
                {typeof t.confidence === "number"
                  ? ` · confidence ${(t.confidence * 100).toFixed(0)}%`
                  : ""}
              </p>
              <p className="mt-2 whitespace-pre-wrap leading-relaxed">{t.content}</p>
              {t.reasoning ? (
                <p className="mt-2 text-xs text-muted-foreground">{t.reasoning}</p>
              ) : null}
              {t.citations && t.citations.length > 0 ? (
                <ul className="mt-3 space-y-1 border-t border-border pt-2 text-xs text-muted-foreground">
                  {t.citations.slice(0, 6).map((c, i) => (
                    <li key={i}>
                      {c.citation || c.document_id || "source"}
                      {c.text ? ` — ${c.text.slice(0, 120)}` : ""}
                    </li>
                  ))}
                </ul>
              ) : null}
            </article>
          ))}

          {status ? (
            <p className="text-xs text-muted-foreground animate-pulse">{status}</p>
          ) : null}
        </div>

        <div className="border-t border-border bg-card px-5 py-3">
          <form
            className="mx-auto flex max-w-4xl gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void send(input);
            }}
          >
            <input
              className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none ring-accent focus:ring-2"
              placeholder="Ask about specs, tests, LOTO, certifications…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={streaming}
            />
            <button
              type="submit"
              disabled={streaming || !input.trim()}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground disabled:opacity-50"
            >
              Send
            </button>
            {lastMessageId ? (
              <>
                <button
                  type="button"
                  className="rounded-md border border-border px-3 py-2 text-xs"
                  onClick={() =>
                    void submitCopilotFeedback({
                      rating: 5,
                      sessionId,
                      messageId: lastMessageId,
                    })
                  }
                >
                  Helpful
                </button>
                <button
                  type="button"
                  className="rounded-md border border-border px-3 py-2 text-xs"
                  onClick={() =>
                    void submitCopilotFeedback({
                      rating: 1,
                      sessionId,
                      messageId: lastMessageId,
                    })
                  }
                >
                  Needs work
                </button>
              </>
            ) : null}
          </form>
        </div>
      </main>
    </>
  );
}
