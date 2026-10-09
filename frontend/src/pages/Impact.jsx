import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { getCampusStats } from "../api/client";

const MATERIAL_DISPLAY = {
  pet_bottle: "PET Bottles",
  aluminium_can: "Aluminium Cans",
  rigid_plastic: "Rigid Plastic",
  snack_wrapper: "Snack Wrappers",
  non_recyclable: "Other / Flagged",
};

const BAR_COLORS = ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444"];

export default function Impact() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const fetchStats = async () => {
    try {
      setLoading(true);
      setErrorMessage("");
      const data = await getCampusStats();
      setStats(data);
    } catch (err) {
      console.error("Failed to load campus stats:", err);
      setErrorMessage(err.message || "Could not retrieve campus impact data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const totalKg = stats ? (stats.totalGrams / 1000).toFixed(2) : "0.00";
  const totalItems = stats ? stats.totalItems : 0;
  // Estimate rupee rewards generated (e.g., approx 100 pts per 100g = ₹1 per 100g = ₹10/kg)
  const rupeesGenerated = stats ? (stats.totalGrams / 100).toFixed(0) : "0";

  // Prepare data for Recharts BarChart
  const countsByMaterial = stats?.countsByMaterial || {};
  const chartData = Object.keys(countsByMaterial).map((key) => ({
    name: MATERIAL_DISPLAY[key] || key.replace("_", " "),
    count: countsByMaterial[key] || 0,
  }));

  // Fallback if chartData is empty
  const hasChartData = chartData.some((d) => d.count > 0);

  const leaderboard = stats?.leaderboard || [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl">
            Campus Recycling Impact
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Real-time analytics and environmental metrics powered by CampusCycle reverse vending machines.
          </p>
        </div>
        <button
          onClick={fetchStats}
          disabled={loading}
          className="self-start sm:self-auto inline-flex items-center px-3.5 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50"
        >
          🔄 Refresh Analytics
        </button>
      </div>

      {errorMessage && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700 flex items-center justify-between">
          <span>{errorMessage}</span>
          <button onClick={fetchStats} className="font-semibold underline ml-3">
            Retry
          </button>
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
        {/* Total kg Diverted */}
        <div className="bg-gradient-to-br from-emerald-600 to-teal-700 rounded-2xl p-6 text-white shadow-md">
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-100">
            Diverted from Landfill
          </p>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold tracking-tight">
              {loading ? "..." : totalKg}
            </span>
            <span className="text-emerald-100 text-base font-semibold">kg</span>
          </div>
          <p className="mt-2 text-xs text-emerald-100/90">
            Total verified weight of segregated waste
          </p>
        </div>

        {/* Total Items Recycled */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Total Items Diverted
          </p>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold text-slate-900 tracking-tight">
              {loading ? "..." : totalItems}
            </span>
            <span className="text-slate-500 text-base font-semibold">items</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">Bottles, cans, and wrappers</p>
        </div>

        {/* Value Generated */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Student Rewards Generated
          </p>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold text-slate-900 tracking-tight">
              {loading ? "..." : `₹${rupeesGenerated}`}
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400">Total campus reward value distributed</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Materials Breakdown Chart (Left 7 Cols) */}
        <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h2 className="text-base font-bold text-slate-900 mb-1">
            Recycled Waste by Material
          </h2>
          <p className="text-xs text-slate-500 mb-6">
            Item counts categorized by Gemini vision AI
          </p>

          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : hasChartData ? (
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis
                    dataKey="name"
                    stroke="#94a3b8"
                    fontSize={11}
                    tickLine={false}
                    interval={0}
                    angle={-15}
                    textAnchor="end"
                  />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border: "none",
                      borderRadius: "8px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                    cursor={{ fill: "rgba(241, 245, 249, 0.6)" }}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-slate-400 text-xs">
              <span className="text-3xl mb-2">📊</span>
              <span>No categorized items recorded yet.</span>
            </div>
          )}
        </div>

        {/* Top 5 Leaderboard (Right 5 Cols) */}
        <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-base font-bold text-slate-900">
              Campus Leaderboard
            </h2>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">
              Top 5
            </span>
          </div>
          <p className="text-xs text-slate-500 mb-6">
            Ranked by total mass diverted (masked for privacy)
          </p>

          {loading ? (
            <div className="p-8 text-center">
              <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            </div>
          ) : leaderboard.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              <span className="text-3xl mb-2 block">🏆</span>
              <span>No active recyclers on the leaderboard yet.</span>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {leaderboard.map((entry) => {
                const isTop3 = entry.rank <= 3;
                const medal =
                  entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : null;

                return (
                  <div
                    key={entry.rank}
                    className="py-3 flex items-center justify-between hover:bg-slate-50/50 rounded-lg px-2 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                          isTop3
                            ? "bg-amber-100 text-amber-800"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {medal || entry.rank}
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-900">
                          {entry.displayName}
                        </p>
                        <p className="text-[11px] text-slate-400">
                          {entry.totalItems} items recycled
                        </p>
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="text-xs font-extrabold text-emerald-700">
                        {(entry.totalGrams / 1000).toFixed(2)} kg
                      </p>
                      <p className="text-[10px] text-slate-400">
                        {entry.totalGrams} g
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
