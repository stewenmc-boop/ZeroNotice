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

  const updateField = (field, value) => {
    onChangeProfile({ ...profile, [field]: value });
  };

  return (
    <aside className="w-64 border-r border-zinc-200 bg-zinc-50/70 flex flex-col justify-between overflow-y-auto shrink-0 p-4 select-none">
      <div className="space-y-5">
        {/* 1. Board Navigation */}
        <div className="space-y-1">
          <div className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
            {t.boardsHeader}
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = category === item.key;
            return (
              <button
                key={item.key}
                onClick={() => setCategory(item.key)}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition ${
                  active
                    ? 'bg-zinc-900 text-white shadow-xs'
                    : 'text-zinc-600 hover:bg-zinc-200/60 hover:text-zinc-950'
                }`}
              >
                <span className="flex items-center gap-2 truncate">
                  <Icon className="w-3.5 h-3.5 shrink-0 opacity-80" />
                  <span className="truncate">{item.label}</span>
                </span>
                <span
                  className={`tabular-nums text-[11px] ${
                    active ? 'text-zinc-300' : 'text-zinc-400'
                  }`}
                >
                  {item.count}
                </span>
              </button>
            );
          })}
        </div>

        {/* 2. Smart Eligibility Filter Toggle */}
        <div className="pt-3 border-t border-zinc-200/80">
          <label className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-zinc-200/50 cursor-pointer transition">
            <span className="flex items-center gap-1.5 text-xs font-medium text-zinc-800">
              <Filter className="w-3.5 h-3.5 text-zinc-500" />
              <span>{t.onlyEligibleLabel}</span>
            </span>
            <input
              type="checkbox"
              checked={onlyEligible}
              onChange={(e) => setOnlyEligible(e.target.checked)}
              className="accent-zinc-950 w-4 h-4 rounded cursor-pointer"
            />
          </label>
          <p className="px-2 text-[11px] text-zinc-400 mt-0.5 leading-snug">
            {t.onlyEligibleSub(ineligibleCount)}
          </p>
        </div>

        {/* 3. My Academic Profile Controls */}
        <div className="pt-3 border-t border-zinc-200/80 space-y-3">
          <div className="px-1 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
              {t.profileHeader}
            </span>
          </div>

          <div className="space-y-2.5 text-xs">
            {/* Campus */}
            <div>
              <label className="block text-zinc-500 mb-1">{t.lblCampus}</label>
              <select
                value={profile.campus}
                onChange={(e) => updateField('campus', e.target.value)}
                className="w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 font-medium text-zinc-900 focus:outline-none focus:border-zinc-900"
              >
                {Object.entries(t.campuses).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* Enrollment Status */}
            <div>
              <label className="block text-zinc-500 mb-1">{t.lblStatus}</label>
              <select
                value={profile.status}
                onChange={(e) => updateField('status', e.target.value)}
                className="w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 font-medium text-zinc-900 focus:outline-none focus:border-zinc-900"
              >
                {Object.entries(t.statuses).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* GPA Slider */}
            <div>
              <label className="block text-zinc-500 mb-1 flex justify-between">
                <span>{t.lblGpa}</span>
                <span className="font-semibold text-zinc-950 tabular-nums">
                  {Number(profile.gpa).toFixed(1)} / 4.5
                </span>
              </label>
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

            {/* Income Bracket */}
            <div>
              <label className="block text-zinc-500 mb-1">{t.lblIncome}</label>
              <select
                value={profile.income_bracket}
                onChange={(e) => updateField('income_bracket', parseInt(e.target.value, 10))}
                className="w-full rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 font-medium text-zinc-900 focus:outline-none focus:border-zinc-900"
              >
                {Object.entries(t.incomes).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* Department & Grade */}
            <div className="grid grid-cols-2 gap-1.5">
              <div>
                <label className="block text-zinc-500 mb-1">{t.lblDept}</label>
                <input
                  type="text"
                  value={profile.department}
                  onChange={(e) => updateField('department', e.target.value)}
                  className="w-full rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-xs font-medium text-zinc-900 focus:outline-none focus:border-zinc-900"
                />
              </div>
              <div>
                <label className="block text-zinc-500 mb-1">{t.lblGrade}</label>
                <select
                  value={profile.grade}
                  onChange={(e) => updateField('grade', parseInt(e.target.value, 10))}
                  className="w-full rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-xs font-medium text-zinc-900 focus:outline-none focus:border-zinc-900"
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
        </div>
      </div>

      {/* Live Sync Button */}
      <div className="pt-4 border-t border-zinc-200/80">
        <button
          onClick={onRefresh}
          disabled={loading}
          className="w-full py-2 px-3 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-100 text-xs font-medium text-zinc-800 flex items-center justify-center gap-2 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>{t.btnRefresh}</span>
        </button>
      </div>
    </aside>
  );
}

