"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function NotionCallback() {
  const router = useRouter();

  useEffect(() => {
    console.log("Callback URL:", window.location.href);

    const url = new URL(window.location.href);
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    const storedState = localStorage.getItem("notion_oauth_state");

    console.log("code:", code);
    console.log("state:", state, "storedState:", storedState);

    if (!code || state !== storedState) {
      router.push("/?error=oauth");
      return;
    }

    // Send code to backend to exchange for tokens
    fetch("http://localhost:5001/api/notion/oauth/exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    })
      .then(res => {
          console.log("exchange response status:", res.status);
          res.json();
          })
      .then(() => {
        localStorage.removeItem("notion_oauth_state");
        router.push("/?notion=connected");
      });
  }, []);

  return <p>Connecting Notion...</p>;
}
