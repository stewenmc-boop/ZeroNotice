import React, { useEffect, useRef, useState } from 'react';
import { Sparkles, X, Send, Bell, Search, CalendarClock, Loader2 } from 'lucide-react';

const GREETING = {
  ko: '안녕하세요! 공지 검색, 마감 확인, 구독, 문의 메일까지 대신해 드려요.',
  zh: '你好！我可以帮你找公告、查截止、订阅提醒、写并发送咨询邮件。',
  en: 'Hi! I can search notices, check deadlines, subscribe you, and send inquiry e-mails.',
};

const CHIPS = {
  ko: ['이번 주 마감 공지', '내가 지원 가능한 공모전', '관심 공지 구독 확인'],
  zh: ['本周截止的公告', '我能申请的竞赛', '查看我的订阅'],
  en: ['Deadlines this week', 'Competitions I qualify for', 'My subscriptions'],
};

export default function AssistantDock({ lang = 'ko', onOpenNotice }) {
  const [open, setOpen] = useState(
    () => new URLSearchParams(window.location.search).get('chat') === '1'
  );
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [tools, setTools] = useState([]);
  const listRef = useRef(null);
  const t = (GREETING[lang] ? lang : 'ko');

  useEffect(() => {
    if (!open) return;
    fetch('/api/assistant/history?limit=20')
      .then((r) => r.json())
      .then((d) => {
        const history = (d.messages || []).map((m) => ({ role: m.role, content: m.content }));
        setMessages(history.length ? history : [{ role: 'assistant', content: GREETING[t] }]);
      })
      .catch(() => setMessages([{ role: 'assistant', content: GREETING[t] }]));
  }, [open, t]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, busy]);

  const send = async (text) => {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    const next = [...messages, { role: 'user', content }];
    setMessages(next);
    setInput('');
    setBusy(true);
    setTools([]);
    try {
      const res = await fetch('/api/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: next.filter((m) => m.role !== 'system').slice(-10),
          lang,
        }),
      });
      const data = await res.json();
      setTools(data.tool_calls || []);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.reply || data.error || '...' },
      ]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: String(err) }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {/* floating ball */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-40 grid h-14 w-14 place-items-center rounded-full bg-ink text-white shadow-pop transition hover:scale-105 active:scale-95"
          title="ZeroNotice AI"
        >
          <Sparkles className="h-6 w-6" />
          <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full bg-emerald-400 ring-2 ring-white" />
        </button>
      )}

      {open && (
        <section className="fixed bottom-6 right-6 z-40 flex h-[560px] w-[380px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-card border border-line bg-white shadow-pop">
          <header className="flex items-center justify-between border-b border-line px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-ink text-white">
                <Sparkles className="h-3.5 w-3.5" />
              </span>
              <div>
                <div className="text-title font-semibold text-ink">ZeroNotice AI</div>
                <div className="text-meta text-faint">공지·마감·구독·메일</div>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="rounded-control p-1 text-faint hover:text-ink">
              <X className="h-4 w-4" />
            </button>
          </header>

          <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto bg-canvas px-3 py-3">
            {messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                <div
                  className={`max-w-[86%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-body leading-6 ${
                    m.role === 'user'
                      ? 'bg-ink text-white'
                      : 'bg-white text-zinc-800 ring-1 ring-line'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex items-center gap-2 text-meta text-faint">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                생각 중…
              </div>
            )}
            {!busy && tools.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tools.map((tool, i) => (
                  <span key={i} className="rounded-chip bg-accent-soft px-1.5 py-0.5 text-[10px] text-muted">
                    {tool.name}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-line bg-white px-3 py-2">
            <div className="mb-2 flex gap-1 overflow-x-auto pb-1">
              {CHIPS[t].map((chip) => (
                <button
                  key={chip}
                  onClick={() => send(chip)}
                  className="shrink-0 rounded-chip bg-accent-soft px-2 py-1 text-meta text-muted hover:text-ink"
                >
                  {chip}
                </button>
              ))}
            </div>
            <div className="flex items-end gap-2">
              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                placeholder={GREETING[t]}
                className="max-h-24 flex-1 resize-none rounded-control border border-line px-3 py-2 text-label text-ink placeholder:text-faint focus:border-ink/40 focus:outline-none"
              />
              <button
                onClick={() => send()}
                disabled={busy || !input.trim()}
                className="grid h-9 w-9 shrink-0 place-items-center rounded-control bg-ink text-white disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
