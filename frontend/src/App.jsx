import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Kiosk from "./pages/Kiosk";
import Wallet from "./pages/Wallet";

function Layout({ children }) {
  const { user } = useAuth();
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {user && <Navbar />}
      <main className="flex-1">{children}</main>
      <footer className="py-4 border-t border-slate-200 text-center text-xs text-slate-500">
        CampusCycle • Smart Campus Recycling System
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Kiosk />
                </ProtectedRoute>
              }
            />
            <Route
              path="/wallet"
              element={
                <ProtectedRoute>
                  <Wallet />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AuthProvider>
  );
}
