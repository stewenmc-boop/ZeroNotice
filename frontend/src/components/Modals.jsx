import React, { useState } from 'react';
import { X, Link2, Cpu, FileText, Download, Sparkles } from 'lucide-react';

export function UrlParseModal({ t, lang, profile, open, onClose }) {
  const [inputVal, setInputVal] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  if (!open) return null;

  const sampleUrl =
    'https://kangwon.ac.kr/ko/bbs/721/detail.do?pstSn=2534&pageIndex=1&pageItm=10&searchOrderSort=0&searchGbn=0';

  const handleParse = async (valToUse) => {
    const raw = (valToUse !== undefined ? valToUse : inputVal).trim();
    if (!raw) return;
    setLoading(true);
    try {
      const res = await fetch('/api/parse-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url_or_text: raw,
          profile,
          lang,
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error('URL parse failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-card border border-line shadow-pop w-full max-w-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-5 py-4 border-b border-line flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Link2 className="w-4 h-4 text-ink" />
            <h2 className="text-title font-bold text-ink">{t.urlModalTitle}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-control text-faint hover:text-ink hover:bg-zinc-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto space-y-4">
          <p className="text-label text-muted leading-relaxed">{t.urlModalDesc}</p>

          <div className="space-y-2">
            <textarea
              rows={3}
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="https://kangwon.ac.kr/ko/bbs/721/detail.do?pstSn=2534"
              className="w-full rounded-control border border-line p-3 text-label font-mono text-ink focus:outline-none focus:border-ink/40"
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => {
                  setInputVal(sampleUrl);
                  handleParse(sampleUrl);
                }}
                className="px-3 py-1.5 rounded-control bg-accent-soft hover:bg-zinc-200/70 text-label font-medium text-zinc-700 transition"
              >
                {t.urlSampleBtn}
              </button>

              <button
                type="button"
                onClick={() => handleParse()}
                disabled={loading}
                className="px-4 py-1.5 rounded-control bg-ink hover:bg-ink/90 text-white text-label font-medium inline-flex items-center gap-1.5 disabled:opacity-50 transition"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{loading ? '...' : t.urlRunBtn}</span>
              </button>
            </div>
          </div>

          {result && (
            <div className="space-y-3 pt-3 border-t border-line">
              <div className="flex items-center justify-between">
                <span className="text-label font-bold text-ink">
                  {result.extracted?.title || 'Analysis Result'}
                </span>
                <span className="text-[11px] font-mono text-muted">
                  {result.engine}
                </span>
              </div>

              <pre className="p-3.5 rounded-control bg-canvas border border-line text-label text-zinc-700 whitespace-pre-wrap font-sans leading-relaxed">
                {result.analysis}
              </pre>

              {result.extracted?.attachments?.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold text-muted">
                    {t.filesHeader}
                  </div>
                  {result.extracted.attachments.map((att, idx) => (
                    <a
                      key={idx}
                      href={att.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between p-2 rounded-control border border-line hover:border-ink/30 text-label"
                    >
                      <span className="flex items-center gap-2 truncate">
                        <FileText className="w-3.5 h-3.5 text-muted shrink-0" />
                        <span className="truncate">{att.name}</span>
                      </span>
                      <Download className="w-3.5 h-3.5 text-muted shrink-0" />
                    </a>
                  ))}
                </div>
              )}

              {result.extracted?.attachment_extracted_text && (
                <div className="space-y-1">
                  <div className="text-[11px] font-semibold text-muted">
                    {t.hwpViewerHeader}
                  </div>
                  <pre className="p-3 rounded-control bg-canvas border border-line text-[11px] font-mono text-zinc-700 whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {result.extracted.attachment_extracted_text}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function GroqConfigModal({ t, groqStatus, open, onClose, onSaved }) {
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState(
    groqStatus?.model || 'llama-3.3-70b-versatile'
  );
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/config/groq', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, model }),
      });
      const data = await res.json();
      onSaved(data.groq);
      onClose();
    } catch (err) {
      console.error('Failed to save Groq config:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-card border border-line shadow-pop w-full max-w-md overflow-hidden">
        <div className="px-5 py-4 border-b border-line flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-ink" />
            <h2 className="text-title font-bold text-ink">
              {t.groqModalTitle}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-control text-faint hover:text-ink hover:bg-zinc-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-label text-muted leading-relaxed">
            {t.groqModalDesc}
          </p>

          <div className="space-y-3 text-label">
            <div>
              <label className="block font-medium text-zinc-700 mb-1">
                GROQ_API_KEY
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="gsk_..."
                className="w-full rounded-control border border-line px-3 py-2 font-mono text-label focus:outline-none focus:border-ink/40"
              />
            </div>

            <div>
              <label className="block font-medium text-zinc-700 mb-1">
                Groq Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full rounded-control border border-line px-3 py-2 text-label font-medium focus:outline-none focus:border-ink/40"
              >
                <option value="llama-3.3-70b-versatile">
                  llama-3.3-70b-versatile (Recommended)
                </option>
                <option value="llama-3.1-8b-instant">
                  llama-3.1-8b-instant (Ultra Fast)
                </option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-control border border-line text-label font-medium text-zinc-600 hover:text-ink"
            >
              {t.btnCancel}
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-1.5 rounded-control bg-ink hover:bg-ink/90 text-white text-label font-medium"
            >
              {saving ? '...' : t.btnSave}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

