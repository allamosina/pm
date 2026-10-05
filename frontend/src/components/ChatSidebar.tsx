import { useEffect, useRef, useState } from "react";

export type ChatMessage = { role: "user" | "assistant"; content: string };

type Props = {
  disabled: boolean;
  onSend: (question: string, history: ChatMessage[]) => Promise<string | null>;
};

export function ChatSidebar({ disabled, onSend }: Props) {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const sending = useRef(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const log = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [history, pending]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || disabled || sending.current) return;
    sending.current = true;
    setPending(true);
    try {
      const reply = await onSend(question, history.slice(-40));
      if (reply !== null) {
        setHistory(previous => [...previous, { role: "user", content: question }, { role: "assistant", content: reply }]);
        setDraft("");
      }
    } finally {
      sending.current = false;
      setPending(false);
      requestAnimationFrame(() => input.current?.focus());
    }
  }

  return (
    <aside aria-labelledby="chat-title" className="min-w-0 rounded-3xl border border-[var(--stroke)] bg-white p-5 shadow-[var(--shadow)] xl:sticky xl:top-6 xl:self-start">
      <h2 id="chat-title" className="font-display text-xl font-semibold text-[var(--navy-dark)]">Board assistant</h2>
      <p className="mt-2 text-sm text-[var(--gray-text)]">Ask about your board, or create, edit, and move cards.</p>
      <p className="mt-2 text-xs text-[var(--gray-text)]">Conversation clears on reload or sign-out.</p>
      <div ref={log} role="log" aria-label="Conversation" aria-live="polite" tabIndex={0} className="my-4 max-h-[45vh] min-h-24 space-y-3 overflow-y-auto rounded-xl focus-visible:outline-[var(--primary-blue)]">
        {history.length === 0 && <p className="p-2 text-sm text-[var(--gray-text)]">Try “Create a card to review the launch plan.”</p>}
        {history.map((message, index) => <div key={index} className={`rounded-xl p-3 text-sm whitespace-pre-wrap break-words ${message.role === "user" ? "bg-[var(--surface)]" : "bg-purple-50"}`}>
          <p className="mb-1 text-xs font-semibold text-[var(--secondary-purple)]">{message.role === "user" ? "You" : "Assistant"}</p>
          {message.content}
        </div>)}
        {pending && <p role="status" className="text-sm text-[var(--gray-text)]">Thinking...</p>}
      </div>
      <form onSubmit={submit} className="space-y-3">
        <label className="block text-sm font-medium" htmlFor="chat-question">Message</label>
        <textarea id="chat-question" ref={input} value={draft} onChange={event => setDraft(event.target.value)} disabled={pending} required maxLength={4000} rows={3} placeholder="How can I help?" className="w-full resize-y rounded-xl border border-[var(--stroke)] p-3 text-sm focus:outline-[var(--primary-blue)] disabled:opacity-60" />
        <button disabled={disabled || pending || !draft.trim()} className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{pending ? "Sending..." : "Send message"}</button>
      </form>
    </aside>
  );
}
