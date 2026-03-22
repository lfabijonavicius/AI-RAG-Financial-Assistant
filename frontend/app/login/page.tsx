"use client"

import { Auth } from "@supabase/auth-ui-react"
import { ThemeSupa } from "@supabase/auth-ui-shared"
import { createClient } from "@/lib/supabase"
import { useEffect } from "react"
import { useRouter } from "next/navigation"

export default function LoginPage() {
  const supabase = createClient()
  const router = useRouter()

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN") router.push("/chat")
    })
    return () => subscription.unsubscribe()
  }, [supabase, router])

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "var(--background)" }}>
      <div className="w-full max-w-md p-8 rounded-2xl" style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}>
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--color-teal)" }}>Finance Chatbot</h1>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>AI-powered financial research assistant</p>
        </div>
        <Auth
          supabaseClient={supabase}
          redirectTo={`${typeof window !== "undefined" ? window.location.origin : "http://localhost:3000"}/auth/callback`}
          appearance={{
            theme: ThemeSupa,
            variables: {
              default: {
                colors: {
                  brand: "#1D9E75",
                  brandAccent: "#17855f",
                  inputBackground: "var(--surface-2)",
                  inputBorder: "var(--border)",
                  inputText: "var(--text-primary)",
                },
              },
            },
          }}
          providers={["google"]}
          theme="dark"
        />
      </div>
    </div>
  )
}
