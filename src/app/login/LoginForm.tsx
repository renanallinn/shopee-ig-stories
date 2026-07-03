"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginForm() {
  const router = useRouter();
  const supabase = createClient();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    if (mode === "login") {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      setLoading(false);
      if (error) {
        setMessage(error.message);
        return;
      }
      router.push("/dashboard");
      router.refresh();
      return;
    }

    const { error } = await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (error) {
      setMessage(error.message);
      return;
    }
    setMessage(
      "Conta criada. Se a confirmação por e-mail estiver ativa no seu projeto Supabase, verifique sua caixa de entrada antes de entrar.",
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="email" className="text-sm font-medium">
          E-mail
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border border-black/10 px-3 py-2 dark:border-white/20"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="password" className="text-sm font-medium">
          Senha
        </label>
        <input
          id="password"
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border border-black/10 px-3 py-2 dark:border-white/20"
        />
      </div>

      {message && <p className="text-sm text-red-600 dark:text-red-400">{message}</p>}

      <button
        type="submit"
        disabled={loading}
        className="rounded bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-50"
      >
        {loading ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}
      </button>

      <button
        type="button"
        onClick={() => {
          setMessage(null);
          setMode(mode === "login" ? "signup" : "login");
        }}
        className="text-sm text-black/60 underline dark:text-white/60"
      >
        {mode === "login" ? "Ainda não tem conta? Criar conta" : "Já tem conta? Entrar"}
      </button>
    </form>
  );
}
