# YieldSense — Frontend Context for Claude Code

## Project Overview

**YieldSense** is a crop yield forecasting and AI advisory platform for African smallholder farmers.
Built at Carnegie Mellon University Africa.

The backend is a **FastAPI** app deployed on **Vercel** (Python serverless). The frontend needs to be built as a separate web app that consumes the REST API.

---

## Backend API — Base URL

The API is deployed via Vercel. All routes are served from `api/index.py`.

**Local dev:** `http://localhost:8000`
**Production:** Vercel deployment URL (set as env var `VITE_API_BASE_URL` or similar)

---

## Authentication

### POST `/auth/login`
Login with email OR phone (not both).

**Request:**
```json
{
  "email_address": "farmer@example.com",   // OR
  "phone_number": "+254700000000",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<opaque>",
  "token_type": "Bearer",
  "expires_in": 1800,
  "session_id": "<uuid>"
}
```

**Errors:**
- `401` — Invalid credentials
- `403` — Account not verified (OTP not confirmed)

---

### POST `/auth/refresh`
```json
{ "refresh_token": "<token>" }
```
Returns same shape as login response.

---

### POST `/auth/logout?session_id=<uuid>`
Requires `Authorization: Bearer <token>` header.

---

### GET `/auth/session/{session_id}`
Returns session status. Requires auth.

---

## Onboarding (Registration)

### POST `/onboarding/signup`
Register a new farmer. No auth required.

**Request:**
```json
{
  "name": "John Doe",
  "farm_country": "Kenya",
  "farm_state_region": "Nairobi",
  "phone_number": "+254700000000",
  "email_address": "john@example.com",
  "area_of_farmland": 2.5,
  "password": "password123",
  "crop_profiles": [
    {
      "crop_type": "Maize",
      "planting_month": "March",
      "harvest_month": "August",
      "average_yield_tons": 3.5
    }
  ]
}
```

**Response:** `FarmerOnboardingResponse` — farmer details, `is_verified: false` until OTP confirmed.

**Errors:**
- `400` — `"Email already registered"` or `"Phone number already registered"`

---

### POST `/onboarding/verify-email`
Verify account with OTP. **Dev OTP is `123456`** (static).

**Request:**
```json
{
  "email_address": "john@example.com",   // OR phone_number
  "otp": "123456"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Contact verified successfully. You can now log in.",
  "farmer_id": 1,
  "email": "john@example.com",
  "is_verified": true
}
```

---

### GET `/onboarding/status/{farmer_id}`
Check onboarding/verification status.

---

## Farmer Profile (requires auth)

### GET `/farmers/{farmer_id}`
```json
{
  "id": 1,
  "name": "John Doe",
  "farm_country": "Kenya",
  "farm_state_region": "Nairobi",
  "phone_number": "+254700000000",
  "email_address": "john@example.com",
  "area_of_farmland": 2.5,
  "crop_profiles": [
    {
      "id": 1,
      "crop_type": "Maize",
      "planting_month": "March",
      "harvest_month": "August",
      "average_yield_tons": 3.5
    }
  ]
}
```

### PUT `/farmers/{farmer_id}`
Update farmer profile. All fields optional.

### DELETE `/farmers/{farmer_id}`

### GET `/farmers`
List all farmers (admin use).

---

## Chat (requires auth)

All chat endpoints require `Authorization: Bearer <token>`.

### POST `/chat`
Send a message and get an AI reply.

**Request:**
```json
{
  "session_id": "<session_id from login>",
  "farmer_id": 1,
  "message": "What should I do after harvest?",
  "conversation_id": null   // optional, omit to use active conversation
}
```

**Response:**
```json
{
  "message": "Based on your maize harvest...",
  "language": "en",
  "session_id": "<uuid>",
  "conversation_id": "<uuid>",
  "message_id": "<uuid>",
  "chart": null   // or chart data object for yield analytics
}
```

The AI has tools: `get_yield_analytics`, `web_search`, `get_weather`.
When `get_yield_analytics` is called, `chart` will contain chart data.

---

### POST `/chat/new-conversation?session_id=<uuid>`
Start a fresh conversation. Returns `{ "conversation_id": "<uuid>" }`.

---

### GET `/chat/conversations?farmer_id=1&status=active`
List conversations. `status` can be `active`, `archived`, or `all`.

