import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { I18N } from './i18n/translations';
import TopNavbar from './components/TopNavbar';
import SidebarFilter from './components/SidebarFilter';
import NoticeListPane from './components/NoticeListPane';
import NoticeDetailPane from './components/NoticeDetailPane';
import { UrlParseModal, GroqConfigModal } from './components/Modals';

const DEFAULT_PROFILE = {
  campus: '춘천',
  status: 'undergrad_kr',
  department: '첨단AI공학부',
  grade: 3,
  gpa: 3.8,
  income_bracket: 3,
  name: '김강원',
  student_id: '202411234',
};

export default function App() {
  const [lang, setLang] = useState(() => {
    const fromUrl = new URLSearchParams(window.location.search).get('lang');
    const supported = ['ko', 'zh', 'en'];
    if (fromUrl && supported.includes(fromUrl)) return fromUrl;
    const saved = localStorage.getItem('zn_lang');
    return supported.includes(saved) ? saved : 'ko';
  });
  const [category, setCategory] = useState('ALL');
  const [onlyEligible, setOnlyEligible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const [profile, setProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('zn_profile');
      return saved ? { ...DEFAULT_PROFILE, ...JSON.parse(saved) } : DEFAULT_PROFILE;
    } catch {
      return DEFAULT_PROFILE;
    }
  });

  const [savedIds, setSavedIds] = useState(() => {
    try {
      const saved = localStorage.getItem('zn_saved_ids');
      return saved ? JSON.parse(saved) : ['knu-real-02', 'knu-real-30'];
    } catch {
      return ['knu-real-02', 'knu-real-30'];
    }
  });

  const [progressMap, setProgressMap] = useState(() => {
    try {
      const saved = localStorage.getItem('zn_progress');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const [notices, setNotices] = useState([]);
  const [stats, setStats] = useState(null);
  const [groqStatus, setGroqStatus] = useState({ configured: false, model: 'llama-3.3-70b-versatile' });
  const [selectedId, setSelectedId] = useState('knu-real-02');
  const [loading, setLoading] = useState(false);

  const [urlModalOpen, setUrlModalOpen] = useState(false);
  const [groqModalOpen, setGroqModalOpen] = useState(false);

  const t = I18N[lang] || I18N.ko;

  // Persist user preferences
  useEffect(() => {
    localStorage.setItem('zn_lang', lang);
  }, [lang]);

  useEffect(() => {
    localStorage.setItem('zn_profile', JSON.stringify(profile));
  }, [profile]);

  useEffect(() => {
    localStorage.setItem('zn_saved_ids', JSON.stringify(savedIds));
  }, [savedIds]);

  useEffect(() => {
    localStorage.setItem('zn_progress', JSON.stringify(progressMap));
  }, [progressMap]);

  const fetchNotices = useCallback(
    async (liveCheck = false) => {
      setLoading(true);
      try {
        const res = await fetch('/api/notices', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...profile, live_check: liveCheck }),
        });
        const data = await res.json();
        setNotices(data.notices || []);
        setStats(data.stats || null);
        if (data.groq) setGroqStatus(data.groq);
      } catch (err) {
        console.error('Failed to fetch notices:', err);
      } finally {
        setLoading(false);
      }
    },
    [profile]
  );

  useEffect(() => {
    fetchNotices(false);
  }, [fetchNotices]);

  const toggleSave = (id) => {
    setSavedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const updateProgress = (id, status) => {
    setProgressMap((prev) => ({ ...prev, [id]: status }));
  };

  // Compute category counts
  const counts = useMemo(() => {
    const base = onlyEligible
      ? notices.filter((n) => n.match_status !== 'ineligible')
      : notices;
    const map = { ALL: base.length, 장학: 0, 학사: 0, 공모: 0, 일반행사: 0 };
    base.forEach((n) => {
      if (n.category === '장학') map['장학'] += 1;
      else if (n.category === '학사') map['학사'] += 1;
      else if (n.category === '공모') map['공모'] += 1;
      else map['일반행사'] += 1;
    });
    return map;
  }, [notices, onlyEligible]);

  // Filter notices by category, eligibility, and search query
  const visibleNotices = useMemo(() => {
    return notices.filter((n) => {
      if (onlyEligible && n.match_status === 'ineligible') return false;
      if (category === 'SAVED') {
        if (!savedIds.includes(n.id)) return false;
      } else if (category === '일반행사') {
        if (n.category !== '일반' && n.category !== '행사') return false;
      } else if (category !== 'ALL' && n.category !== category) {
        return false;
      }

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const haystack = [
          n.title,
          n.title_ko,
          n.title_zh,
          n.title_en,
          n.summary_ko,
          n.summary_zh,
          n.summary_en,
          n.body,
          n.attachment_extracted_text,
          n.author,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        if (!haystack.includes(q)) return false;
      }

      return true;
    });
  }, [notices, onlyEligible, category, savedIds, searchQuery]);

  // Keep selected notice valid
  const selectedNotice = useMemo(() => {
    return (
      visibleNotices.find((n) => n.id === selectedId) ||
      notices.find((n) => n.id === selectedId) ||
      visibleNotices[0] ||
      null
    );
  }, [visibleNotices, notices, selectedId]);

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-white text-zinc-900">
      {/* Top Bar */}
      <TopNavbar
        t={t}
        lang={lang}
        setLang={setLang}
        stats={stats}
        groqStatus={groqStatus}
        onOpenUrlModal={() => setUrlModalOpen(true)}
        onOpenGroqModal={() => setGroqModalOpen(true)}
      />

      {/* Main 3-Pane Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Board Nav & Academic Profile */}
        <SidebarFilter
          t={t}
          category={category}
          setCategory={setCategory}
          onlyEligible={onlyEligible}
          setOnlyEligible={setOnlyEligible}
          profile={profile}
          onChangeProfile={setProfile}
          counts={counts}
          ineligibleCount={stats?.ineligible || 0}
          savedIds={savedIds}
          loading={loading}
          onRefresh={() => fetchNotices(true)}
        />

        {/* Middle Pane: Notice Feed List */}
        <NoticeListPane
          t={t}
          lang={lang}
          notices={visibleNotices}
          selectedId={selectedNotice?.id}
          onSelect={setSelectedId}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          savedIds={savedIds}
          onToggleSave={toggleSave}
          progressMap={progressMap}
        />

        {/* Right Pane: Notice Detail, HWP Reader & AI Agent Studio */}
        <NoticeDetailPane
          t={t}
          lang={lang}
          notice={selectedNotice}
          profile={profile}
          isSaved={selectedNotice ? savedIds.includes(selectedNotice.id) : false}
          onToggleSave={toggleSave}
          progress={selectedNotice ? progressMap[selectedNotice.id] || 'none' : 'none'}
          onChangeProgress={updateProgress}
        />
      </div>

      {/* Live URL / HWP Parser Modal */}
      <UrlParseModal
        t={t}
        lang={lang}
        profile={profile}
        open={urlModalOpen}
        onClose={() => setUrlModalOpen(false)}
      />

      {/* Groq LPU Config Modal */}
      <GroqConfigModal
        t={t}
        groqStatus={groqStatus}
        open={groqModalOpen}
        onClose={() => setGroqModalOpen(false)}
        onSaved={(newGroq) => setGroqStatus(newGroq)}
      />
    </div>
  );
}

