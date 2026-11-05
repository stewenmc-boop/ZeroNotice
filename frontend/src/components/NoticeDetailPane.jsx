import React, { useState, useEffect, useRef } from 'react';
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
  ArrowRight,
  Link2,
} from 'lucide-react';

const VERDICT_STYLE = {
  eligible: {
    wrap: 'bg-emerald-50/70 ring-emerald-100',
    icon: 'text-emerald-600',
    Icon: CheckCircle2,
  },
  conditional: {
    wrap: 'bg-amber-50/70 ring-amber-100',
    icon: 'text-amber-600',
    Icon: AlertCircle,
  },
  ineligible: {
    wrap: 'bg-canvas ring-line',
    icon: 'text-zinc-400',
    Icon: MinusCircle,
  },
};

function CopyButton({ value, label }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      title={label}
      onClick={(e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(value || '');
        setDone(true);
        setTimeout(() => setDone(false), 1500);
      }}
      className="grid h-5 w-5 shrink-0 place-items-center rounded text-faint transition hover:bg-accent-soft hover:text-ink"
    >
      {done ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
    </button>
  );
}

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
  const initialTab = (() => {
    const fromUrl = new URLSearchParams(window.location.search).get('tab');
    return ['summary', 'agent', 'hwp', 'original'].includes(fromUrl) ? fromUrl : 'summary';
  })();
  const firstTabRun = useRef(true);
  const [activeTab, setActiveTab] = useState(initialTab);
  const [emailQuestion, setEmailQuestion] = useState('');
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailResult, setEmailResult] = useState(null);
  const [emailCopied, setEmailCopied] = useState(false);

  const [appLoading, setAppLoading] = useState(false);
  const [appResult, setAppResult] = useState(null);
  const [appCopied, setAppCopied] = useState(false);

  const [hwpKeyword, setHwpKeyword] = useState('');
  const [fields, setFields] = useState(null);
  const [fieldsLoading, setFieldsLoading] = useState(false);

  useEffect(() => {
    if (!notice) return;
    setEmailResult(null);
    setAppResult(null);
    setEmailQuestion('');
    setHwpKeyword('');
    setFields(notice.fields || null);
    setActiveTab(firstTabRun.current ? initialTab : 'summary');
    firstTabRun.current = false;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notice?.id]);

  if (!notice) {
    return (
      <main className="flex flex-1 items-center justify-center bg-white p-8 text-label text-faint">
        {t.emptyList}
      </main>
    );
  }

  const title = notice[`title_${lang}`] || notice.title_ko || notice.title;
  const summary = notice[`summary_${lang}`] || notice.summary_ko || '';
  const benefit = notice[`benefit_label_${lang}`] || notice.benefit_label_ko || '';
  const verdict = notice[`verdict_${lang}`] || notice.verdict_ko || '';
  const attachments = notice.attachments || [];
  const imageAttachments = attachments.filter((a) =>
    /\.(png|jpe?g|gif|webp|bmp)$/i.test(a.name || '')
  );
  const extractedHwp = notice.attachment_extracted_text || '';
  const vStyle = VERDICT_STYLE[notice.match_status] || VERDICT_STYLE.ineligible;
  const VIcon = vStyle.Icon;

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
        body: JSON.stringify({ notice_id: notice.id, profile, custom_question: q, lang }),
      });
      setEmailResult(await res.json());
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
        body: JSON.stringify({ notice_id: notice.id, profile, lang }),
      });
      setAppResult(await res.json());
    } catch (err) {
      console.error('Failed to generate application draft:', err);
    } finally {
      setAppLoading(false);
    }
  };

  const handleExtractFields = async () => {
    setFieldsLoading(true);
    try {
      const res = await fetch(`/api/notices/${encodeURIComponent(notice.id)}/fields`);
      const data = await res.json();
      setFields(data.fields || null);
    } catch (err) {
      console.error('Failed to extract application fields:', err);
    } finally {
      setFieldsLoading(false);
    }
  };

  const copyText = (text, setFlag) => {    navigator.clipboard.writeText(text || '');
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
    const parts = rawText.split(
      new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
    );
    return parts.map((part, idx) =>
      part.toLowerCase() === keyword.toLowerCase() ? (
        <mark key={idx} className="rounded bg-amber-200 px-0.5 text-ink">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  const TABS = [
    { key: 'summary', label: t.tabSummary, icon: Sparkles },
    { key: 'agent', label: t.tabAgent, icon: Mail },
    { key: 'hwp', label: `${t.tabHwp} (${attachments.length})`, icon: FileText },
    { key: 'original', label: t.tabOriginal, icon: FileEdit },
  ];

  return (
    <main className="flex flex-1 flex-col overflow-y-auto bg-white">
      {/* Sticky header */}
      <div className="sticky top-0 z-20 border-b border-line bg-white/95 px-7 pt-4 backdrop-blur">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2.5">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-meta">
            <span className="rounded-md bg-accent-soft px-2 py-0.5 font-semibold text-ink">
              {notice.category}
            </span>
            <span className="font-medium text-zinc-700">{notice.author}</span>
            <span className="text-line">/</span>
            <span className="text-faint">
              {t.postedOn} {notice.posted_date}
            </span>
            {notice.verified_at && (
              <>
                <span className="text-line">/</span>
                <span className="inline-flex items-center gap-1 text-emerald-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {t.verifiedAt} {String(notice.verified_at).slice(5, 16)}
                </span>
              </>
            )}
          </div>

          <div className="ml-auto flex flex-wrap items-center justify-end gap-1.5">
            <div className="seg">
              {[
                { key: 'none', label: t.progNone },
                { key: 'prep', label: t.progPrep },
                { key: 'done', label: t.progDone },
              ].map((st) => (
                <button
                  key={st.key}
                  onClick={() => onChangeProgress(notice.id, st.key)}
                  className={`${progress === st.key ? 'seg-item seg-item-active' : 'seg-item hover:text-ink'}`}
                >
                  {st.label}
                </button>
              ))}
            </div>

            <button
              onClick={() => onToggleSave(notice.id)}
              title="Bookmark"
              className={`grid h-8 w-8 place-items-center rounded-control transition ${
                isSaved
                  ? 'bg-ink text-white'
                  : 'text-muted ring-1 ring-line hover:text-ink hover:ring-ink/25'
              }`}
            >
              <Bookmark className="h-3.5 w-3.5" fill={isSaved ? 'currentColor' : 'none'} />
            </button>

            <a
              href={notice.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-8 items-center gap-1.5 rounded-control px-2.5 text-label font-medium text-muted ring-1 ring-line transition hover:text-ink hover:ring-ink/25"
            >
              <span>{t.openOriginal}</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>

        <h1 className="mt-3 max-w-[820px] text-h1 font-semibold leading-8 tracking-[-0.015em] text-ink">
          {title}
        </h1>

        <div className="-mb-px mt-3 flex items-center gap-5 overflow-x-auto pr-2">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex h-10 shrink-0 items-center gap-1.5 border-b-2 text-label font-medium transition ${
                  active
                    ? 'border-ink text-ink'
                    : 'border-transparent text-muted hover:text-ink'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="w-full max-w-[860px] space-y-6 px-7 py-6">
        {/* ---------- SUMMARY ---------- */}
        {activeTab === 'summary' && (
          <>
            <div
              className={`flex items-start justify-between gap-4 rounded-card p-4 ring-1 ${vStyle.wrap}`}
            >
              <div className="flex min-w-0 items-start gap-3">
                <VIcon className={`mt-0.5 h-4 w-4 shrink-0 ${vStyle.icon}`} />
                <div className="min-w-0">
                  <div className="mb-0.5 text-meta font-semibold uppercase tracking-[0.08em] text-muted">
                    {t.verdictTitle}
                  </div>
                  <div className="text-title font-semibold leading-6 text-ink">{verdict}</div>
                </div>
              </div>
              <span className="shrink-0 rounded-md bg-white px-2 py-1 text-meta font-semibold tabular-nums text-ink ring-1 ring-line">
                {notice.d_day}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-card p-4 ring-1 ring-line">
                <div className="mb-1.5 text-meta text-faint">{t.benefitLabel}</div>
                <div className="text-body font-medium leading-5 text-ink">{benefit}</div>
              </div>

              <div className="rounded-card p-4 ring-1 ring-line">
                <div className="mb-1.5 text-meta text-faint">{t.deadlineLabel}</div>
                <div className="text-body font-medium tabular-nums leading-5 text-ink">
                  {notice.deadline}
                </div>
              </div>

              <div className="min-w-0 rounded-card p-4 ring-1 ring-line sm:col-span-2 xl:col-span-1">
                <div className="mb-1.5 text-meta text-faint">{t.contactLabel}</div>
                <div className="flex items-center gap-1.5 text-body font-medium leading-5 text-ink">
                  <Building2 className="h-3.5 w-3.5 shrink-0 text-faint" />
                  <span className="truncate">{notice.author}</span>
                </div>
                <div className="mt-1 space-y-0.5 text-meta text-muted">
                  {notice.phone && (
                    <div className="flex items-center gap-1">
                      <Phone className="h-3 w-3 shrink-0 text-faint" />
                      <span className="whitespace-nowrap tabular-nums">{notice.phone}</span>
                      <CopyButton value={notice.phone} label="copy" />
                    </div>
                  )}
                  {notice.email && (
                    <div className="flex min-w-0 items-center gap-1">
                      <Mail className="h-3 w-3 shrink-0 text-faint" />
                      <span className="truncate" title={notice.email}>
                        {notice.email}
                      </span>
                      <CopyButton value={notice.email} label="copy" />
                    </div>
                  )}
                </div>
              </div>
            </div>

            <section className="rounded-card p-5 ring-1 ring-line">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-1.5 text-meta font-semibold uppercase tracking-[0.08em] text-muted">
                  <Link2 className="h-3.5 w-3.5" />
                  <span>{t.siTitle}</span>
                </div>
                <button
                  onClick={handleExtractFields}
                  disabled={fieldsLoading}
                  className="inline-flex h-7 items-center gap-1 rounded-chip px-2 text-meta font-medium text-ink ring-1 ring-line transition hover:ring-ink/30 disabled:opacity-50"
                >
                  <Sparkles className="h-3 w-3" />
                  <span>
                    {fieldsLoading ? '...' : fields ? t.siRefresh : t.siExtractBtn}
                  </span>
                </button>
              </div>

              {!fields ? (
                <p className="text-meta leading-5 text-muted">{t.siEmpty}</p>
              ) : (
                <div className="space-y-3">
                  {fields.application_url && (
                    <a
                      href={fields.application_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-control bg-ink px-3 text-label font-medium text-white transition hover:bg-ink/90"
                    >
                      <Link2 className="h-3.5 w-3.5" />
                      <span>{t.siLink}</span>
                      <ExternalLink className="h-3 w-3 opacity-70" />
                    </a>
                  )}
                  {fields.application_url && (
                    <div className="truncate font-mono text-[10px] text-faint">
                      {fields.application_url}
                    </div>
                  )}

                  {(fields[`application_method_${lang}`] ||
                    fields.application_method_ko ||
                    fields.application_method) && (
                    <div>
                      <div className="mb-0.5 text-meta text-faint">{t.siMethod}</div>
                      <div className="text-body leading-6 text-zinc-700">
                        {fields[`application_method_${lang}`] ||
                          fields.application_method_ko ||
                          fields.application_method}
                      </div>
                    </div>
                  )}

                  {fields.required_documents?.length > 0 && (
                    <div>
                      <div className="mb-1 text-meta text-faint">{t.siDocs}</div>
                      <div className="flex flex-wrap gap-1">
                        {fields.required_documents.map((doc, idx) => (
                          <span
                            key={idx}
                            className="rounded-chip bg-accent-soft px-1.5 py-0.5 text-meta text-muted"
                          >
                            {doc}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-2 text-meta text-muted">
                    <span className="text-faint">{t.siContact}</span>
                    {fields.contact_email ? (
                      <a
                        href={`mailto:${fields.contact_email}`}
                        className="truncate text-ink hover:underline"
                      >
                        {fields.contact_email}
                      </a>
                    ) : null}
                    {fields.contact_phone ? (
                      <span className="tabular-nums text-ink">{fields.contact_phone}</span>
                    ) : null}
                    {!fields.contact_email && !fields.contact_phone && (
                      <span className="text-faint">{t.siNoEmail}</span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 border-t border-line pt-2 text-[10px] text-faint">
                    <span>
                      {t.siSource}: {fields.source_hint || '-'}
                    </span>
                    <span>·</span>
                    <span className="tabular-nums">
                      {Math.round((Number(fields.confidence) || 0) * 100)}%
                    </span>
                  </div>
                </div>
              )}
            </section>

            <section className="rounded-card p-5 ring-1 ring-line">
              <div className="mb-2 flex items-center gap-1.5 text-meta font-semibold uppercase tracking-[0.08em] text-muted">
                <Sparkles className="h-3.5 w-3.5" />
                <span>{t.tabSummary}</span>
              </div>
              <p className="text-body leading-7 text-zinc-700">{summary}</p>
            </section>

            <section>
              <div className="mb-2.5 text-meta font-semibold uppercase tracking-[0.08em] text-faint">
                {t.quickActionsTitle}
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                {[
                  {
                    icon: Calendar,
                    title: t.actionIcsTitle,
                    desc: t.actionIcsDesc,
                    btn: t.actionIcsBtn,
                    onClick: handleDownloadIcs,
                    primary: true,
                    btnIcon: Download,
                  },
                  {
                    icon: Mail,
                    title: t.actionEmailTitle,
                    desc: t.actionEmailDesc,
                    btn: t.actionEmailBtn,
                    onClick: () => {
                      setActiveTab('agent');
                      if (!emailResult) handleGenerateEmail('');
                    },
                    btnIcon: Sparkles,
                  },
                  {
                    icon: FileEdit,
                    title: t.actionAppTitle,
                    desc: t.actionAppDesc,
                    btn: t.actionAppBtn,
                    onClick: () => {
                      setActiveTab('agent');
                      if (!appResult) handleGenerateApp();
                    },
                    btnIcon: Sparkles,
                  },
                ].map((a) => {
                  const Icon = a.icon;
                  const BtnIcon = a.btnIcon;
                  return (
                    <div
                      key={a.title}
                      className="flex flex-col justify-between gap-3 rounded-card p-4 ring-1 ring-line transition hover:ring-ink/20"
                    >
                      <div>
                        <div className="mb-2.5 grid h-8 w-8 place-items-center rounded-lg bg-accent-soft text-ink">
                          <Icon className="h-4 w-4" />
                        </div>
                        <h4 className="mb-1 text-body font-semibold text-ink">{a.title}</h4>
                        <p className="text-meta leading-5 text-muted">{a.desc}</p>
                      </div>
                      <button
                        onClick={a.onClick}
                        className={`inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-control text-label font-medium transition ${
                          a.primary
                            ? 'bg-ink text-white hover:bg-ink/90'
                            : 'text-ink ring-1 ring-line hover:ring-ink/30'
                        }`}
                      >
                        <BtnIcon className="h-3.5 w-3.5" />
                        <span>{a.btn}</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            </section>

            {extractedHwp && (
              <button
                onClick={() => setActiveTab('hwp')}
                className="flex w-full items-center justify-between gap-4 rounded-card p-4 text-left ring-1 ring-line transition hover:ring-ink/20"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-accent-soft text-ink">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-body font-semibold text-ink">{t.hwpViewerHeader}</div>
                    <div className="truncate text-meta text-muted">{t.hwpViewerSub}</div>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-faint" />
              </button>
            )}
          </>
        )}

        {/* ---------- AGENT ---------- */}
        {activeTab === 'agent' && (
          <div className="space-y-4">
            <section className="space-y-4 rounded-card p-5 ring-1 ring-line">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h3 className="flex items-center gap-2 text-body font-semibold text-ink">
                    <Mail className="h-4 w-4 text-muted" />
                    <span>{t.actionEmailTitle}</span>
                  </h3>
                  <p className="mt-0.5 truncate text-meta text-muted">
                    {notice.author} · {notice.phone}
                    {notice.email ? ` · ${notice.email}` : ''}
                  </p>
                </div>
                {emailResult?.engine && (
                  <span className="shrink-0 rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[10px] text-muted">
                    {emailResult.engine}
                  </span>
                )}
              </div>

              <div className="space-y-2">
                <div className="text-meta font-medium text-zinc-600">{t.emailPromptLabel}</div>
                <div className="flex flex-wrap gap-1.5">
                  {[t.emailQuick1, t.emailQuick2, t.emailQuick3].map((q, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        setEmailQuestion(q);
                        handleGenerateEmail(q);
                      }}
                      className="rounded-chip bg-accent-soft px-2 py-1 text-meta text-muted transition hover:bg-zinc-200/70 hover:text-ink"
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
                    className="h-9 flex-1 rounded-control border border-line px-3 text-label text-ink transition placeholder:text-faint focus:border-ink/40 focus:outline-none"
                  />
                  <button
                    onClick={() => handleGenerateEmail()}
                    disabled={emailLoading}
                    className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-control bg-ink px-4 text-label font-medium text-white transition hover:bg-ink/90 disabled:opacity-50"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>{emailLoading ? '...' : t.btnGenerateEmail}</span>
                  </button>
                </div>
              </div>

              {emailResult && (
                <div className="space-y-2.5 border-t border-line pt-3">
                  {emailResult.missing_fields?.length > 0 && (
                    <div className="rounded-control bg-amber-50 px-3 py-2 text-meta leading-5 text-amber-800 ring-1 ring-amber-100">
                      {t.warnMissingProfile}
                    </div>
                  )}
                  <div className="truncate text-label font-medium text-zinc-700">
                    {emailResult.subject}
                  </div>
                  <pre className="max-h-[380px] overflow-y-auto whitespace-pre-wrap rounded-control bg-canvas p-4 font-sans text-label leading-6 text-zinc-800 ring-1 ring-line">
                    {emailResult.body}
                  </pre>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() =>
                        copyText(`${emailResult.subject}\n\n${emailResult.body}`, setEmailCopied)
                      }
                      className="inline-flex h-8 items-center gap-1.5 rounded-control px-2.5 text-label font-medium text-ink ring-1 ring-line transition hover:ring-ink/30"
                    >
                      {emailCopied ? (
                        <Check className="h-3.5 w-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                      <span>{emailCopied ? t.btnCopied : t.btnCopy}</span>
                    </button>
                    {emailResult.email ? (
                      <a
                        href={`mailto:${encodeURIComponent(emailResult.email)}?subject=${encodeURIComponent(emailResult.subject || '')}&body=${encodeURIComponent(emailResult.body || '')}`}
                        className="inline-flex h-8 items-center gap-1.5 rounded-control bg-ink px-2.5 text-label font-medium text-white transition hover:bg-ink/90"
                      >
                        <Send className="h-3.5 w-3.5" />
                        <span>
                          {t.btnSendMailApp} ({emailResult.email})
                        </span>
                      </a>
                    ) : (
                      <span className="text-meta leading-5 text-amber-700">{t.siNoEmail}</span>
                    )}
                  </div>
                </div>
              )}
            </section>

            <section className="space-y-4 rounded-card p-5 ring-1 ring-line">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h3 className="flex items-center gap-2 text-body font-semibold text-ink">
                    <FileEdit className="h-4 w-4 text-muted" />
                    <span>{t.actionAppTitle}</span>
                  </h3>
                  <p className="mt-0.5 text-meta text-muted">{t.actionAppDesc}</p>
                </div>
                <button
                  onClick={handleGenerateApp}
                  disabled={appLoading}
                  className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-control bg-ink px-3 text-label font-medium text-white transition hover:bg-ink/90 disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>{appLoading ? '...' : t.btnGenerateApp}</span>
                </button>
              </div>

              {appResult && (
                <div className="space-y-2.5 border-t border-line pt-3">
                  {appResult.missing_fields?.length > 0 && (
                    <div className="rounded-control bg-amber-50 px-3 py-2 text-meta leading-5 text-amber-800 ring-1 ring-amber-100">
                      {t.warnMissingProfile}
                    </div>
                  )}
                  {appResult.engine && (
                    <div className="font-mono text-[10px] text-faint">Engine: {appResult.engine}</div>
                  )}
                  <pre className="max-h-[420px] overflow-y-auto whitespace-pre-wrap rounded-control bg-canvas p-4 font-sans text-label leading-6 text-zinc-800 ring-1 ring-line">
                    {appResult.draft}
                  </pre>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => copyText(appResult.draft, setAppCopied)}
                      className="inline-flex h-8 items-center gap-1.5 rounded-control px-2.5 text-label font-medium text-ink ring-1 ring-line transition hover:ring-ink/30"
                    >
                      {appCopied ? (
                        <Check className="h-3.5 w-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                      <span>{appCopied ? t.btnCopied : t.btnCopy}</span>
                    </button>
                    <button
                      onClick={() =>
                        downloadTxtFile(`${notice.id}_application_draft.txt`, appResult.draft)
                      }
                      className="inline-flex h-8 items-center gap-1.5 rounded-control bg-ink px-2.5 text-label font-medium text-white transition hover:bg-ink/90"
                    >
                      <Download className="h-3.5 w-3.5" />
                      <span>{t.btnDownloadTxt}</span>
                    </button>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        {/* ---------- HWP ---------- */}
        {activeTab === 'hwp' && (
          <div className="space-y-4">
            {imageAttachments.length > 0 && (
              <section className="rounded-card p-5 ring-1 ring-line">
                <h3 className="mb-3 text-meta font-semibold uppercase tracking-[0.08em] text-faint">
                  {t.imageHeader}
                </h3>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {imageAttachments.map((att, idx) => (
                    <a
                      key={idx}
                      href={att.url}
                      target="_blank"
                      rel="noreferrer"
                      className="group block overflow-hidden rounded-control ring-1 ring-line transition hover:ring-ink/30"
                    >
                      <img
                        src={att.url}
                        alt={att.name}
                        loading="lazy"
                        className="h-36 w-full bg-canvas object-cover"
                      />
                      <div className="truncate px-2 py-1.5 text-[10px] text-muted">
                        {att.name}
                      </div>
                    </a>
                  ))}
                </div>
                {notice.image_links?.length > 0 && (
                  <div className="mt-3 border-t border-line pt-3">
                    <div className="mb-1 text-meta text-faint">{t.siLink}</div>
                    {notice.image_links.map((link, idx) => (
                      <a
                        key={idx}
                        href={link}
                        target="_blank"
                        rel="noreferrer"
                        className="block truncate font-mono text-[11px] text-ink hover:underline"
                      >
                        {link}
                      </a>
                    ))}
                  </div>
                )}
              </section>
            )}

            <section className="rounded-card p-5 ring-1 ring-line">
              <h3 className="mb-3 text-meta font-semibold uppercase tracking-[0.08em] text-faint">
                {t.filesHeader}
              </h3>
              {attachments.length === 0 ? (
                <p className="text-label text-faint">{t.noFiles}</p>
              ) : (
                <div className="divide-y divide-line">
                  {attachments.map((att, i) => (
                    <a
                      key={i}
                      href={att.url}
                      target="_blank"
                      rel="noreferrer"
                      className="group flex items-center justify-between gap-3 py-2.5"
                    >
                      <div className="flex min-w-0 items-center gap-2.5">
                        <FileText className="h-4 w-4 shrink-0 text-faint" />
                        <span className="truncate text-label font-medium text-ink group-hover:underline">
                          {att.name}
                        </span>
                      </div>
                      <span className="inline-flex shrink-0 items-center gap-1 text-meta text-faint transition group-hover:text-ink">
                        <Download className="h-3.5 w-3.5" />
                        <span>Download</span>
                      </span>
                    </a>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-card p-5 ring-1 ring-line">
              <div className="mb-3 flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                <div>
                  <h3 className="text-body font-semibold text-ink">{t.hwpViewerHeader}</h3>
                  <p className="text-meta text-muted">{t.hwpViewerSub}</p>
                </div>
                {extractedHwp && (
                  <div className="relative w-full sm:w-56">
                    <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
                    <input
                      type="text"
                      value={hwpKeyword}
                      onChange={(e) => setHwpKeyword(e.target.value)}
                      placeholder={t.hwpSearchPlaceholder}
                      className="h-8 w-full rounded-control border border-line pl-8 pr-3 text-label text-ink transition placeholder:text-faint focus:border-ink/40 focus:outline-none"
                    />
                  </div>
                )}
              </div>

              {extractedHwp ? (
                <pre className="max-h-[520px] overflow-y-auto whitespace-pre-wrap rounded-control bg-canvas p-4 font-mono text-[11.5px] leading-6 text-zinc-700 ring-1 ring-line">
                  {renderHighlightedText(extractedHwp, hwpKeyword)}
                </pre>
              ) : (
                <p className="py-6 text-center text-label text-faint">{t.noHwpText}</p>
              )}
            </section>
          </div>
        )}

        {/* ---------- ORIGINAL ---------- */}
        {activeTab === 'original' && (
          <section className="rounded-card p-5 ring-1 ring-line">
            <div className="mb-3 flex items-center justify-between border-b border-line pb-2.5 text-meta text-faint">
              <span>
                {notice.author} · {notice.posted_date}
              </span>
              <span className="tabular-nums">{notice.char_count} chars</span>
            </div>
            <pre className="whitespace-pre-wrap font-sans text-label leading-7 text-zinc-700">
              {notice.body || extractedHwp || ''}
            </pre>
          </section>
        )}
      </div>
    </main>
  );
}
