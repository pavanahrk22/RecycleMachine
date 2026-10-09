import React, { useEffect, useState } from "react";
import { getMyProfile, getMyDrops } from "../api/client";

const MATERIAL_LABELS = {
  pet_bottle: "PET Bottle",
  aluminium_can: "Aluminium Can",
  rigid_plastic: "Rigid Plastic",
  snack_wrapper: "Snack Wrapper",
  non_recyclable: "Non-Recyclable",
  no_item: "No Item",
  flagged_drop: "Flagged Drop",
};

export default function Wallet() {
  const [profile, setProfile] = useState(null);
  const [drops, setDrops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  const fetchData = async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const [profileData, dropsData] = await Promise.all([
        getMyProfile(),
        getMyDrops(20),
      ]);
      setProfile(profileData);
      setDrops(dropsData?.drops || []);
    } catch (err) {
      console.error("Wallet data fetch error:", err);
      setErrorMsg(err.message || "Failed to load wallet data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const points = profile?.pointsBalance || 0;
  // 100 points = ₹1 conversion from PRD
  const rupeeValue = (points / 100).toFixed(2);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Student Recycling Wallet
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Track your recycling points, environmental impact, and recent drops.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="self-start sm:self-auto inline-flex items-center px-3.5 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50"
        >
          🔄 Refresh
        </button>
      </div>

      {errorMsg && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700 flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={fetchData} className="font-semibold underline ml-3">
            Retry
          </button>
        </div>
      )}

      {/* Balance & Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
        {/* Balance Card */}
        <div className="bg-gradient-to-br from-emerald-600 to-teal-700 rounded-2xl p-6 text-white shadow-md sm:col-span-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-100">
            Current Balance
          </p>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-4xl font-extrabold tracking-tight">
              {loading ? "..." : points}
            </span>
            <span className="text-emerald-100 text-sm font-medium">Points</span>
          </div>
          <p className="mt-2 text-xs text-emerald-100/90 flex items-center space-x-1">
            <span>≈ ₹{rupeeValue}</span>
            <span className="opacity-75">(100 pts = ₹1)</span>
          </p>
        </div>

        {/* Total Diverted Card */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Plastic Diverted
          </p>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
              {loading ? "..." : ((profile?.totalGrams || 0) / 1000).toFixed(2)}
            </span>
            <span className="text-slate-500 text-sm font-medium">kg</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            {profile?.totalGrams || 0} grams recorded
          </p>
        </div>

        {/* Total Items Recycled Card */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Items Recycled
          </p>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
              {loading ? "..." : profile?.totalItems || 0}
            </span>
            <span className="text-slate-500 text-sm font-medium">items</span>
          </div>
          <p className="mt-2 text-xs text-slate-400">Total accepted deposits</p>
        </div>
      </div>

      {/* Recent Drops History */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900">
            Recent Recycling Activity (Last 20)
          </h2>
          <span className="text-xs text-slate-500">{drops.length} records</span>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="mt-3 text-xs text-slate-500">Loading history...</p>
          </div>
        ) : drops.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p className="text-4xl mb-3">📦</p>
            <p className="font-semibold text-slate-700">No recycling activity yet</p>
            <p className="text-xs mt-1 text-slate-400">
              Visit the Kiosk to deposit your first item and start earning rewards!
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100 overflow-x-auto">
            {drops.map((drop) => {
              const isAccepted = drop.status === "accepted";
              const formattedDate = drop.createdAt
                ? new Date(drop.createdAt).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "Recent";

              return (
                <div
                  key={drop.id}
                  className="px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 hover:bg-slate-50/50 transition-colors"
                >
                  <div className="flex items-start space-x-3">
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0 mt-0.5 ${
                        isAccepted
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {isAccepted ? "✓" : "✕"}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-slate-900 text-sm capitalize">
                          {MATERIAL_LABELS[drop.material] || drop.material}
                        </span>
                        <span
                          className={`px-2 py-0.5 text-[10px] font-bold rounded-full uppercase tracking-wider ${
                            isAccepted
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-red-50 text-red-700 border border-red-200"
                          }`}
                        >
                          {drop.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {drop.weightG}g • {formattedDate}
                      </p>
                      {!isAccepted && drop.rejectReason && (
                        <p className="text-xs text-red-600 mt-1 font-medium">
                          Reason: {drop.rejectReason}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="text-left sm:text-right flex-shrink-0 pl-12 sm:pl-0">
                    <div
                      className={`text-sm font-extrabold ${
                        isAccepted ? "text-emerald-600" : "text-slate-400"
                      }`}
                    >
                      {isAccepted ? `+${drop.points} pts` : "0 pts"}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono truncate max-w-[120px]">
                      {drop.id}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
