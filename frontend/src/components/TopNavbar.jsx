import React from 'react';
import { Link2, Cpu, ExternalLink, Clock } from 'lucide-react';

const LANGS = [
  { code: 'ko', label: '한국어' },
  { code: 'zh', label: '中文' },
  { code: 'en', label: 'EN' },
];

export default function TopNavbar({
  t,
  lang,
  setLang,
  stats,
  groqStatus,
  onOpenUrlModal,
  onOpenGroqModal,
}) {
  return (
    <header className="z-30 flex h-14 shrink-0 items-center justify-between gap-4 border-b border-line bg-white px-5">
      {/* Brand */}
      <div className="flex min-w-0 items-center gap-3">
        <div className="grid h-7 w-7 shrink-0 place-items-center rounded-[9px] bg-ink text-[13px] font-bold tracking-tighter text-white">
          Z
        </div>
        <div className="min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-title font-semibold tracking-tight text-ink">
              {t.brandName}
            </span>
            <span className="hidden truncate text-meta text-faint lg:inline">
              {t.brandSub}
            </span>
          </div>
        </div>

        <span className="hidden h-4 w-px bg-line md:block" />

        <a
          href="https://kangwon.ac.kr/ko/bbs/721/list.do"
          target="_blank"
          rel="noreferrer"
          className="hidden min-w-0 items-center gap-1.5 text-meta text-muted transition hover:text-ink md:flex"
        >
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
          <span className="max-w-[200px] truncate">{t.liveSynced}</span>
          <ExternalLink className="h-3 w-3 shrink-0 opacity-50" />
        </a>
      </div>

      {/* Controls */}
      <div className="flex shrink-0 items-center gap-1.5">
        {stats && (
          <div className="mr-1 hidden items-center gap-1.5 rounded-control bg-canvas px-2.5 py-1.5 text-meta tabular-nums text-muted ring-1 ring-line/70 xl:flex">
            <Clock className="h-3.5 w-3.5 text-faint" />
            <span className="whitespace-nowrap">
              {t.savedTimeCompact(stats.total, stats.saved_minutes)}
            </span>
          </div>
        )}

        <button
          onClick={onOpenUrlModal}
          className="inline-flex h-8 items-center gap-1.5 rounded-control bg-ink px-3 text-label font-medium text-white transition hover:bg-ink/90"
        >
          <Link2 className="h-3.5 w-3.5" />
          <span>{t.btnParseUrl}</span>
        </button>

        <button
          onClick={onOpenGroqModal}
          title={t.btnGroq}
          aria-label={t.btnGroq}
          className="inline-flex h-8 items-center gap-1.5 rounded-control px-2.5 text-label font-medium text-muted ring-1 ring-line transition hover:text-ink hover:ring-ink/25"
        >
          <Cpu className="h-3.5 w-3.5" />
          <span>Groq</span>
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: groqStatus?.configured ? '#10b981' : '#d4d4d8' }}
          />
        </button>

        <div className="seg ml-1">
          {LANGS.map((item) => (
            <button
              key={item.code}
              onClick={() => setLang(item.code)}
              className={`${lang === item.code ? 'seg-item seg-item-active' : 'seg-item hover:text-ink'}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
