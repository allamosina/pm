import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  disabled: boolean;
  onEdit: (cardId: string, title: string, details: string) => Promise<boolean>;
  onDelete: (cardId: string) => Promise<boolean>;
};

export const KanbanCard = ({ card, onDelete, onEdit, disabled }: KanbanCardProps) => {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id, disabled: disabled || editing });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      data-testid={`card-${card.id}`}
    >
      {editing ? <form onSubmit={async event => {
        event.preventDefault();
        if (title.trim() && await onEdit(card.id, title.trim(), details)) setEditing(false);
      }}>
        <fieldset disabled={disabled} className="space-y-3">
          <label className="block text-sm">Card title<input autoFocus required maxLength={200} value={title} onChange={event => setTitle(event.target.value)} className="mt-1 w-full rounded-lg border border-[var(--stroke)] p-2" /></label>
          <label className="block text-sm">Details<textarea maxLength={10000} value={details} onChange={event => setDetails(event.target.value)} rows={4} className="mt-1 w-full rounded-lg border border-[var(--stroke)] p-2" /></label>
          <div className="flex gap-3 text-xs"><button type="submit" disabled={!title.trim()} className="rounded-full bg-[var(--secondary-purple)] px-3 py-2 text-white">Save card</button><button type="button" onClick={() => setEditing(false)}>Cancel</button></div>
        </fieldset>
      </form> : <>
      <div ref={setActivatorNodeRef} {...attributes} {...listeners} aria-label={`Move ${card.title}`} className="cursor-grab touch-none break-words">

        <div>
          <h4 className="font-display text-base font-semibold text-[var(--navy-dark)]">
            {card.title}
          </h4>
          <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
            {card.details}
          </p>
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <button type="button" disabled={disabled} onClick={() => { setTitle(card.title); setDetails(card.details); setEditing(true); }} aria-label={`Edit ${card.title}`} className="px-2 py-1 text-xs font-semibold text-[var(--secondary-purple)]">Edit</button>
        <button
          disabled={disabled}
          type="button"
          onClick={() => onDelete(card.id)}
          className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
          aria-label={`Delete ${card.title}`}
        >
          Remove
        </button>
      </div>
      </>}
    </article>
  );
};
