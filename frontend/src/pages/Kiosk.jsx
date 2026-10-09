import React, { useState, useRef, useEffect } from "react";
import { dropItem, ApiError } from "../api/client";

const COOLDOWN_SECONDS = 12;

const MATERIAL_LABELS = {
  pet_bottle: "PET Bottle",
  aluminium_can: "Aluminium Can",
  rigid_plastic: "Rigid Plastic",
  snack_wrapper: "Snack Wrapper",
  non_recyclable: "Non-Recyclable Item",
  no_item: "No Item Detected",
  flagged_drop: "Flagged Drop",
};

export default function Kiosk() {
  const [stream, setStream] = useState(null);
  const [cameraError, setCameraError] = useState("");
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);

  // Simulated load cell reading in grams (default 20.0g)
  const [weightG, setWeightG] = useState(20.0);

  // Submission & cooldown state
  const [submitting, setSubmitting] = useState(false);
  const [cooldownRemaining, setCooldownRemaining] = useState(0);

  // Response & Error State
  const [dropResult, setDropResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isRetryable, setIsRetryable] = useState(false);

  const videoRef = useRef(null);
  const streamRef = useRef(null);

  // Start webcam stream
  const startCamera = async () => {
    setCameraError("");
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = mediaStream;
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.warn("Camera access denied or unavailable:", err);
      setCameraError("Camera unavailable or permission denied. Please use the file upload fallback.");
    }
  };

  useEffect(() => {
    startCamera();
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Sync stream to video element when stream is ready
  useEffect(() => {
    if (videoRef.current && stream && !capturedBlob) {
      videoRef.current.srcObject = stream;
    }
  }, [stream, capturedBlob]);

  // Handle 12-second countdown timer
  useEffect(() => {
    if (cooldownRemaining <= 0) return;
    const timer = setInterval(() => {
      setCooldownRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldownRemaining]);

  // Capture frame from webcam
  const handleCapture = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          setCapturedBlob(blob);
          setPreviewUrl(URL.createObjectURL(blob));
          setDropResult(null);
          setErrorMessage("");
        }
      },
      "image/jpeg",
      0.9
    );
  };

  // Fallback file upload handler
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setCapturedBlob(file);
    setPreviewUrl(URL.createObjectURL(file));
    setDropResult(null);
    setErrorMessage("");
  };

  const handleRetake = () => {
    setCapturedBlob(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    setDropResult(null);
    setErrorMessage("");
    if (!stream) {
      startCamera();
    }
  };

  // Submit drop to backend
  const handleDrop = async () => {
    if (!capturedBlob) {
      setErrorMessage("Please capture or upload a photo of the item first.");
      return;
    }

    if (cooldownRemaining > 0 || submitting) return;

    try {
      setSubmitting(true);
      setErrorMessage("");
      setDropResult(null);
      setIsRetryable(false);

      const response = await dropItem({
        imageBlob: capturedBlob,
        weightG: Number(weightG),
        machineId: "sim-machine-01",
      });

      setDropResult(response);

      // Start cooldown after every drop attempt
      setCooldownRemaining(COOLDOWN_SECONDS);
    } catch (err) {
      console.error("Drop request error:", err);
      const isRetry = err instanceof ApiError ? err.retryable : true;
      setIsRetryable(isRetry);
      setErrorMessage(err.message || "Failed to process item drop. Please try again.");
      // Apply cooldown if error occurred
      setCooldownRemaining(COOLDOWN_SECONDS);
    } finally {
      setSubmitting(false);
    }
  };

  const isButtonDisabled = submitting || cooldownRemaining > 0 || !capturedBlob;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl">
          Recycling Machine Kiosk
        </h1>
        <p className="mt-2 text-base text-slate-600">
          Hold your item up to the camera and set the simulated load cell reading.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Camera / Capture Card */}
        <div className="lg:col-span-7 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-4 bg-slate-900 flex justify-between items-center text-white">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Chute Camera Simulator
              </span>
            </div>
            {capturedBlob && (
              <button
                onClick={handleRetake}
                className="text-xs bg-slate-800 hover:bg-slate-700 px-2.5 py-1 rounded text-slate-200 transition-colors"
              >
                🔄 Retake
              </button>
            )}
          </div>

          <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
            {capturedBlob ? (
              <img
                src={previewUrl}
                alt="Captured recyclable"
                className="w-full h-full object-contain bg-slate-950"
              />
            ) : cameraError ? (
              <div className="p-6 text-center text-slate-400">
                <p className="text-sm mb-3">{cameraError}</p>
                <label className="inline-flex items-center px-4 py-2 border border-slate-600 rounded-lg text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 cursor-pointer">
                  Choose Photo File
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>
            ) : (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
            )}
          </div>

          {/* Camera controls footer */}
          <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
            {!capturedBlob ? (
              <div className="flex items-center space-x-3 w-full sm:w-auto">
                <button
                  onClick={handleCapture}
                  disabled={!stream}
                  className="flex-1 sm:flex-initial inline-flex items-center justify-center px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl shadow-sm transition-colors cursor-pointer"
                >
                  📸 Capture Photo
                </button>
                <label className="flex-1 sm:flex-initial inline-flex items-center justify-center px-4 py-2.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium rounded-xl shadow-sm transition-colors cursor-pointer">
                  📁 Upload File
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>
            ) : (
              <div className="flex items-center space-x-2 text-xs text-emerald-700 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>Photo captured and ready for analysis</span>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Weight Simulator & Drop Button */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-5">
            <div>
              <label className="block text-sm font-bold text-slate-800 mb-1">
                Load cell reading (simulated)
              </label>
              <p className="text-xs text-slate-500 mb-4">
                Simulates real hardware scale module (grams)
              </p>

              <div className="flex items-center space-x-4">
                <input
                  type="range"
                  min="1"
                  max="150"
                  step="0.5"
                  value={weightG}
                  onChange={(e) => setWeightG(parseFloat(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <div className="flex items-center space-x-1 min-w-[90px]">
                  <input
                    type="number"
                    min="1"
                    max="500"
                    step="0.5"
                    value={weightG}
                    onChange={(e) => setWeightG(parseFloat(e.target.value) || 0)}
                    className="w-20 px-2 py-1.5 text-right font-bold text-slate-900 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <span className="text-xs font-semibold text-slate-500">g</span>
                </div>
              </div>

              {/* Quick weight presets for convenience */}
              <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-slate-100">
                <span className="text-[11px] text-slate-400 self-center">Presets:</span>
                {[
                  { label: "Can (15g)", val: 15.0 },
                  { label: "Bottle (20g)", val: 20.0 },
                  { label: "Wrapper (5g)", val: 5.0 },
                  { label: "Heavy (80g)", val: 80.0 },
                ].map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    onClick={() => setWeightG(p.val)}
                    className={`text-xs px-2 py-1 rounded-md border transition-colors ${
                      weightG === p.val
                        ? "bg-emerald-50 border-emerald-300 text-emerald-800 font-semibold"
                        : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Drop Button & Cooldown */}
            <div>
              <button
                onClick={handleDrop}
                disabled={isButtonDisabled}
                className="w-full flex items-center justify-center px-6 py-4 rounded-xl text-base font-bold text-white shadow-md transition-all cursor-pointer bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed disabled:shadow-none"
              >
                {submitting ? (
                  <div className="flex items-center space-x-2">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>AI Analyzing Item...</span>
                  </div>
                ) : cooldownRemaining > 0 ? (
                  <span>⏳ Cooldown active ({cooldownRemaining}s)</span>
                ) : (
                  <span>Drop Item & Earn Points</span>
                )}
              </button>

              {cooldownRemaining > 0 && (
                <div className="mt-2 text-center text-xs font-medium text-amber-600 flex items-center justify-center space-x-1">
                  <span>Anti-spam guard active. Next drop in</span>
                  <span className="font-bold">{cooldownRemaining}s</span>
                </div>
              )}
            </div>
          </div>

          {/* Friendly Error Banner (e.g. 429/503 AI busy or network) */}
          {errorMessage && (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-sm flex items-start space-x-3">
              <span className="text-xl">⚠️</span>
              <div className="flex-1">
                <p className="font-semibold text-amber-900">Notice</p>
                <p className="mt-0.5">{errorMessage}</p>
                {isRetryable && (
                  <button
                    onClick={handleDrop}
                    className="mt-2 text-xs font-bold text-amber-900 underline hover:no-underline"
                  >
                    Retry Now
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Result Card: Accepted (Green) or Rejected (Red) */}
          {dropResult && (
            <div
              className={`p-6 rounded-2xl shadow-lg border transition-all ${
                dropResult.status === "accepted"
                  ? "bg-emerald-50/80 border-emerald-300 text-emerald-950"
                  : "bg-red-50/80 border-red-300 text-red-950"
              }`}
            >
              <div className="flex items-center space-x-3 mb-4">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold ${
                    dropResult.status === "accepted"
                      ? "bg-emerald-500 text-white"
                      : "bg-red-500 text-white"
                  }`}
                >
                  {dropResult.status === "accepted" ? "✓" : "✕"}
                </div>
                <div>
                  <h3 className="font-extrabold text-lg leading-tight">
                    {dropResult.status === "accepted" ? "Item Accepted!" : "Item Rejected"}
                  </h3>
                  <p className="text-xs opacity-75">
                    {dropResult.status === "accepted"
                      ? "Reward points credited to your wallet"
                      : "Anti-fraud and recycling verification failed"}
                  </p>
                </div>
              </div>

              <div className="space-y-2 text-sm border-t border-b border-black/10 py-3 my-3">
                <div className="flex justify-between">
                  <span className="text-slate-600">Identified Material:</span>
                  <span className="font-semibold capitalize">
                    {MATERIAL_LABELS[dropResult.material] || dropResult.material}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">AI Confidence:</span>
                  <span className="font-semibold">
                    {(dropResult.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Simulated Weight:</span>
                  <span className="font-semibold">{dropResult.weightG} g</span>
                </div>
                {dropResult.status === "accepted" ? (
                  <>
                    <div className="flex justify-between text-emerald-800 font-bold text-base pt-1">
                      <span>Points Earned:</span>
                      <span>+{dropResult.points} pts</span>
                    </div>
                    {dropResult.newBalance !== null && (
                      <div className="flex justify-between text-xs text-emerald-700">
                        <span>New Wallet Balance:</span>
                        <span className="font-bold">{dropResult.newBalance} pts</span>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="mt-2 p-2.5 rounded-lg bg-red-100/70 border border-red-200 text-xs text-red-800">
                    <span className="font-bold">Reason: </span>
                    <span>{dropResult.rejectReason || "Verification failed."}</span>
                  </div>
                )}
              </div>

              <p className="text-[11px] text-slate-500 text-center">
                Machine ID: {dropResult.machineId}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
