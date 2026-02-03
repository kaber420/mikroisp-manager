# AI ARCHITECTURE RULES - Real-Time & Multi-Worker

> **CRITICAL**: Read this BEFORE touching WebSockets, Redict, or notifications.

## Architecture Overview

```
┌─────────────┐
│  Telegram   │
│     Bot     │ ─── Separate Python process
└──────┬──────┘
       │ Publishes to Redict Pub/Sub
       ▼
┌──────────────────────────────────────────┐
│              Redict (Redis)              │
│         Channel: "chat:updates"          │
└──────────────────────────────────────────┘
       │ All workers subscribe
       ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Worker 1 │  │ Worker 2 │  │ Worker 3 │
│ (uvicorn)│  │ (uvicorn)│  │ (uvicorn)│
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     └─────────────┼─────────────┘
                   │
            WebSocket clients
           (browser connects to
            ONE random worker)
```

## RULES - DO NOT VIOLATE

### 1. Multi-Worker Awareness

- **Uvicorn runs with 3+ workers** - each is a separate process
- Each worker has its OWN `ConnectionManager` instance
- HTTP requests hit random workers (load balanced)
- **NEVER** assume HTTP → WebSocket will reach the browser's worker

### 2. Cross-Worker Communication

- **ALWAYS use Redict Pub/Sub** for real-time notifications
- All workers subscribe to `chat:updates` channel
- When ANY worker receives a Redict message, it broadcasts to ITS WebSocket clients
- This ensures the message reaches the browser regardless of which worker it's connected to

### 3. Bot is a Separate Process

- The bot does NOT share memory with web workers
- Bot does NOT have access to web server's `cache_manager` or `redict_manager`
- Bot must create its OWN Redict connection to publish messages
- Use `redis.from_url(os.getenv("REDICT_URL"))` directly in bot code

### 4. Backend Agnosticism

- Application supports BOTH in-memory cache AND Redict
- **Check backend availability** before using Redict features
- **Provide HTTP fallback** for single-worker deployments
- Pattern:

  ```python
  # Try Redict first (multi-worker)
  try:
      client = redis.from_url(REDICT_URL)
      client.publish("chat:updates", payload)
  except:
      # Fallback to HTTP (single-worker)
      httpx.post("/api/internal/notify-monitor-update", ...)
  ```

### 5. WebSocket Connection Persistence

- WebSocket MUST stay open (bidirectional)
- Implement heartbeat (ping/pong every 25s)
- Handle reconnection with exponential backoff
- **NEVER** use early return if indicator elements missing

## Key Files

| File | Purpose |
|------|---------|
| `app/core/websockets.py` | ConnectionManager + Redict listener |
| `app/bot/core/ticket_manager.py` | Bot notifications (publishes to Redict) |
| `static/js/ws-client.js` | Browser WebSocket client |
| `app/main.py` | WebSocket endpoint + lifespan (starts listener) |

## Testing Checklist

Before claiming "it works":

1. [ ] Test with 3+ workers running
2. [ ] Send message from Telegram
3. [ ] Verify browser receives WebSocket message
4. [ ] Check logs show `[REDICT] Published` not `[HTTP]`
5. [ ] Confirm `subscribers: 3` (or your worker count)
