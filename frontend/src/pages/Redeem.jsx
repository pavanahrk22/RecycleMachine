import React, { useState, useEffect } from "react";
import { getMyProfile, redeemPoints } from "../api/client";

export default function Redeem() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [redeeming, setRedeeming] = useState(false);
  const [selectedPoints, setSelectedPoints] = useState(100);
  const [redeemResult, setRedeemResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [copied, setCopied] = useState(false);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setErrorMessage("");
      const data = await getMyProfile();
      setProfile(data);
      // Default to 100 or full available multiple
      const bal = data?.pointsBalance || 0;
      if (bal >= 100) {
        setSelectedPoints(100);
      }
    } catch (err) {
      console.error("Failed to load profile for redeem:", err);
      setErrorMessage(err.message || "Could not retrieve user balance.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const points = profile?.pointsBalance || 0;
  const canRedeem = points >= 100;
  const maxMultiple = Math.floor(points / 100) * 100;

  const handleRedeem = async () => {
    if (!canRedeem || redeeming) return;
    try {
      setRedeeming(true);
      setErrorMessage("");
      const res = await redeemPoints(selectedPoints);
      setRedeemResult(res);
      // Update local profile balance
      setProfile((prev) => (prev ? { ...prev, pointsBalance: res.newBalance } : prev));
    } catch (err) {
      console.error("Redemption error:", err);
      setErrorMessage(err.message || "Failed to redeem points. Please try again.");
    } finally {
      setRedeeming(false);
    }
  };

  const handleCopyCode = (code) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl">
          Redeem Campus Rewards
        </h1>
        <p className="mt-2 text-base text-slate-600">
          Convert your verified recycling points into campus store and canteen coupons.
        </p>
      </div>

      {/* Balance Card */}
      <div className="bg-gradient-to-br from-emerald-600 to-teal-700 rounded-2xl p-6 text-white shadow-md mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-100">
              Available Balance
            </p>
            <div className="mt-2 flex items-baseline space-x-2">
              <span className="text-4xl font-extrabold tracking-tight">
                {loading ? "..." : points}
              </span>
              <span className="text-emerald-100 text-sm font-medium">Points</span>
            </div>
            <p className="mt-1 text-xs text-emerald-100/90">
              Equivalent to ₹{(points / 100).toFixed(2)} (100 pts = ₹1)
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-3 border border-white/20 text-xs space-y-1">
            <p className="font-semibold text-white">Redemption Policy:</p>
            <p className="text-emerald-100">• Minimum redemption: 100 points</p>
            <p className="text-emerald-100">• Valid at Campus Canteen & Stores</p>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700 flex items-start space-x-2">
          <span className="text-lg">⚠️</span>
          <div className="flex-1">
            <p className="font-semibold">Redemption Notice</p>
            <p className="mt-0.5">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Success Coupon Card */}
      {redeemResult && (
        <div className="mb-8 p-6 rounded-2xl bg-emerald-50 border-2 border-emerald-300 shadow-md text-emerald-950">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold text-lg">
              ✓
            </div>
            <div>
              <h2 className="text-lg font-bold">Reward Coupon Issued!</h2>
              <p className="text-xs text-emerald-700">
                Redeemed {redeemResult.pointsRedeemed} pts for ₹{redeemResult.rupees} value.
              </p>
            </div>
          </div>

          <div className="p-4 bg-white rounded-xl border border-emerald-200 flex flex-col sm:flex-row items-center justify-between gap-3 my-4">
            <div className="text-center sm:text-left">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Your Coupon Code
              </p>
              <p className="text-2xl font-mono font-extrabold text-emerald-700 tracking-wider">
                {redeemResult.couponCode}
              </p>
            </div>
            <button
              onClick={() => handleCopyCode(redeemResult.couponCode)}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg shadow-sm transition-colors cursor-pointer"
            >
              {copied ? "✓ Copied!" : "📋 Copy Code"}
            </button>
          </div>

          <p className="text-xs text-slate-500 text-center">
            Present this code at participating campus counters or canteen checkout. New balance:{" "}
            <span className="font-bold text-emerald-800">{redeemResult.newBalance} pts</span>.
          </p>
        </div>
      )}

      {/* Redemption Form */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <h2 className="text-base font-bold text-slate-900 mb-2">Redeem Points for Coupons</h2>
        <p className="text-xs text-slate-500 mb-6">
          Select points in multiples of 100 to convert into discount coupons.
        </p>

        {canRedeem ? (
          <div className="space-y-6">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                Choose Amount to Redeem:
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[100, 200, 500, maxMultiple].filter((val, idx, arr) => val <= maxMultiple && arr.indexOf(val) === idx).map((amt) => (
                  <button
                    key={amt}
                    type="button"
                    onClick={() => setSelectedPoints(amt)}
                    className={`py-3 px-4 rounded-xl border text-center transition-all ${
                      selectedPoints === amt
                        ? "bg-emerald-50 border-emerald-500 ring-2 ring-emerald-500 text-emerald-900 font-bold"
                        : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100"
                    }`}
                  >
                    <p className="text-base font-extrabold">{amt} pts</p>
                    <p className="text-xs text-slate-500">₹{amt / 100}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-800">
                  Redeeming: <span className="text-emerald-600">{selectedPoints} Points</span>
                </p>
                <p className="text-xs text-slate-500">
                  Value: ₹{selectedPoints / 100}
                </p>
              </div>

              <button
                onClick={handleRedeem}
                disabled={redeeming || selectedPoints > points}
                className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 text-white font-bold text-sm rounded-xl shadow-md transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {redeeming ? "Generating Coupon..." : "Redeem Now"}
              </button>
            </div>
          </div>
        ) : (
          <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
            <span className="text-3xl block mb-2">🎟️</span>
            <p className="font-bold text-slate-700 text-sm">Need at least 100 points</p>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              You currently have <span className="font-semibold">{points} points</span>. Deposit a few more bottles or cans at the Kiosk to unlock coupons!
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
