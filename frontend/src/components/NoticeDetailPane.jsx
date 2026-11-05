import React, { useState, useEffect } from 'react';
import {
  ExternalLink,
  Bookmark,
  Calendar,
  Mail,
  FileEdit,
  FileText,
  Download,
  Copy,
  Check,
  Send,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  MinusCircle,
  Phone,
  Building2,
  Search,
} from 'lucide-react';

export default function NoticeDetailPane({
  t,
  lang,
  notice,
  profile,
  isSaved,
  onToggleSave,
  progress,
  onChangeProgress,
}) {
  const [activeTab, setActiveTab] = useState('summary'); // summary | agent | hwp | original
  const [emailQuestion, setEmailQuestion] = useState('');
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailResult, setEmailResult] = useState(null);
  const [emailCopied, setEmailCopied] = useState(false);

  const [appLoading, setAppLoading] = useState(false);
  const [appResult, setAppResult] = useState(null);
  const [appCopied, setAppCopied] = useState(false);

  const [hwpKeyword, setHwpKeyword] = useState('');

  // Reset generated states when switching notices
  useEffect(() => {
    setEmailResult(null);
    setAppResult(null);
    setEmailQuestion('');
    setHwpKeyword('');
    setActiveTab('summary');
  }, [notice?.id]);

  if (!notice) {
    return (
      <main className="flex-1 bg-zinc-50/40 flex items-center justify-center p-8 text-xs text-zinc-400">
        {t.emptyList}
      </main>
    );
  }

  const title = notice[`title_${lang}`] || notice.title_ko || notice.title;
  const summary = notice[`summary_${lang}`] || notice.summary_ko || '';
  const benefit = notice[`benefit_label_${lang}`] || notice.benefit_label_ko || '';
  const verdict = notice[`verdict_${lang}`] || notice.verdict_ko || '';
  const attachments = notice.attachments || [];
  const extractedHwp = notice.attachment_extracted_text || '';

  const handleDownloadIcs = () => {
    window.open(
      `/api/agent/ics/${encodeURIComponent(notice.id)}?lang=${encodeURIComponent(lang)}`,
      '_blank'
    );
  };

  const handleGenerateEmail = async (overrideQuestion) => {
    const q = overrideQuestion !== undefined ? overrideQuestion : emailQuestion;
    setEmailLoading(true);
    try {
      const res = await fetch('/api/agent/email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          notice_id: notice.id,
          profile,
          custom_question: q,
          lang,
        }),
      });
      const data = await res.json();
      setEmailResult(data);
    } catch (err) {
      console.error('Failed to generate email:', err);
    } finally {
      setEmailLoading(false);
    }
  };

  const handleGenerateApp = async () => {
    setAppLoading(true);
    try {
      const res = await fetch('/api/agent/application', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          notice_id: notice.id,
          profile,
          lang,
        }),
      });
      const data = await res.json();
      setAppResult(data);
    } catch (err) {
      console.error('Failed to generate application draft:', err);
    } finally {
      setAppLoading(false);
    }
  };

  const copyText = (text, setFlag) => {
    navigator.clipboard.writeText(text || '');
    setFlag(true);
    setTimeout(() => setFlag(false), 1800);
  };

  const downloadTxtFile = (filename, content) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const renderHighlightedText = (rawText, keyword) => {
    if (!keyword.trim()) return rawText;
    const parts = rawText.split(new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, idx) =>
      part.toLowerCase() === keyword.toLowerCase() ? (
        <mark key={idx} className="bg-amber-200 text-zinc-950 px-0.5 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <main className="flex-1 bg-white overflow-y-auto flex flex-col">
      {/* Top Sticky Detail Header */}
      <div className="border-b border-zinc-200 px-6 pt-5 pb-0 bg-white sticky top-0 z-20">
        {/* Top Meta Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <span className="px-2 py-0.5 rounded bg-zinc-900 text-white font-medium text-[11px]">
              {notice.category}
            </span>
            <span>·</span>
            <span className="font-medium text-zinc-800">{notice.author}</span>
            <span>·</span>
            <span>
              {t.postedOn} {notice.posted_date}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Personal Application Status Selector */}
            <div className="inline-flex items-center bg-zinc-100 p-0.5 rounded-lg border border-zinc-200 text-[11px]">
              {[
                { key: 'none', label: t.progNone },
                { key: 'prep', label: t.progPrep },
                { key: 'done', label: t.progDone },
              ].map((st) => (
                <button
                  key={st.key}
                  onClick={() => onChangeProgress(notice.id, st.key)}
                  className={`px-2 py-1 rounded-md font-medium transition ${
                    progress === st.key
                      ? 'bg-white text-zinc-950 shadow-xs'
                      : 'text-zinc-500 hover:text-zinc-900'
                  }`}
                >
                  {st.label}
                </button>
              ))}
            </div>

            {/* Bookmark Button */}
            <button
              onClick={() => onToggleSave(notice.id)}
              className={`p-1.5 rounded-lg border transition ${
                isSaved
                  ? 'border-zinc-900 bg-zinc-900 text-white'
                  : 'border-zinc-200 text-zinc-600 hover:border-zinc-900'
              }`}
              title="Bookmark"
            >
              <Bookmark className="w-3.5 h-3.5" fill={isSaved ? 'currentColor' : 'none'} />
            </button>

            {/* Open Original KNU Link */}
            <a
              href={notice.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-zinc-200 hover:border-zinc-900 text-xs font-medium text-zinc-700 hover:text-zinc-950 transition"
            >
              <span>{t.openOriginal}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>

        {/* Notice Title */}
        <h1 className="text-lg font-bold text-zinc-950 tracking-tight leading-snug mb-4">
          {title}
        </h1>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 border-t border-zinc-100 pt-1 -mb-px overflow-x-auto">
          {[
            { key: 'summary', label: t.tabSummary, icon: Sparkles },
            { key: 'agent', label: t.tabAgent, icon: Mail },
            {
              key: 'hwp',
              label: `${t.tabHwp} (${attachments.length})`,
              icon: FileText,
            },
            { key: 'original', label: t.tabOriginal, icon: FileEdit },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex items-center gap-1.5 px-3 py-2.5 border-b-2 text-xs font-semibold whitespace-nowrap transition ${
                  active
                    ? 'border-zinc-950 text-zinc-950'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content Area */}
      <div className="p-6 max-w-4xl space-y-6">
        {/* TAB 1: AI SUMMARY & ELIGIBILITY VERDICT */}
        {activeTab === 'summary' && (
          <>
            {/* Eligibility Verdict Card */}
            <div
              className={`p-4 rounded-xl border flex items-start justify-between gap-4 ${
                notice.match_status === 'eligible'
                  ? 'bg-emerald-50/60 border-emerald-200'
                  : notice.match_status === 'conditional'
                  ? 'bg-amber-50/60 border-amber-200'
                  : 'bg-zinc-100 border-zinc-200'
              }`}
            >
              <div className="flex items-start gap-3">
                {notice.match_status === 'eligible' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                ) : notice.match_status === 'conditional' ? (
                  <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                ) : (
                  <MinusCircle className="w-5 h-5 text-zinc-500 shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 mb-0.5">
                    {t.verdictTitle}
                  </div>
                  <div className="text-sm font-bold text-zinc-950">{verdict}</div>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-white border border-zinc-200 text-zinc-800 shrink-0 tabular-nums">
                {notice.d_day}
              </span>
            </div>

            {/* Key Facts 3-Col Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3.5 rounded-xl border border-zinc-200 bg-zinc-50/50">
                <div className="text-[11px] text-zinc-400 mb-1">{t.benefitLabel}</div>
                <div className="text-xs font-semibold text-zinc-950 leading-snug">
                  {benefit}
                </div>
              </div>
              <div className="p-3.5 rounded-xl border border-zinc-200 bg-zinc-50/50">
                <div className="text-[11px] text-zinc-400 mb-1">{t.deadlineLabel}</div>
                <div className="text-xs font-semibold text-zinc-950 tabular-nums">
                  {notice.deadline} ({notice.d_day})
                </div>
              </div>
              <div className="p-3.5 rounded-xl border border-zinc-200 bg-zinc-50/50">
                <div className="text-[11px] text-zinc-400 mb-1">{t.contactLabel}</div>
                <div className="text-xs font-semibold text-zinc-950 flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <span className="truncate">{notice.author}</span>
                </div>
                <div className="text-[11px] text-zinc-500 mt-0.5 flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 tabular-nums">
                    <Phone className="w-3 h-3" />
                    {notice.phone}
                  </span>
                  {notice.email && <span className="truncate">· {notice.email}</span>}
                </div>
              </div>
            </div>

            {/* AI Summary Box */}
            <div className="p-4 rounded-xl border border-zinc-200 bg-white space-y-2">
              <div className="text-xs font-semibold text-zinc-900 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-zinc-700" />
                <span>{t.tabSummary}</span>
              </div>
              <p className="text-sm text-zinc-700 leading-relaxed">{summary}</p>
            </div>

            {/* 1-Click Autonomous AI Agent Cards */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                {t.quickActionsTitle}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* Action 1: .ics Calendar */}
                <div className="p-4 rounded-xl border border-zinc-200 bg-white flex flex-col justify-between gap-3 hover:border-zinc-900 transition">
                  <div>
                    <div className="w-8 h-8 rounded-lg bg-zinc-100 text-zinc-900 flex items-center justify-center mb-2.5">
                      <Calendar className="w-4 h-4" />
                    </div>
                    <h4 className="text-xs font-bold text-zinc-950 mb-1">
                      {t.actionIcsTitle}
                    </h4>
                    <p className="text-[11px] text-zinc-500 leading-relaxed">
                      {t.actionIcsDesc}
                    </p>
                  </div>
                  <button
                    onClick={handleDownloadIcs}
                    className="w-full py-2 px-3 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium flex items-center justify-center gap-1.5 transition"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>{t.actionIcsBtn}</span>
                  </button>
                </div>

                {/* Action 2: Polite Korean Email */}
                <div className="p-4 rounded-xl border border-zinc-200 bg-white flex flex-col justify-between gap-3 hover:border-zinc-900 transition">
                  <div>
                    <div className="w-8 h-8 rounded-lg bg-zinc-100 text-zinc-900 flex items-center justify-center mb-2.5">
                      <Mail className="w-4 h-4" />
                    </div>
                    <h4 className="text-xs font-bold text-zinc-950 mb-1">
                      {t.actionEmailTitle}
                    </h4>
                    <p className="text-[11px] text-zinc-500 leading-relaxed">
                      {t.actionEmailDesc}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setActiveTab('agent');
                      if (!emailResult) handleGenerateEmail('');
                    }}
                    className="w-full py-2 px-3 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium flex items-center justify-center gap-1.5 transition"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{t.actionEmailBtn}</span>
                  </button>
                </div>

                {/* Action 3: 500-char Application Statement */}
                <div className="p-4 rounded-xl border border-zinc-200 bg-white flex flex-col justify-between gap-3 hover:border-zinc-900 transition">
                  <div>
                    <div className="w-8 h-8 rounded-lg bg-zinc-100 text-zinc-900 flex items-center justify-center mb-2.5">
                      <FileEdit className="w-4 h-4" />
                    </div>
                    <h4 className="text-xs font-bold text-zinc-950 mb-1">
                      {t.actionAppTitle}
                    </h4>
                    <p className="text-[11px] text-zinc-500 leading-relaxed">
                      {t.actionAppDesc}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setActiveTab('agent');
                      if (!appResult) handleGenerateApp();
                    }}
                    className="w-full py-2 px-3 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium flex items-center justify-center gap-1.5 transition"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{t.actionAppBtn}</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Quick HWP Preview Banner if HWP extracted */}
            {extractedHwp && (
              <div className="p-4 rounded-xl border border-zinc-200 bg-zinc-50 flex items-center justify-between gap-4">
                <div className="space-y-0.5">
                  <div className="text-xs font-bold text-zinc-950 flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-zinc-800" />
                    <span>{t.hwpViewerHeader}</span>
                  </div>
                  <p className="text-xs text-zinc-500">{t.hwpViewerSub}</p>
                </div>
                <button
                  onClick={() => setActiveTab('hwp')}
                  className="px-3 py-1.5 rounded-lg bg-white border border-zinc-300 hover:border-zinc-900 text-xs font-semibold text-zinc-900 shrink-0 transition"
                >
                  {t.tabHwp} →
                </button>
              </div>
            )}
          </>
        )}

        {/* TAB 2: AI AGENT STUDIO (EMAIL / APPLICATION DRAFT / ICS) */}
        {activeTab === 'agent' && (
          <div className="space-y-6">
            {/* Section 1: Polite Korean Inquiry Email Generator */}
            <div className="p-5 rounded-xl border border-zinc-200 bg-white space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-sm font-bold text-zinc-950 flex items-center gap-2">
                    <Mail className="w-4 h-4" />
                    <span>{t.actionEmailTitle}</span>
                  </h3>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    {notice.author} ({notice.phone}
                    {notice.email ? ` · ${notice.email}` : ''})
                  </p>
                </div>
                {emailResult?.engine && (
                  <span className="px-2 py-0.5 rounded bg-zinc-100 text-[11px] font-mono text-zinc-600">
                    {emailResult.engine}
                  </span>
                )}
              </div>

              {/* Quick Question Chips */}
              <div className="space-y-2">
                <label className="block text-xs font-medium text-zinc-700">
                  {t.emailPromptLabel}
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {[t.emailQuick1, t.emailQuick2, t.emailQuick3].map((q, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        setEmailQuestion(q);
                        handleGenerateEmail(q);
                      }}
                      className="px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-[11px] transition text-left"
                    >
                      + {q}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={emailQuestion}
                    onChange={(e) => setEmailQuestion(e.target.value)}
                    placeholder={t.emailQuick1}
                    className="flex-1 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs focus:outline-none focus:border-zinc-900"
                  />
                  <button
                    onClick={() => handleGenerateEmail()}
                    disabled={emailLoading}
                    className="px-4 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium shrink-0 disabled:opacity-50 transition"
                  >
                    {emailLoading ? '...' : t.btnGenerateEmail}
                  </button>
                </div>
              </div>

              {/* Generated Email Output */}
              {emailResult && (
                <div className="space-y-2 pt-2 border-t border-zinc-100">
                  <div className="text-xs font-semibold text-zinc-800">
                    Subject: {emailResult.subject}
                  </div>
                  <pre className="p-3.5 rounded-lg bg-zinc-50 border border-zinc-200 text-xs text-zinc-800 whitespace-pre-wrap font-sans leading-relaxed">
                    {emailResult.body}
                  </pre>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() =>
                        copyText(
                          `${emailResult.subject}\n\n${emailResult.body}`,
                          setEmailCopied
                        )
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 hover:border-zinc-900 text-xs font-medium text-zinc-800 transition"
                    >
                      {emailCopied ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                      <span>{emailCopied ? t.btnCopied : t.btnCopy}</span>
                    </button>
                    <a
                      href={`mailto:${encodeURIComponent(
                        emailResult.email || ''
                      )}?subject=${encodeURIComponent(
                        emailResult.subject || ''
                      )}&body=${encodeURIComponent(emailResult.body || '')}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium transition"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>
                        {t.btnSendMailApp} ({emailResult.email})
                      </span>
                    </a>
                  </div>
                </div>
              )}
            </div>

            {/* Section 2: 500-Char Korean Application Statement Drafter */}
            <div className="p-5 rounded-xl border border-zinc-200 bg-white space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-sm font-bold text-zinc-950 flex items-center gap-2">
                    <FileEdit className="w-4 h-4" />
                    <span>{t.actionAppTitle}</span>
                  </h3>
                  <p className="text-xs text-zinc-500 mt-0.5">{t.actionAppDesc}</p>
                </div>
                <button
                  onClick={handleGenerateApp}
                  disabled={appLoading}
                  className="px-4 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium shrink-0 disabled:opacity-50 transition"
                >
                  {appLoading ? '...' : t.btnGenerateApp}
                </button>
              </div>

              {appResult && (
                <div className="space-y-2 pt-2 border-t border-zinc-100">
                  {appResult.engine && (
                    <div className="text-[11px] font-mono text-zinc-400">
                      Engine: {appResult.engine}
                    </div>
                  )}
                  <pre className="p-3.5 rounded-lg bg-zinc-50 border border-zinc-200 text-xs text-zinc-800 whitespace-pre-wrap font-sans leading-relaxed">
                    {appResult.draft}
                  </pre>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => copyText(appResult.draft, setAppCopied)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-200 hover:border-zinc-900 text-xs font-medium text-zinc-800 transition"
                    >
                      {appCopied ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                      <span>{appCopied ? t.btnCopied : t.btnCopy}</span>
                    </button>
                    <button
                      onClick={() =>
                        downloadTxtFile(
                          `${notice.id}_application_draft.txt`,
                          appResult.draft
                        )
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>{t.btnDownloadTxt}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: OFFICIAL ATTACHMENTS & HWP VIEWER */}
        {activeTab === 'hwp' && (
          <div className="space-y-6">
            {/* Official Attachments Download List */}
            <div className="p-5 rounded-xl border border-zinc-200 bg-white space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                {t.filesHeader}
              </h3>
              {attachments.length === 0 ? (
                <p className="text-xs text-zinc-400">{t.noFiles}</p>
              ) : (
                <div className="divide-y divide-zinc-100">
                  {attachments.map((att, i) => (
                    <a
                      key={i}
                      href={att.url}
                      target="_blank"
                      rel="noreferrer"
                      className="py-2.5 flex items-center justify-between gap-3 group hover:bg-zinc-50 px-2 rounded-lg transition"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <FileText className="w-4 h-4 text-zinc-500 shrink-0" />
                        <span className="text-xs font-medium text-zinc-900 truncate group-hover:underline">
                          {att.name}
                        </span>
                      </div>
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-zinc-500 group-hover:text-zinc-950 shrink-0">
                        <Download className="w-3.5 h-3.5" />
                        <span>Download</span>
                      </span>
                    </a>
                  ))}
                </div>
              )}
            </div>

            {/* Automatic HWP / HWPX Extracted Text Viewer */}
            <div className="p-5 rounded-xl border border-zinc-200 bg-white space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-zinc-950">
                    {t.hwpViewerHeader}
                  </h3>
                  <p className="text-xs text-zinc-500">{t.hwpViewerSub}</p>
                </div>
                {extractedHwp && (
                  <div className="relative w-full sm:w-60">
                    <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={hwpKeyword}
                      onChange={(e) => setHwpKeyword(e.target.value)}
                      placeholder={t.hwpSearchPlaceholder}
                      className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-zinc-200 text-xs focus:outline-none focus:border-zinc-900"
                    />
                  </div>
                )}
              </div>

              {extractedHwp ? (
                <pre className="p-4 rounded-xl bg-zinc-50 border border-zinc-200 text-xs text-zinc-800 whitespace-pre-wrap font-mono leading-relaxed max-h-[500px] overflow-y-auto">
                  {renderHighlightedText(extractedHwp, hwpKeyword)}
                </pre>
              ) : (
                <p className="text-xs text-zinc-400 py-4">{t.noHwpText}</p>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: ORIGINAL KOREAN NOTICE BODY */}
        {activeTab === 'original' && (
          <div className="p-5 rounded-xl border border-zinc-200 bg-white space-y-3">
            <div className="flex items-center justify-between text-xs text-zinc-400 border-b border-zinc-100 pb-2">
              <span>
                {notice.author} · {notice.posted_date}
              </span>
              <span className="tabular-nums">{notice.char_count} chars</span>
            </div>
            <pre className="text-xs text-zinc-800 whitespace-pre-wrap font-sans leading-relaxed">
              {notice.body || extractedHwp || ''}
            </pre>
          </div>
        )}
      </div>
    </main>
  );
}