**Response:** Array of:
```json
{
  "id": 1,
  "external_id": "<uuid>",
  "farmer_id": 1,
  "title": "What should I do after harvest?",
  "context_type": "ai_chat",
  "is_active": "active",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "message_count": 5
}
```

---

### GET `/chat/conversations/{conversation_id}`
Get full conversation with messages.

**Response:**
```json
{
  "id": 1,
  "external_id": "<uuid>",
  "farmer_id": 1,
  "title": "...",
  "context_type": "ai_chat",
  "is_active": "active",
  "created_at": "...",
  "updated_at": "...",
  "messages": [
    {
      "id": 1,
      "conversation_id": 1,
      "farmer_id": 1,
      "sender_type": "farmer",   // or "ai"
      "content": "What should I do?",
      "created_at": "..."
    }
  ]
}
```

---

### POST `/chat/conversations/{conversation_id}/archive`
Archive a conversation.

### POST `/chat/conversations/{conversation_id}/read`
Mark conversation as read.

---

## Health Check

### GET `/health`
Returns `{ "status": "healthy" }`. No auth required.

---

## Database Schema (for reference)

**farmers** — id, name, farm_country, farm_state_region, phone_number, email_address, area_of_farmland, is_verified, otp_verified, created_at

**crop_profiles** — id, farmer_id, crop_type, planting_month, harvest_month, average_yield_tons

**yield_records** — id, farmer_id, crop_type, season, planting_date, harvest_date, predicted_yield_kg_per_ha, actual_yield_kg_per_ha

**farmer_sessions** — id, farmer_id, session_id, access_token, refresh_token, is_active, expires_at

**conversations** — id, farmer_id, external_id (UUID), title, context_type, is_active ("active"/"archived")

**messages** — id, conversation_id, farmer_id, sender_type (farmer/ai), content, created_at

---

## Auth Flow Summary

1. User signs up → `POST /onboarding/signup`
2. User verifies OTP → `POST /onboarding/verify-email` (dev OTP: `123456`)
3. User logs in → `POST /auth/login` → store `access_token`, `refresh_token`, `session_id`, `farmer_id`
4. All protected requests → `Authorization: Bearer <access_token>`
5. Token expires in 30 min → use `POST /auth/refresh` with `refresh_token`
6. Logout → `POST /auth/logout?session_id=<uuid>`

---

## Key Business Rules

- A farmer must be **verified** (OTP confirmed) before they can log in
- Each farmer has one or more **crop profiles**
- Chat is tied to a **session** (from login) and a **conversation** (UUID)
- The AI is context-aware: it knows the farmer's name, location, farm size, and crops
- Chat responses may include a `chart` object for yield analytics visualisation
- Conversations can be archived but not deleted from the UI
- `session_id` from login must be passed in every chat request

---

## Suggested Frontend Pages

1. **Landing / Home** — product intro, CTA to sign up or log in
2. **Sign Up** — onboarding form (name, country, region, phone, email, password, crop profiles)
3. **OTP Verification** — enter 6-digit OTP (dev: `123456`)
4. **Login** — email or phone + password
5. **Dashboard** — farmer overview (name, farm info, crop profiles, yield records)
6. **Chat** — AI advisory chat interface with conversation history sidebar
7. **Profile / Settings** — edit farmer details

---

## Tech Recommendations

- **Framework:** Next.js (App Router) or React + Vite
- **Styling:** Tailwind CSS
- **State:** Zustand or React Context for auth state
- **HTTP:** Axios or fetch with interceptors for token refresh
- **Charts:** Recharts or Chart.js (for yield analytics from chat `chart` field)
- **i18n:** The AI supports multiple languages; consider `next-intl` or `react-i18next`

---

## Environment Variables Needed

```env
NEXT_PUBLIC_API_BASE_URL=https://<your-vercel-deployment>.vercel.app
# or for local dev:
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Notes

- The backend is already deployed and working — no backend changes needed
- CORS must be enabled on the backend for the frontend domain (check with backend team)
- The dev OTP is always `123456` — no email is actually sent in development
- `session_id` is returned at login and must be stored alongside the JWT
- The `farmer_id` is returned in the login response indirectly via the session; fetch it from `GET /farmers/{farmer_id}` or store it from the signup/login flow
- Chart data shape from `chat.chart` is dynamic — render it conditionally if present
