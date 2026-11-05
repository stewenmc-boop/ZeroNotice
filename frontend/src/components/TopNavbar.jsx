import React from 'react';
import { Link2, Cpu, Clock, ExternalLink } from 'lucide-react';

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
    <header className="h-12 border-b border-zinc-200 bg-white px-4 flex items-center justify-between shrink-0 z-30">
      {/* Left Brand */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-zinc-950 text-white text-xs font-bold flex items-center justify-center tracking-tighter">
            Z
          </div>
          <span className="font-semibold text-sm text-zinc-950 tracking-tight">
            {t.brandName}
          </span>
          <span className="text-xs text-zinc-400 hidden sm:inline">
            {t.brandSub}
          </span>
        </div>

        <span className="text-zinc-200 hidden md:inline">|</span>

        <a
          href="https://kangwon.ac.kr/ko/bbs/721/list.do"
          target="_blank"
          rel="noreferrer"
          className="hidden md:inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-950 transition"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>{t.liveSynced}</span>
          <ExternalLink className="w-3 h-3 opacity-60" />
        </a>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2">
        {/* Saved Time Counter */}
        {stats && (
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-100 text-xs text-zinc-600 tabular-nums">
            <Clock className="w-3.5 h-3.5 text-zinc-400" />
            <span>
              {t.savedTimeBadge(stats.total, stats.hwp_parsed_count, stats.saved_minutes)}
            </span>
          </div>
        )}

        {/* Live URL / HWP Parser Trigger */}
        <button
          onClick={onOpenUrlModal}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-zinc-200 hover:border-zinc-900 text-xs font-medium text-zinc-700 hover:text-zinc-950 transition"
        >
          <Link2 className="w-3.5 h-3.5" />
          <span>{t.btnParseUrl}</span>
        </button>

        {/* Groq API Config Trigger */}
        <button
          onClick={onOpenGroqModal}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-zinc-200 hover:border-zinc-900 text-xs font-medium text-zinc-700 hover:text-zinc-950 transition"
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              groqStatus?.configured ? 'bg-emerald-500' : 'bg-zinc-400'
            }`}
          />
          <Cpu className="w-3.5 h-3.5" />
          <span>{t.btnGroq}</span>
        </button>

        {/* Language Segmented Switcher */}
        <div className="inline-flex bg-zinc-100 p-0.5 rounded-md border border-zinc-200/70 text-[11px]">
          {[
            { code: 'ko', label: '한국어' },
            { code: 'zh', label: '中文' },
            { code: 'en', label: 'EN' },
          ].map((item) => (
            <button
              key={item.code}
              onClick={() => setLang(item.code)}
              className={`px-2 py-0.5 rounded font-medium transition ${
                lang === item.code
                  ? 'bg-white text-zinc-950 shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}

