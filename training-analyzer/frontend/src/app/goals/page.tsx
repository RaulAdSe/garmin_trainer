"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { useAthleteContext } from "@/hooks/useAthleteContext";
import type { RaceGoalInfo } from "@/lib/types";

export default function GoalsPage() {
  const { data: context, isLoading } = useAthleteContext();
  const [isAddingGoal, setIsAddingGoal] = useState(false);

  // Goals from athlete context
  const goals: RaceGoalInfo[] = context?.race_goals || [];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Race Goals</h1>
          <p className="text-gray-400 mt-1">
            Track your upcoming races and training targets
          </p>
        </div>
        <button
          onClick={() => setIsAddingGoal(true)}
          className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
        >
          Add Goal
        </button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl animate-pulse h-48" />
          ))}
        </div>
      ) : goals.length === 0 ? (
        <Card className="text-center py-12">
          <div className="text-6xl mb-4">?</div>
          <h2 className="text-xl font-semibold text-white mb-2">No Goals Set</h2>
          <p className="text-gray-400 mb-4">
            Add your first race goal to start tracking your training progress
          </p>
          <button
            onClick={() => setIsAddingGoal(true)}
            className="bg-teal-600 hover:bg-teal-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
          >
            Set Your First Goal
          </button>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {goals.map((goal, index) => (
            <GoalCard key={index} goal={goal} isPrimary={index === 0} />
          ))}
        </div>
      )}

      {/* Training Paces Section */}
      {context?.training_paces && (
        <div className="mt-12">
          <h2 className="text-2xl font-bold text-white mb-6">Training Paces</h2>
          <Card>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {Object.entries(context.training_paces).map(([type, pace]) => (
                <div key={type} className="text-center">
                  <div className="text-sm text-gray-400 uppercase tracking-wide">
                    {type}
                  </div>
                  <div className="text-xl font-mono text-teal-400 mt-1">
                    {typeof pace === 'string' ? pace : `${pace}/km`}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Add Goal Modal */}
      {isAddingGoal && (
        <AddGoalModal onClose={() => setIsAddingGoal(false)} />
      )}
    </div>
  );
}

function GoalCard({
  goal,
  isPrimary,
}: {
  goal: RaceGoalInfo;
  isPrimary: boolean;
}) {
  const weeksColor =
    goal.weeks_remaining <= 4
      ? "text-red-400"
      : goal.weeks_remaining <= 8
      ? "text-yellow-400"
      : "text-green-400";

  return (
    <Card
      className={`relative overflow-hidden ${
        isPrimary ? "ring-2 ring-teal-500" : ""
      }`}
    >
      {isPrimary && (
        <div className="absolute top-0 right-0 bg-teal-600 text-white text-xs px-2 py-1 rounded-bl-lg font-medium">
          Primary
        </div>
      )}

      <div className="text-center">
        <div className="text-2xl font-bold text-white">{goal.distance}</div>
        <div className="text-3xl font-mono text-teal-400 mt-2">
          {goal.target_time_formatted}
        </div>
        <div className="text-sm text-gray-400 mt-1">
          {goal.target_pace_formatted}
        </div>

        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="text-sm text-gray-400">Race Date</div>
          <div className="text-white font-medium">
            {new Date(goal.race_date).toLocaleDateString("en-US", {
              weekday: "long",
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </div>
          <div className={`text-lg font-bold mt-2 ${weeksColor}`}>
            {goal.weeks_remaining} weeks remaining
          </div>
        </div>

        {/* Progress bar placeholder */}
        <div className="mt-4">
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-teal-500 transition-all"
              style={{
                width: `${Math.min(
                  100,
                  Math.max(0, ((16 - goal.weeks_remaining) / 16) * 100)
                )}%`,
              }}
            />
          </div>
          <div className="text-xs text-gray-400 mt-1">Training progress</div>
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <button className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition-colors">
          Edit
        </button>
        <button className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded text-sm transition-colors">
          View Plan
        </button>
      </div>
    </Card>
  );
}

function AddGoalModal({ onClose }: { onClose: () => void }) {
  const [formData, setFormData] = useState({
    distance: "10k",
    targetTime: "",
    raceDate: "",
    raceName: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Call API to create goal
    console.log("Creating goal:", formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md mx-4">
        <h2 className="text-xl font-bold text-white mb-4">Add Race Goal</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Race Name (optional)
            </label>
            <input
              type="text"
              value={formData.raceName}
              onChange={(e) =>
                setFormData({ ...formData, raceName: e.target.value })
              }
              placeholder="e.g., Boston Marathon"
              className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-teal-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Distance</label>
            <select
              value={formData.distance}
              onChange={(e) =>
                setFormData({ ...formData, distance: e.target.value })
              }
              className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-teal-500 focus:outline-none"
            >
              <option value="5k">5K</option>
              <option value="10k">10K</option>
              <option value="half_marathon">Half Marathon</option>
              <option value="marathon">Marathon</option>
              <option value="50k">50K</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Target Time
            </label>
            <input
              type="text"
              value={formData.targetTime}
              onChange={(e) =>
                setFormData({ ...formData, targetTime: e.target.value })
              }
              placeholder="e.g., 3:30:00 or 45:00"
              className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-teal-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Race Date
            </label>
            <input
              type="date"
              value={formData.raceDate}
              onChange={(e) =>
                setFormData({ ...formData, raceDate: e.target.value })
              }
              className="w-full bg-gray-700 text-white px-3 py-2 rounded border border-gray-600 focus:border-teal-500 focus:outline-none"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded font-medium transition-colors"
            >
              Add Goal
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
}
