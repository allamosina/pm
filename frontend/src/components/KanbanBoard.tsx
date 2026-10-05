"use client";

import { useEffect, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCorners,
  pointerWithin,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { ChatSidebar, type ChatMessage } from "@/components/ChatSidebar";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { moveCard, type BoardData } from "@/lib/kanban";

import { api, ApiError } from "@/lib/api";

const collisionDetection: CollisionDetection = args => {
  const hits = pointerWithin(args);
  const cards = hits.filter(hit => args.droppableContainers.find(container => container.id === hit.id)?.data.current?.sortable);
  return cards.length ? cards : hits.length ? hits : closestCorners(args);
};

export const KanbanBoard = ({ onSessionExpired }: { onSessionExpired: () => void }) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [needsReload, setNeedsReload] = useState(false);
  const busy = useRef(false);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    api<BoardData>("/board", { signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) setBoard(data);
    }).catch(error => {
      if (controller.signal.aborted) return;
      if (error instanceof ApiError && error.status === 401) onSessionExpired();
      else setError("Unable to load your board. Please try again.");
    });
    return () => { mounted.current = false; controller.abort(); };
  }, [onSessionExpired]);

  async function reload() {
    if (busy.current) return;
    busy.current = true;
    setSaving(true);
    try {
      const data = await api<BoardData>("/board");
      if (!mounted.current) return;
      setBoard(data);
      setNeedsReload(false);
      setError("");
    } catch (error) {
      if (!mounted.current) return;
      if (error instanceof ApiError && error.status === 401) onSessionExpired();
      else setError("Unable to load your board. Please try again.");
    } finally { busy.current = false; if (mounted.current) setSaving(false); }
  }

  async function save(path: string, method: string, fields = {}): Promise<boolean | string> {
    if (!board || busy.current || needsReload) return false;
    busy.current = true;
    setSaving(true);
    setError("");
    try {
      const suffix = method === "DELETE" ? `?expected_revision=${board.revision}` : "";
      const isChat = path === "/chat";
      const data = await api<BoardData | { reply: string; board: BoardData }>(isChat ? "/chat" : `/board${path}${suffix}`, {
        method,
        ...(method === "DELETE" ? {} : { body: JSON.stringify(isChat ? fields : { ...fields, expected_revision: board.revision }) }),
      });
      if (!mounted.current) return false;
      if ("board" in data) { setBoard(data.board); return data.reply; }
      setBoard(data);
      return true;
    } catch (error) {
      if (!mounted.current) return false;
      if (error instanceof ApiError && error.status === 401) { onSessionExpired(); return false; }
      setError(error instanceof ApiError ? error.message : "Save could not be confirmed. Review the refreshed board before retrying.");
      // A lost response may follow a committed write. Reconcile before allowing another save.
      try {
        const data = await api<BoardData>("/board");
        if (mounted.current) setBoard(data);
      } catch (reloadError) {
        if (mounted.current) {
          if (reloadError instanceof ApiError && reloadError.status === 401) onSessionExpired();
          else { setNeedsReload(true); setError("Save could not be confirmed. Reload the board before making more changes."); }
        }
      }
      return false;
    } finally { busy.current = false; if (mounted.current) setSaving(false); }
  }

  const handleDragStart = (event: DragStartEvent) => {
    if (!busy.current && !needsReload) setActiveCardId(event.active.id as string);
  };
  const handleDragEnd = (event: DragEndEvent) => {
    setActiveCardId(null);
    if (!board || !event.over || event.active.id === event.over.id) return;
    const id = String(event.active.id);
    const columns = moveCard(board.columns, id, String(event.over.id));
    const target = columns.find(column => column.cardIds.includes(id));
    if (target) void save(`/cards/${id}/move`, "POST", { column_id: target.id, position: target.cardIds.indexOf(id) });
  };
  const handleRenameColumn = async (columnId: string, title: string) => Boolean(await save(`/columns/${columnId}`, "PATCH", { title }));
  const handleAddCard = async (columnId: string, title: string, details: string) => Boolean(await save("/cards", "POST", { column_id: columnId, title, details }));
  const handleDeleteCard = async (cardId: string) => Boolean(await save(`/cards/${cardId}`, "DELETE"));
  const handleEditCard = async (cardId: string, title: string, details: string) => Boolean(await save(`/cards/${cardId}`, "PATCH", { title, details }));
  const handleChat = async (question: string, history: ChatMessage[]) => {
    const result = await save("/chat", "POST", { question, history });
    return typeof result === "string" ? result : null;
  };
  const activeCard = activeCardId ? board?.cards[activeCardId] : null;

  if (!board) return <div className="p-8">{error ? <><p role="alert">{error}</p><button disabled={saving} onClick={reload}>Try again</button></> : <p role="status">Loading your board...</p>}</div>;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1800px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                data-stage={column.id}
                className="stage-label flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--stage-color)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <div aria-live="polite">
          {saving && <p role="status">Saving...</p>}
          {error && <p role="alert">{error}</p>}
          {needsReload && <button disabled={saving} onClick={reload}>Reload board</button>}
        </div>
        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 overflow-x-auto pb-4" aria-label="Kanban columns" tabIndex={0}>
        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          onDragCancel={() => setActiveCardId(null)}
        >
          <section className="grid gap-4 lg:min-w-[1000px] lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
                onEditCard={handleEditCard}
                disabled={saving || needsReload}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
        </div>
        <ChatSidebar disabled={saving || needsReload || activeCardId !== null} onSend={handleChat} />
        </div>
      </main>
    </div>
  );
};
