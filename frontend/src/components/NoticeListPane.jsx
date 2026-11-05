import React, { useState } from 'react';
import {
  Search,
  X,
  Bookmark,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  MinusCircle,
} from 'lucide-react';

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
  progressMap,
}) {
  const [subFilter, setSubFilter] = useState('ALL'); // ALL | ELIGIBLE | HWP

  const filteredNotices = notices.filter((n) => {
    if (subFilter === 'ELIGIBLE' && n.match_status === 'ineligible') return false;
    if (subFilter === 'HWP' && !n.attachment_extracted_text) return false;
    return true;
  });

  const renderStatusBadge = (notice) => {
    if (notice.match_status === 'eligible') {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80">
          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
          <span>{t.badgeEligible}</span>
        </span>
      );
    }
    if (notice.match_status === 'conditional') {
      return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200/80">
          <AlertCircle className="w-3 h-3 text-amber-600" />
          <span>{t.badgeCond}</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium bg-zinc-100 text-zinc-500">
        <MinusCircle className="w-3 h-3 text-zinc-400" />
        <span>{t.badgeIneligible}</span>
      </span>
    );
  };

  return (
    <section className="w-full md:w-[410px] xl:w-[450px] border-r border-zinc-200 bg-white flex flex-col shrink-0">
      {/* Search & Sub-filter Header */}
      <div className="p-3 border-b border-zinc-200 space-y-2.5">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t.searchPlaceholder}
            className="w-full pl-8 pr-8 py-1.5 rounded-lg bg-zinc-100/80 border border-transparent focus:bg-white focus:border-zinc-900 text-xs text-zinc-900 placeholder:text-zinc-400 focus:outline-none transition"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Sub-filter Pills */}
        <div className="flex items-center justify-between">
          <div className="inline-flex items-center gap-1">
            {[
              { key: 'ALL', label: t.filterAll },
              { key: 'ELIGIBLE', label: t.filterEligible },
              { key: 'HWP', label: t.filterHwp },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setSubFilter(tab.key)}
                className={`px-2 py-1 rounded-md text-[11px] font-medium transition ${
                  subFilter === tab.key
                    ? 'bg-zinc-900 text-white'
                    : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <span className="text-[11px] text-zinc-400 tabular-nums">
            {filteredNotices.length}
          </span>
        </div>
      </div>

      {/* Notice Feed List */}
      <div className="flex-1 overflow-y-auto divide-y divide-zinc-100">
        {filteredNotices.length === 0 ? (
          <div className="p-12 text-center text-xs text-zinc-400">
            {t.emptyList}
          </div>
        ) : (
          filteredNotices.map((n) => {
            const title = n[`title_${lang}`] || n.title_ko || n.title;
            const summary = n[`summary_${lang}`] || n.summary_ko || '';
            const benefit = n[`benefit_label_${lang}`] || n.benefit_label_ko || '';
            const isSelected = n.id === selectedId;
            const isSaved = savedIds.includes(n.id);
            const prog = progressMap[n.id] || 'none';
            const hasHwpText = Boolean(n.attachment_extracted_text);

            return (
              <div
                key={n.id}
                onClick={() => onSelect(n.id)}
                className={`p-3.5 cursor-pointer transition relative group ${
                  isSelected
                    ? 'bg-zinc-900/[0.04]'
                    : 'hover:bg-zinc-50'
                } ${n.match_status === 'ineligible' ? 'opacity-60' : ''}`}
              >
                {/* Left Active Indicator Bar */}
                {isSelected && (
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-zinc-950" />
                )}

                {/* Top Meta Row */}
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {renderStatusBadge(n)}
                    <span className="px-1.5 py-0.5 rounded text-[11px] font-medium bg-zinc-100 text-zinc-700">
                      {n.category}
                    </span>
                    {hasHwpText && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-zinc-900 text-white">
                        <FileText className="w-2.5 h-2.5" />
                        <span>{t.badgeHwp}</span>
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[11px] font-semibold text-zinc-700 tabular-nums">
                      {n.d_day}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleSave(n.id);
                      }}
                      className={`p-1 rounded hover:bg-zinc-200/70 transition ${
                        isSaved
                          ? 'text-zinc-950'
                          : 'text-zinc-300 opacity-0 group-hover:opacity-100'
                      }`}
                      title="Bookmark"
                    >
                      <Bookmark
                        className="w-3.5 h-3.5"
                        fill={isSaved ? 'currentColor' : 'none'}
                      />
                    </button>
                  </div>
                </div>

                {/* Title */}
                <h3 className="text-[13px] font-semibold text-zinc-950 leading-snug line-clamp-2 mb-1">
                  {title}
                </h3>

                {/* Summary */}
                <p className="text-xs text-zinc-500 line-clamp-2 leading-relaxed mb-2">
                  {summary}
                </p>

                {/* Bottom Row */}
                <div className="flex items-center justify-between text-[11px] text-zinc-400">
                  <span className="truncate font-medium text-zinc-600 max-w-[210px]">
                    {benefit}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    {prog !== 'none' && (
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          prog === 'done'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {prog === 'done' ? t.progDone : t.progPrep}
                      </span>
                    )}
                    <span>{n.author}</span>
                    <span className="inline-flex items-center gap-0.5 tabular-nums">
                      <Clock className="w-3 h-3" />
                      {n.saved_minutes}m
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

