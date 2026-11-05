import React, { useState, useEffect } from 'react';
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

export function LlmConfigModal({ t, llmStatus, open, onClose, onSaved }) {
  const providers = llmStatus?.providers?.length
    ? llmStatus.providers
    : [
        { id: 'openrouter', label: 'OpenRouter', base_url: 'https://openrouter.ai/api/v1', default_model: 'deepseek/deepseek-chat-v3.1:free' },
        { id: 'openai', label: 'OpenAI', base_url: 'https://api.openai.com/v1', default_model: 'gpt-4o-mini' },
        { id: 'groq', label: 'Groq', base_url: 'https://api.groq.com/openai/v1', default_model: 'llama-3.3-70b-versatile' },
        { id: 'custom', label: 'Custom', base_url: '', default_model: '' },
      ];

  const [provider, setProvider] = useState(llmStatus?.provider || 'openrouter');
  const [baseUrl, setBaseUrl] = useState(
    llmStatus?.base_url || 'https://openrouter.ai/api/v1'
  );
  const [model, setModel] = useState(llmStatus?.model || '');
  const [apiKey, setApiKey] = useState('');
  const [models, setModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // When opened without a pinned model, pull the provider's live model list.
  useEffect(() => {
    if (!open || model) return undefined;
    let cancelled = false;
    setLoadingModels(true);
    fetch(`/api/llm/models?provider=${encodeURIComponent(provider)}&free_only=true`)
      .then((res) => res.json())
      .then((data) => {
        if (cancelled || !data.ok || !data.models?.length) return;
        setModels(data.models);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingModels(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, provider]);

  if (!open) return null;

  const applyProvider = (pid) => {
    setProvider(pid);
    const meta = providers.find((p) => p.id === pid);
    if (meta) {
      setBaseUrl(meta.base_url || '');
      setModel(meta.default_model || '');
    }
    setModels([]);
    setError('');
  };

  const loadModels = async () => {
    setLoadingModels(true);
    setError('');
    try {
      const res = await fetch(
        `/api/llm/models?provider=${encodeURIComponent(provider)}&free_only=true`
      );
      const data = await res.json();
      if (data.ok && data.models?.length) {
        setModels(data.models);
        if (!data.models.includes(model)) setModel(data.models[0]);
      } else {
        setError(data.error || 'no models');
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoadingModels(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const res = await fetch('/api/config/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: apiKey,
          model,
          provider,
          base_url: baseUrl,
        }),
      });
      const data = await res.json();
      onSaved(data.llm || data.groq);
      onClose();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg overflow-hidden rounded-card border border-line bg-white shadow-pop">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-ink" />
            <h2 className="text-title font-semibold text-ink">{t.llmTitle}</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-control p-1 text-faint hover:bg-zinc-100 hover:text-ink"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          <p className="text-label leading-relaxed text-muted">{t.llmDesc}</p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-meta font-medium text-zinc-600">
                {t.llmProvider}
              </label>
              <select
                value={provider}
                onChange={(e) => applyProvider(e.target.value)}
                className="field"
              >
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-meta font-medium text-zinc-600">
                {t.llmApiKey}
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-or-v1-..."
                className="field font-mono"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-meta font-medium text-zinc-600">
              {t.llmBaseUrl}
            </label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://openrouter.ai/api/v1"
              className="field font-mono"
            />
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between">
              <label className="text-meta font-medium text-zinc-600">{t.llmModel}</label>
              <button
                type="button"
                onClick={loadModels}
                disabled={loadingModels}
                className="text-meta font-medium text-ink underline-offset-2 hover:underline disabled:opacity-50"
              >
                {loadingModels ? '...' : t.btnLoadModels}
              </button>
            </div>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              list="zn-model-list"
              placeholder="deepseek/deepseek-chat-v3.1:free"
              className="field font-mono"
            />
            <datalist id="zn-model-list">
              {models.map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
            {models.length > 0 && (
              <div className="mt-2 flex max-h-24 flex-wrap gap-1 overflow-y-auto">
                {models.slice(0, 12).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setModel(m)}
                    className={`rounded-chip px-1.5 py-0.5 text-[10px] transition ${
                      m === model
                        ? 'bg-ink text-white'
                        : 'bg-accent-soft text-muted hover:text-ink'
                    }`}
                  >
                    {m.replace(':free', '')}
                  </button>
                ))}
              </div>
            )}
          </div>

          <p className="text-meta leading-5 text-faint">{t.llmHint}</p>
          {error && <p className="text-meta text-amber-700">{error}</p>}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              onClick={onClose}
              className="rounded-control border border-line px-3 py-1.5 text-label font-medium text-zinc-600 hover:text-ink"
            >
              {t.btnCancel}
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded-control bg-ink px-4 py-1.5 text-label font-medium text-white hover:bg-ink/90 disabled:opacity-50"
            >
              {saving ? '...' : t.btnSave}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// backward compatibility for older imports
export const GroqConfigModal = LlmConfigModal;
