
import React, { useEffect, useState } from "react";

import AuthPage from "./pages/AuthPage";
import ChatPage from "./pages/ChatPage";
import {
  clearToken,
  getCurrentUser,
  getToken,
  logout,
} from "./services/api";

export default function App() {
  const [user, setUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      if (!getToken()) {
        setCheckingAuth(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();

        if (!cancelled) {
          setUser(currentUser);
        }
      } catch {
        clearToken();
      } finally {
        if (!cancelled) {
          setCheckingAuth(false);
        }
      }
    }

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  function handleLogout() {
    logout();
    setUser(null);
  }

  if (checkingAuth) {
    return <main className="app-loading">Checking your session...</main>;
  }

  if (!user) {
    return <AuthPage onLogin={setUser} />;
  }

  return <ChatPage user={user} onLogout={handleLogout} />;
}
