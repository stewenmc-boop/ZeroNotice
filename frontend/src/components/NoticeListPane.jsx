import React, { useState } from 'react';
import { Search, X, Bookmark, FileText, Clock, Link2, Bell } from 'lucide-react';

const STATUS = {
  eligible: { dot: 'bg-emerald-500', text: 'text-emerald-700', key: 'badgeEligible' },
  conditional: { dot: 'bg-amber-500', text: 'text-amber-700', key: 'badgeCond' },
  ineligible: { dot: 'bg-zinc-300', text: 'text-faint', key: 'badgeIneligible' },
};

export default function NoticeListPane({
  t,
  lang,
  notices,
  selectedId,
  onSelect,
  searchQuery,
  setSearchQuery,
  savedIds,
  onToggleSave,
  onToggleSubscribe,
  progressMap,
}) {
  const [subFilter, setSubFilter] = useState('ALL'); // ALL | ELIGIBLE | HWP

  const filteredNotices = notices.filter((n) => {
    if (subFilter === 'ELIGIBLE' && n.match_status === 'ineligible') return false;
    if (subFilter === 'HWP' && !n.attachment_extracted_text) return false;
    if (subFilter === 'LINK' && !n.has_application_link) return false;
    return true;
  });

  return (
    <section className="flex w-[340px] shrink-0 flex-col border-r border-line bg-canvas xl:w-[420px]">
      {/* Search + filters */}
      <div className="space-y-3 border-b border-line bg-white px-4 pb-3 pt-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.searchPlaceholder}
            className="h-9 w-full rounded-control bg-canvas pl-9 pr-8 text-label text-ink ring-1 ring-line transition placeholder:text-faint focus:bg-white focus:outline-none focus:ring-ink/30"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-faint transition hover:text-ink"
              aria-label="clear"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <div className="flex items-center justify-between">
          <div className="inline-flex items-center gap-0.5">
            {[
              { key: 'ALL', label: t.filterAll },
              { key: 'LINK', label: t.filterLink },
              { key: 'ELIGIBLE', label: t.filterEligible },
              { key: 'HWP', label: t.filterHwp },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setSubFilter(tab.key)}
                className={`h-7 rounded-chip px-2 text-meta font-medium transition ${
                  subFilter === tab.key
                    ? 'bg-ink text-white'
                    : 'text-muted hover:bg-accent-soft hover:text-ink'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <span className="text-meta tabular-nums text-faint">{filteredNotices.length}</span>
        </div>
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto">
        {filteredNotices.length === 0 ? (
          <div className="p-12 text-center text-label text-faint">{t.emptyList}</div>
        ) : (
          filteredNotices.map((n) => {
            const title = n[`title_${lang}`] || n.title_ko || n.title;
            const summary = n[`summary_${lang}`] || n.summary_ko || '';
            const benefit = n[`benefit_label_${lang}`] || n.benefit_label_ko || '';
            const isSelected = n.id === selectedId;
            const isSaved = savedIds.includes(n.id);
            const prog = progressMap[n.id] || 'none';
            const hasHwpText = Boolean(n.attachment_extracted_text);
            const status = STATUS[n.match_status] || STATUS.ineligible;

            return (
              <article
                key={n.id}
                onClick={() => onSelect(n.id)}
                className={`group relative cursor-pointer border-b border-line px-4 py-3.5 transition ${
                  isSelected ? 'bg-white' : 'hover:bg-white/70'
                } ${n.match_status === 'ineligible' ? 'opacity-70' : ''}`}
              >
                {isSelected && (
                  <span className="absolute inset-y-0 left-0 w-[2px] bg-ink" />
                )}

                {/* meta row */}
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-1.5 text-meta">
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${status.dot}`} />
                    <span className={`font-medium ${status.text}`}>{t[status.key]}</span>
                    <span className="text-line">|</span>
                    <span className="truncate text-faint">{n.category}</span>
                    {n.has_application_link && (
                      <span
                        title={t.hasLink}
                        className="inline-flex shrink-0 items-center gap-0.5 rounded-[5px] bg-emerald-50 px-1 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-emerald-100"
                      >
                        <Link2 className="h-2.5 w-2.5" />
                        {t.hasLink}
                      </span>
                    )}
                    {hasHwpText && (
                      <span
                        title={t.badgeHwp}
                        className="inline-flex shrink-0 items-center gap-0.5 rounded-[5px] bg-accent-soft px-1 py-0.5 text-[10px] font-medium text-muted ring-1 ring-line"
                      >
                        <FileText className="h-2.5 w-2.5" />
                        HWP
                      </span>
                    )}
                  </div>

                  <div className="flex shrink-0 items-center gap-1">
                    <span
                      className={`text-meta font-semibold tabular-nums ${
                        n.d_day === '마감' ? 'text-faint' : 'text-ink'
                      }`}
                    >
                      {n.d_day}
                    </span>
                    <button
                      type="button"
                      title={t.subTitle}
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleSubscribe(n.id);
                      }}
                      className={`grid h-6 w-6 place-items-center rounded-md transition hover:bg-accent-soft ${
                        n.subscribed ? 'text-ink' : 'text-faint opacity-0 group-hover:opacity-100'
                      }`}
                    >
                      <Bell className="h-3.5 w-3.5" fill={n.subscribed ? 'currentColor' : 'none'} />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleSave(n.id);
                      }}
                      className={`grid h-6 w-6 place-items-center rounded-md transition hover:bg-accent-soft ${
                        isSaved ? 'text-ink' : 'text-faint opacity-0 group-hover:opacity-100'
                      }`}
                      title="Bookmark"
                    >
                      <Bookmark
                        className="h-3.5 w-3.5"
                        fill={isSaved ? 'currentColor' : 'none'}
                      />
                    </button>
                  </div>
                </div>

                {/* title */}
                <h3
                  className={`mb-1 line-clamp-2 text-[13.5px] leading-[1.45] tracking-[-0.01em] ${
                    isSelected ? 'font-semibold text-ink' : 'font-medium text-ink/90'
                  }`}
                >
                  {title}
                </h3>

                {/* summary */}
                {summary && (
                  <p className="mb-2 line-clamp-1 text-label leading-5 text-muted">{summary}</p>
                )}

                {/* footer */}
                <div className="flex items-center gap-2 text-meta">
                  <span className="truncate font-medium text-muted">{benefit}</span>
                  <span className="ml-auto flex shrink-0 items-center gap-2 text-faint">
                    {prog !== 'none' && (
                      <span
                        className={`rounded-[5px] px-1.5 py-0.5 text-[10px] font-medium ${
                          prog === 'done'
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-amber-50 text-amber-700'
                        }`}
                      >
                        {prog === 'done' ? t.progDone : t.progPrep}
                      </span>
                    )}
                    <span className="max-w-[92px] truncate">{n.author}</span>
                    <span className="inline-flex items-center gap-0.5 tabular-nums">
                      <Clock className="h-2.5 w-2.5" />
                      {n.saved_minutes}m
                    </span>
                  </span>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
