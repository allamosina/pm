"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";

export function AuthGate() {
  const [state, setState] = useState<"checking" | "signedOut" | "signedIn" | "unavailable">("checking");
  const [username, setUsername] = useState("");
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const sessionExpired = useCallback(() => {
    setUsername("");
    setState("signedOut");
    setError("Your session expired. Please sign in again.");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/auth/session", { cache: "no-store", signal: controller.signal })
      .then(async response => {
        if (controller.signal.aborted) return;
        if (response.ok) {
          const user = await response.json();
          if (controller.signal.aborted) return;
          setUsername(user.username);
          setState("signedIn");
        } else setState(response.status === 401 ? "signedOut" : "unavailable");
      })
      .catch(() => { if (!controller.signal.aborted) setState("unavailable"); });
    return () => controller.abort();
  }, []);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError("");
    try {
      const response = await fetch(registering ? "/api/auth/register" : "/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: form.get("username"), password: form.get("password") }),
      });
      if (response.ok) {
        const user = await response.json();
        setUsername(user.username);
        setRegistering(false);
        setState("signedIn");
      } else if (response.status === 409) setError("That username is already taken.");
      else if (response.status === 422 && registering) setError("Use a 3–32 character username with letters, numbers, underscores or hyphens, and an 8–128 character password.");
      else setError(response.status === 401 ? "Invalid username or password." : "Unable to sign in or create your account. Please try again.");
    } catch {
      setError("Unable to reach the server. Please try again.");
    } finally {
      setPending(false);
    }
  }

  async function logout() {
    setPending(true);
    setError("");
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) throw new Error("Logout failed");
      setUsername("");
      setState("signedOut");
    } catch {
      setError("Unable to sign out. Please try again.");
    } finally {
      setPending(false);
    }
  }

  if (state === "checking") return <p role="status" className="p-8 text-[var(--gray-text)]">Checking session...</p>;
  if (state === "unavailable") return (
    <main className="mx-auto max-w-md p-8">
      <p role="alert">Unable to check your session.</p>
      <button className="mt-4 text-[var(--primary-blue)]" onClick={() => window.location.reload()}>Try again</button>
    </main>
  );
  if (state === "signedIn") return (
    <>
      <div className="mx-auto flex max-w-[1500px] items-center justify-end gap-4 px-6 pt-6">
        {error && <p role="alert">{error}</p>}
        <span className="text-sm text-[var(--gray-text)]">Signed in as {username}</span>
        <button onClick={logout} disabled={pending} className="rounded-full bg-[var(--secondary-purple)] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50">
          {pending ? "Signing out..." : "Sign out"}
        </button>
      </div>
      <KanbanBoard key={username} onSessionExpired={sessionExpired} />
    </>
  );
  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <form key={registering ? "register" : "login"} onSubmit={login} className="w-full max-w-md space-y-6 rounded-3xl border-t-4 border-[var(--accent-yellow)] bg-white p-8 shadow-[var(--shadow)]">
        <div>
          <h1 className="font-display text-3xl font-semibold text-[var(--navy-dark)]">{registering ? "Create your account" : "Sign in to Kanban Studio"}</h1>
          <p className="mt-3 text-sm text-[var(--gray-text)]">Your project, one clear view.</p>
        </div>
        <label className="block text-sm font-medium">Username
          <input name="username" autoComplete="username" required minLength={registering ? 3 : undefined} maxLength={32} pattern={registering ? "[A-Za-z0-9_\\-]+" : undefined} className="mt-2 block w-full rounded-xl border border-[var(--stroke)] p-3 focus:outline-[var(--primary-blue)]" />
        </label>
        <label className="block text-sm font-medium">Password
          <input name="password" type="password" autoComplete={registering ? "new-password" : "current-password"} required minLength={registering ? 8 : undefined} maxLength={128} className="mt-2 block w-full rounded-xl border border-[var(--stroke)] p-3 focus:outline-[var(--primary-blue)]" />
        </label>
        {registering && <p className="text-sm text-[var(--gray-text)]">Username: 3–32 letters, numbers, underscores or hyphens. Password: 8–128 characters.</p>}
        {error && <p role="alert" className="text-sm text-[var(--navy-dark)]">{error}</p>}
        <button disabled={pending} className="w-full rounded-full bg-[var(--secondary-purple)] py-3 font-semibold text-white disabled:opacity-50">
          {pending ? (registering ? "Creating account..." : "Signing in...") : (registering ? "Create account" : "Sign in")}
        </button>
        <button type="button" disabled={pending} onClick={() => { setRegistering(!registering); setError(""); }} className="w-full text-sm font-semibold text-[var(--primary-blue)]">
          {registering ? "Already have an account? Sign in" : "Create an account"}
        </button>
      </form>
    </main>
  );
}
