import React from 'react';
import {
  Layers,
  GraduationCap,
  BookOpen,
  Trophy,
  Calendar,
  Bookmark,
  RefreshCw,
  Filter,
} from 'lucide-react';

export default function SidebarFilter({
  t,
  category,
  setCategory,
  onlyEligible,
  setOnlyEligible,
  profile,
  onChangeProfile,
  counts,
  ineligibleCount,
  savedIds,
  loading,
  onRefresh,
}) {
  const navItems = [
    { key: 'ALL', label: t.catAll, icon: Layers, count: counts.ALL },
    { key: '장학', label: t.catSch, icon: GraduationCap, count: counts['장학'] },
    { key: '학사', label: t.catAca, icon: BookOpen, count: counts['학사'] },
    { key: '공모', label: t.catCon, icon: Trophy, count: counts['공모'] },
    { key: '일반행사', label: t.catGen, icon: Calendar, count: counts['일반행사'] },
    { key: 'SAVED', label: t.catSaved, icon: Bookmark, count: savedIds.length },
  ];

  const updateField = (field, value) => onChangeProfile({ ...profile, [field]: value });

  const SectionLabel = ({ children }) => (
    <div className="mb-2 px-1 text-meta font-semibold uppercase tracking-[0.08em] text-faint">
      {children}
    </div>
  );

  return (
    <aside className="hidden w-[248px] shrink-0 select-none flex-col border-r border-line bg-canvas min-[1120px]:flex xl:w-[264px]">
      <div className="flex-1 space-y-5 overflow-y-auto p-3.5">
        {/* Boards */}
        <nav>
          <SectionLabel>{t.boardsHeader}</SectionLabel>
          <div className="space-y-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = category === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => setCategory(item.key)}
                  className={`flex h-9 w-full items-center justify-between rounded-[9px] px-2.5 text-body transition ${
                    active
                      ? 'bg-white font-semibold text-ink shadow-card ring-1 ring-line'
                      : 'font-medium text-muted hover:bg-accent-soft hover:text-ink'
                  }`}
                >
                  <span className="flex min-w-0 items-center gap-2.5">
                    <Icon
                      className={`h-4 w-4 shrink-0 ${active ? 'text-ink' : 'text-faint'}`}
                    />
                    <span className="truncate">{item.label}</span>
                  </span>
                  <span
                    className={`shrink-0 text-meta tabular-nums ${
                      active ? 'text-muted' : 'text-faint'
                    }`}
                  >
                    {item.count}
                  </span>
                </button>
              );
            })}
          </div>
        </nav>

        {/* Eligibility filter */}
        <div className="rounded-card border border-line bg-white p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 text-body font-semibold text-ink">
                <Filter className="h-3.5 w-3.5 text-muted" />
                <span className="truncate">{t.onlyEligibleLabel}</span>
              </div>
              <p className="mt-1 text-meta leading-4 text-faint">
                {t.onlyEligibleSub(ineligibleCount)}
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={onlyEligible}
              onClick={() => setOnlyEligible(!onlyEligible)}
              className={`relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition ${
                onlyEligible ? 'bg-ink' : 'bg-zinc-200'
              }`}
            >
              <span
                className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-all ${
                  onlyEligible ? 'left-[18px]' : 'left-0.5'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Academic profile */}
        <section>
          <SectionLabel>{t.profileHeader}</SectionLabel>
          <div className="space-y-2.5 rounded-card border border-line bg-white p-3">
            <div>
              <label className="mb-1 block text-meta text-faint">{t.lblCampus}</label>
              <select
                value={profile.campus}
                onChange={(e) => updateField('campus', e.target.value)}
                className="field"
              >
                {Object.entries(t.campuses).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-meta text-faint">{t.lblStatus}</label>
              <select
                value={profile.status}
                onChange={(e) => updateField('status', e.target.value)}
                className="field"
              >
                {Object.entries(t.statuses).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="mb-1.5 flex items-baseline justify-between">
                <label className="text-meta text-faint">{t.lblGpa}</label>
                <span className="text-meta font-semibold tabular-nums text-ink">
                  {Number(profile.gpa).toFixed(1)} / 4.5
                </span>
              </div>
              <input
                type="range"
                min="1.5"
                max="4.5"
                step="0.1"
                value={profile.gpa}
                onChange={(e) => updateField('gpa', parseFloat(e.target.value))}
                className="w-full"
              />
            </div>

            <div>
              <label className="mb-1 block text-meta text-faint">{t.lblIncome}</label>
              <select
                value={profile.income_bracket}
                onChange={(e) => updateField('income_bracket', parseInt(e.target.value, 10))}
                className="field"
              >
                {Object.entries(t.incomes).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="min-w-0">
                <label className="mb-1 block text-meta text-faint">{t.lblDept}</label>
                <input
                  type="text"
                  value={profile.department}
                  onChange={(e) => updateField('department', e.target.value)}
                  className="field"
                />
              </div>
              <div className="min-w-0">
                <label className="mb-1 block text-meta text-faint">{t.lblGrade}</label>
                <select
                  value={profile.grade}
                  onChange={(e) => updateField('grade', parseInt(e.target.value, 10))}
                  className="field"
                >
                  {Object.entries(t.grades).map(([val, label]) => (
                    <option key={val} value={val}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Footer */}
      <div className="border-t border-line p-3">
        <button
          onClick={onRefresh}
          disabled={loading}
          className="inline-flex h-9 w-full items-center justify-center gap-2 rounded-control bg-white text-label font-medium text-ink ring-1 ring-line transition hover:ring-ink/25 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>{t.btnRefresh}</span>
        </button>
      </div>
    </aside>
  );
}
