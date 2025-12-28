"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Card } from "@/components/ui/Card";
import { useAthleteContext } from "@/hooks/useAthleteContext";
import type { RaceGoalInfo, TrainingPace } from "@/lib/types";

export default function GoalsPage() {
  const t = useTranslations("goals");
  const { data: context, isLoading } = useAthleteContext();
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({ distance: "10k", targetTime: "", raceDate: "" });

  const goals: RaceGoalInfo[] = context?.race_goals || [];
  const paces: TrainingPace[] = context?.training_paces || [];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Creating goal:", formData);
    setShowAddForm(false);
    setFormData({ distance: "10k", targetTime: "", raceDate: "" });
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="h-8 w-48 bg-gray-800 rounded animate-pulse mb-8" />
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl h-32 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-white mb-6">{t("title")}</h1>

      {/* Inline Add Goal Form */}
      <button
        onClick={() => setShowAddForm(!showAddForm)}
        className="w-full mb-4 p-3 border border-dashed border-gray-700 rounded-xl text-gray-400 hover:border-teal-500 hover:text-teal-400 transition-colors flex items-center justify-center gap-2"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={showAddForm ? "M6 18L18 6M6 6l12 12" : "M12 4v16m8-8H4"} />
        </svg>
        {showAddForm ? t("cancel") : t("addGoal")}
      </button>

      {showAddForm && (
        <Card className="mb-6">
          <form onSubmit={handleSubmit} className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[120px]">
              <label className="block text-xs text-gray-400 mb-1">{t("distance")}</label>
              <select
                value={formData.distance}
                onChange={(e) => setFormData({ ...formData, distance: e.target.value })}
                className="w-full bg-gray-800 text-white px-3 py-2 rounded border border-gray-700 focus:border-teal-500 focus:outline-none text-sm"
              >
                <option value="5k">5K</option>
                <option value="10k">10K</option>
                <option value="half_marathon">Half Marathon</option>
                <option value="marathon">Marathon</option>
              </select>
            </div>
            <div className="flex-1 min-w-[120px]">
              <label className="block text-xs text-gray-400 mb-1">{t("targetTime")}</label>
              <input
                type="text"
                value={formData.targetTime}
                onChange={(e) => setFormData({ ...formData, targetTime: e.target.value })}
                placeholder={t("timePlaceholder")}
                className="w-full bg-gray-800 text-white px-3 py-2 rounded border border-gray-700 focus:border-teal-500 focus:outline-none text-sm"
              />
            </div>
            <div className="flex-1 min-w-[140px]">
              <label className="block text-xs text-gray-400 mb-1">{t("raceDate")}</label>
              <input
                type="date"
                value={formData.raceDate}
                onChange={(e) => setFormData({ ...formData, raceDate: e.target.value })}
                className="w-full bg-gray-800 text-white px-3 py-2 rounded border border-gray-700 focus:border-teal-500 focus:outline-none text-sm"
              />
            </div>
            <button type="submit" className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded font-medium text-sm transition-colors">
              {t("save")}
            </button>
          </form>
        </Card>
      )}

      {/* Goals List */}
      {goals.length === 0 ? (
        <Card className="text-center py-10">
          <svg className="w-12 h-12 mx-auto text-gray-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h2 className="text-lg font-medium text-white mb-1">{t("noGoals")}</h2>
          <p className="text-gray-400 text-sm">{t("noGoalsDesc")}</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {goals.map((goal, index) => (
            <GoalCard key={index} goal={goal} isPrimary={index === 0} paces={index === 0 ? paces : []} />
          ))}
        </div>
      )}
    </div>
  );
}

function GoalCard({ goal, isPrimary, paces }: { goal: RaceGoalInfo; isPrimary: boolean; paces: TrainingPace[] }) {
  const weeksColor = goal.weeks_remaining <= 4 ? "text-red-400" : goal.weeks_remaining <= 8 ? "text-yellow-400" : "text-teal-400";
  const raceDate = new Date(goal.race_date);
  const dateStr = raceDate.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

  return (
    <Card className={`relative ${isPrimary ? "ring-1 ring-teal-500/50" : ""}`} variant="interactive">
      {isPrimary && <span className="absolute top-3 right-3 text-xs text-teal-400 font-medium">Primary</span>}

      <div className="flex items-baseline gap-4 mb-2">
        <span className="text-2xl font-bold text-white">{goal.distance}</span>
        <span className="text-xl font-mono text-teal-400">{goal.target_time_formatted}</span>
        <span className="text-sm text-gray-500">{goal.target_pace_formatted}</span>
      </div>

      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-400">{dateStr}</span>
        <span className={`font-medium ${weeksColor}`}>{goal.weeks_remaining}w to go</span>
      </div>

      {/* Training Paces (only on primary goal) */}
      {paces.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Training Paces</div>
          <div className="grid grid-cols-3 gap-2 text-sm">
            {paces.slice(0, 6).map((pace) => (
              <div key={pace.name} className="flex justify-between">
                <span className="text-gray-400">{pace.name}</span>
                <span className="font-mono text-white">{pace.pace_formatted}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
