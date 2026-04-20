import express from "express";

const app = express();
app.use(express.json());

const PORT = process.env.ROUTER_PORT || 8082;
const INTERNAL_SHARED_TOKEN = process.env.INTERNAL_SHARED_TOKEN || "";
const OPENROUTER_BASE_URL = process.env.OPENROUTER_BASE_URL || "https://openrouter.ai/api/v1";
const OPENROUTER_SITE_URL = process.env.OPENROUTER_SITE_URL || "https://example.com";
const OPENROUTER_APP_NAME = process.env.OPENROUTER_APP_NAME || "AXION Router";

const modelMap = {
  free_router: process.env.OPENROUTER_MODEL_FREE_ROUTER || "openrouter/free",
  free_fixed: process.env.OPENROUTER_MODEL_FREE_FIXED || "google/gemma-3-4b-it:free",
  cheap_fast: process.env.OPENROUTER_MODEL_CHEAP_FAST || "openai/gpt-4.1-nano",
  cheap_main: process.env.OPENROUTER_MODEL_CHEAP_MAIN || "openai/gpt-4.1-mini",
  balanced: process.env.OPENROUTER_MODEL_BALANCED || "qwen/qwen3-8b",
  premium: process.env.OPENROUTER_MODEL_PREMIUM || "google/gemma-4-26b-a4b-it"
};

const taskPolicy = {
  classify: "free_fixed",
  summarize: "cheap_fast",
  qa: "cheap_main",
  agent: "balanced",
  premium: "premium"
};

function requireAuth(req, res, next) {
  if (INTERNAL_SHARED_TOKEN && req.headers["x-internal-token"] !== INTERNAL_SHARED_TOKEN) {
    return res.status(401).json({ error: "unauthorized" });
  }
  next();
}

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "router-node" });
});

app.get("/models", requireAuth, (_req, res) => {
  res.json({ models: modelMap, policy: taskPolicy });
});

app.post("/route/chat", requireAuth, async (req, res) => {
  try {
    const { task_type = "qa", messages = [], force_target, temperature = 0.2, max_tokens = 800 } = req.body;
    const target = force_target || taskPolicy[task_type] || "cheap_main";
    const model = modelMap[target];
    const apiKey = ["free_router", "free_fixed"].includes(target)
      ? process.env.OPENROUTER_API_KEY_FREE
      : process.env.OPENROUTER_API_KEY_PAID;

    const r = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-Title": OPENROUTER_APP_NAME
      },
      body: JSON.stringify({ model, messages, temperature, max_tokens, stream: false })
    });

    const data = await r.json();
    if (!r.ok) return res.status(r.status).json(data);
    res.json({ provider: "openrouter", target, model, content: data?.choices?.[0]?.message?.content ?? "", raw: data });
  } catch (err) {
    res.status(500).json({ error: "router failure", detail: String(err) });
  }
});

app.listen(PORT, () => console.log(`router-node listening on ${PORT}`));
