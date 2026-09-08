import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent, ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CloseIcon, PlusIcon, SendIcon } from "../components/icons";
import {
  ApiError,
  apiClient,
  type ChatSourceResult,
  type ConversationResponse,
  type MessageResponse,
  type UserResponse,
} from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import "./AiChatPage.css";

/**
 * Renders assistant message text as Markdown (bold, lists, tables via
 * GFM, etc.) — the LLM is instructed and expected to format answers
 * this way, and rendering it as plain text left literal `**`/`*`
 * markers visible in the UI. react-markdown parses to a React element
 * tree rather than an HTML string, so this is safe without
 * dangerouslySetInnerHTML even though the text is model-generated.
 * User messages stay as plain text — no reason to interpret what a
 * person typed as markup.
 */
function MarkdownContent({ text }: { text: string }) {
  return (
    <div className="aegis-chat__markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

interface AiChatPageProps {
  user: UserResponse;
}

type StreamStage = "idle" | "retrieving" | "generating";
type ConvGroup = "Today" | "Yesterday" | "Older";
const GROUPS: ConvGroup[] = ["Today", "Yesterday", "Older"];

function conversationLabel(c: ConversationResponse): string {
  return c.title?.trim() || "New conversation";
}

function groupLabel(iso: string): ConvGroup {
  const date = new Date(iso);
  const now = new Date();
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diffDays = Math.round((startOfDay(now) - startOfDay(date)) / 86_400_000);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return "Older";
}

function parseSources(json: string | null): ChatSourceResult[] {
  if (!json) return [];
  try {
    const parsed = JSON.parse(json) as { results?: ChatSourceResult[] };
    return parsed.results ?? [];
  } catch {
    return [];
  }
}

/**
 * Splits a backend-highlighted excerpt on its <mark>...</mark> spans
 * and renders each piece as either a real <mark> element or plain
 * (auto-escaped) text. Deliberately never uses dangerouslySetInnerHTML
 * — an excerpt is built from uploaded-document text, which is not
 * trusted content, and blindly injecting it as HTML would let a
 * document containing literal markup execute as real DOM (stored
 * XSS). Splitting and rendering as React children keeps every
 * character outside a well-formed <mark> pair as an inert text node.
 */
function renderHighlighted(text: string): ReactNode[] {
  const parts = text.split(/(<mark>.*?<\/mark>)/g);
  return parts.map((part, i) => {
    const match = /^<mark>([\s\S]*)<\/mark>$/.exec(part);
    return match ? <mark key={i}>{match[1]}</mark> : part;
  });
}

export function AiChatPage({ user: _user }: AiChatPageProps) {
  const auth = useAuth();
  const [conversations, setConversations] = useState<ConversationResponse[] | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageResponse[] | null>(null);
  const [draft, setDraft] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [stage, setStage] = useState<StreamStage>("idle");
  const [streamingText, setStreamingText] = useState("");
  const [streamingSources, setStreamingSources] = useState<ChatSourceResult[] | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const bootstrapped = useRef(false);

  const handleApiError = useCallback(
    (err: unknown, fallback: string): string | null => {
      if (err instanceof ApiError && err.status === 401) {
        void auth.refreshMe();
        return null;
      }
      return err instanceof ApiError ? err.detail : fallback;
    },
    [auth],
  );

  const refreshConversations = useCallback(async (): Promise<ConversationResponse[]> => {
    try {
      const list = await apiClient.listConversations();
      setConversations(list);
      setLoadError(null);
      return list;
    } catch (err) {
      const msg = handleApiError(err, "Unable to load conversations.");
      if (msg) setLoadError(msg);
      return [];
    }
  }, [handleApiError]);

  const loadMessages = useCallback(
    async (conversationId: string) => {
      try {
        const list = await apiClient.listMessages(conversationId);
        setMessages(list);
        setLoadError(null);
      } catch (err) {
        const msg = handleApiError(err, "Unable to load messages.");
        if (msg) setLoadError(msg);
      }
    },
    [handleApiError],
  );

  const selectConversation = useCallback(
    (id: string) => {
      if (stage !== "idle") return;
      setActiveId(id);
      setMessages(null);
      setStreamingSources(null);
      void loadMessages(id);
    },
    [loadMessages, stage],
  );

  const createConversation = useCallback(async () => {
    if (stage !== "idle") return;
    try {
      const conv = await apiClient.createConversation();
      setConversations((prev) => [conv, ...(prev ?? [])]);
      setActiveId(conv.id);
      setMessages([]);
      setStreamingSources(null);
    } catch (err) {
      const msg = handleApiError(err, "Unable to start a new conversation.");
      if (msg) setLoadError(msg);
    }
  }, [handleApiError, stage]);

  const deleteConversation = useCallback(
    async (id: string, e: MouseEvent) => {
      e.stopPropagation();
      if (stage !== "idle") return;
      const ok = window.confirm("Delete this conversation? This cannot be undone.");
      if (!ok) return;
      try {
        await apiClient.deleteConversation(id);
        const remaining = await refreshConversations();
        if (activeId === id) {
          if (remaining.length > 0) {
            setActiveId(remaining[0].id);
            void loadMessages(remaining[0].id);
          } else {
            setActiveId(null);
            setMessages(null);
          }
          setStreamingSources(null);
        }
      } catch (err) {
        const msg = handleApiError(err, "Unable to delete conversation.");
        if (msg) setLoadError(msg);
      }
    },
    [activeId, handleApiError, loadMessages, refreshConversations, stage],
  );

  // Bootstrap once: load conversations, select the most recent, or
  // create the first one if none exist yet so the page never lands
  // on an empty, unusable rail.
  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    void (async () => {
      const list = await refreshConversations();
      if (list.length > 0) {
        setActiveId(list[0].id);
        void loadMessages(list[0].id);
      } else {
        await createConversation();
      }
    })();
    // Intentionally run once on mount only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, streamingText]);

  const handleSend = useCallback(async () => {
    const text = draft.trim();
    if (!text || !activeId || stage !== "idle") return;
    setDraft("");
    setLoadError(null);

    // Optimistic local echo — the server persists this immediately
    // too, but waiting for a refetch before showing it would make
    // sending feel laggy. Replaced by the canonical list once the
    // stream finishes.
    const optimisticUser: MessageResponse = {
      id: `local-${Date.now()}`,
      conversation_id: activeId,
      role: "user",
      content: text,
      sources_json: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...(prev ?? []), optimisticUser]);
    setStreamingText("");
    setStreamingSources(null);
    setStage("retrieving");

    try {
      for await (const evt of apiClient.sendMessage(activeId, text)) {
        if (evt.event === "sources") {
          setStreamingSources(evt.data.results);
          setStage("generating");
        } else if (evt.event === "token") {
          setStreamingText((prev) => prev + evt.data.text);
        } else if (evt.event === "error") {
          setLoadError(evt.data.message);
        }
      }
    } catch (err) {
      const msg = handleApiError(err, "Unable to send message.");
      if (msg) setLoadError(msg);
    } finally {
      setStage("idle");
      setStreamingText("");
      await loadMessages(activeId);
      void refreshConversations();
    }
  }, [draft, activeId, stage, handleApiError, loadMessages, refreshConversations]);

  const activeConversation = conversations?.find((c) => c.id === activeId) ?? null;

  const lastAssistantSources = useMemo(() => {
    if (streamingSources) return streamingSources;
    if (!messages) return [];
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "assistant") return parseSources(messages[i].sources_json);
    }
    return [];
  }, [messages, streamingSources]);

  const groupedConversations = useMemo(() => {
    const groups: Record<ConvGroup, ConversationResponse[]> = {
      Today: [],
      Yesterday: [],
      Older: [],
    };
    for (const c of conversations ?? []) {
      groups[groupLabel(c.updated_at)].push(c);
    }
    return groups;
  }, [conversations]);

  return (
    <div className="aegis-chat">
      <aside className="aegis-chat__rail">
        <button
          type="button"
          className="aegis-chat__new-btn"
          onClick={() => void createConversation()}
          disabled={stage !== "idle"}
        >
          <PlusIcon /> New Chat
        </button>
        <div className="aegis-chat__conv-list">
          {conversations === null && (
            <div className="aegis-chat__empty-state aegis-chat__empty-state--compact">
              Loading conversations…
            </div>
          )}
          {GROUPS.map((group) => {
            const items = groupedConversations[group];
            if (items.length === 0) return null;
            return (
              <div key={group} className="aegis-chat__conv-group">
                <div className="aegis-chat__conv-group-label">{group}</div>
                {items.map((c) => (
                  <div key={c.id} className="aegis-chat__conv-item-row">
                    <button
                      type="button"
                      className={`aegis-chat__conv-item ${
                        c.id === activeId ? "aegis-chat__conv-item--active" : ""
                      }`}
                      onClick={() => selectConversation(c.id)}
                    >
                      {conversationLabel(c)}
                    </button>
                    <button
                      type="button"
                      className="aegis-chat__conv-delete"
                      aria-label="Delete conversation"
                      onClick={(e) => void deleteConversation(c.id, e)}
                    >
                      <CloseIcon />
                    </button>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </aside>

      <section className="aegis-chat__thread">
        <div className="aegis-chat__thread-header">
          <h1>{activeConversation ? conversationLabel(activeConversation) : "Aegis AI"}</h1>
        </div>

        {loadError && (
          <div className="aegis-banner aegis-banner--error" role="alert">
            {loadError}
            <button
              type="button"
              className="aegis-banner-dismiss"
              onClick={() => setLoadError(null)}
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        )}

        <div className="aegis-chat__messages">
          {messages === null && activeId && (
            <div className="aegis-chat__empty-state">Loading messages…</div>
          )}
          {messages !== null && messages.length === 0 && stage === "idle" && (
            <div className="aegis-chat__empty-state">
              Ask anything about your organisation's knowledge base to get started.
            </div>
          )}
          {(messages ?? []).map((m) => (
            <div key={m.id} className={`aegis-chat__msg aegis-chat__msg--${m.role}`}>
              <div className="aegis-chat__msg-avatar" aria-hidden="true">
                {m.role === "user" ? "You" : "AI"}
              </div>
              <div className="aegis-chat__msg-body">
                {m.role === "assistant" ? (
                  <MarkdownContent text={m.content} />
                ) : (
                  <p>{m.content}</p>
                )}
              </div>
            </div>
          ))}
          {stage !== "idle" && (
            <div className="aegis-chat__msg aegis-chat__msg--assistant">
              <div className="aegis-chat__msg-avatar" aria-hidden="true">
                AI
              </div>
              <div className="aegis-chat__msg-body">
                {streamingText ? (
                  <MarkdownContent text={streamingText} />
                ) : (
                  <span className="aegis-chat__typing" aria-label="Aegis AI is responding">
                    <span />
                    <span />
                    <span />
                  </span>
                )}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="aegis-chat__status-row">
          {stage === "retrieving" && "Searching the knowledge base…"}
          {stage === "generating" && "Generating…"}
        </div>

        <form
          className="aegis-chat__input-bar"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSend();
          }}
        >
          <input
            type="text"
            placeholder="Ask anything..."
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={!activeId || stage !== "idle"}
          />
          <button
            type="submit"
            className="aegis-chat__send-btn"
            aria-label="Send"
            disabled={!draft.trim() || !activeId || stage !== "idle"}
          >
            <SendIcon />
          </button>
        </form>
        <p className="aegis-chat__disclaimer">
          Aegis AI makes mistakes. Please verify important information.
        </p>
      </section>

      <aside className="aegis-chat__details">
        <div className="aegis-chat__details-header">
          <h2>Sources</h2>
          <span className="aegis-chat__details-count">{lastAssistantSources.length}</span>
        </div>
        {lastAssistantSources.length === 0 ? (
          <div className="aegis-chat__empty-state aegis-chat__empty-state--compact">
            Sources for the assistant's answer will appear here.
          </div>
        ) : (
          <div className="aegis-chat__source-list">
            {lastAssistantSources.map((s, i) => (
              <div
                className="aegis-chat__source-card"
                key={`${s.document_id}-${s.chunk_index}-${i}`}
              >
                <div className="aegis-chat__source-card-header">
                  <span className="aegis-ext-badge">
                    {s.filename.split(".").pop()?.toUpperCase() ?? "DOC"}
                  </span>
                  <span className="aegis-chat__source-card-name">{s.filename}</span>
                </div>
                {s.page_number != null && (
                  <div className="aegis-chat__source-card-meta">
                    <span>Page {s.page_number}</span>
                  </div>
                )}
                <p className="aegis-chat__source-card-excerpt">
                  {renderHighlighted(s.excerpt)}
                </p>
              </div>
            ))}
          </div>
        )}
      </aside>
    </div>
  );
}
