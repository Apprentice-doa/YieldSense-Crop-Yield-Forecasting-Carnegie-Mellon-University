# YieldSense — Frontend Design Brief & Claude Code Prompt

## The Mission

Build the frontend for **YieldSense** — an AI-powered crop yield forecasting platform for African
smallholder farmers. This is a hackathon submission. The judges are looking for:

- **Representation** — does this feel built *for* African farmers, not just *about* them?
- **Inclusivity** — accessible, multilingual-ready, works on low-end devices
- **Innovation** — creative use of AI, data visualisation, and interaction design
- **Polish** — animations, transitions, and micro-interactions that feel intentional

---

## Design Identity

### Africa-Centric Visual Language

The entire app should feel rooted in sub-Saharan African agricultural culture. Every design
decision — colour, typography, iconography, illustration style, animation — should reinforce this.

**Colour Palette:**

```
Primary:    #C8522A  — Laterite/burnt sienna (African red soil)
Secondary:  #2D6A4F  — Deep savanna green (lush crop canopy)
Accent:     #F4A261  — Warm amber (harvest gold / dry season sun)
Sky:        #1A3C5E  — Deep indigo night sky (for dark mode / headers)
Rain:       #4A90D9  — Clear sky blue (rain, water, irrigation)
Earth:      #8B5E3C  — Rich brown earth
Mist:       #E8F4F0  — Morning mist / fog (light backgrounds)
Sun:        #FFD166  — Bright midday sun
Storm:      #2C3E50  — Storm cloud grey
Text:       #1A1A2E  — Deep charcoal (not pure black)
```

**Typography:**
- Headings: `Plus Jakarta Sans` (bold, modern, African tech feel)
- Body: `Inter` (readable, accessible)
- Accent/numbers: `Space Grono` or `DM Mono` (data, yield numbers)

**Illustration / Icon Style:**
- Use flat, bold SVG illustrations with African motifs: kente-inspired geometric borders,
  baobab tree silhouettes, savanna horizon lines, maize/sorghum/cassava crop icons
- Farmer avatars should represent diverse African ethnicities (dark skin tones, traditional
  and modern clothing mix)
- Weather icons should be hand-drawn style, warm and approachable — not cold tech icons

---

## Weather & Crop Animation System

This is the centrepiece of the visual identity. Weather and crop growth animations should
appear throughout the app as ambient background elements, loading states, and contextual
feedback — not just decorations.

### Animation Library: Framer Motion + Lottie

Use **Framer Motion** for layout/transition animations and **Lottie** (or pure CSS/SVG) for
looping ambient animations.

### Weather States

The app should detect or infer a "weather context" and subtly shift the UI:

| Context | Trigger | Visual Effect |
|---|---|---|
| **Sunny / Good yield** | Predicted yield > baseline | Warm amber glow, animated sun rays, golden particles drifting upward |
| **Rainy season** | Planting month context | Animated rain drops falling diagonally, blue-tinted overlay, puddle ripples |
| **Dry / Drought risk** | Low yield prediction | Cracked earth texture, heat shimmer effect, muted warm tones |
| **Harvest time** | Harvest month context | Falling grain particles, golden confetti, warm celebration glow |
| **Storm / Warning** | Low confidence / risk | Dark clouds drifting, lightning flash micro-animation, storm grey palette |
| **Morning / Neutral** | Default / loading | Soft mist rising from ground, gentle dew drops, cool green tones |

### Crop Growth Animation

On the dashboard and landing page, show an animated crop growth cycle:
- A single maize/sorghum stalk that grows from seed → seedling → full crop → harvest
- Triggered on page load, loops slowly
- Responds to yield prediction: taller/fuller crop = higher predicted yield
- Built as an SVG animation with Framer Motion path drawing

### Ambient Particles

Subtle floating particles throughout the app:
- **Pollen/dust** — tiny golden dots drifting upward (sunny state)
- **Rain drops** — thin blue lines falling at an angle (rainy state)
- **Fireflies** — soft glowing dots blinking (night/dark mode)
- **Harvest chaff** — small golden flecks swirling (harvest state)

These should be a `<WeatherCanvas>` component using `canvas` or CSS animations, rendered
behind all content with `pointer-events: none`.

---

## Page-by-Page Specification

### 1. Landing Page (`/`)

**Hero Section:**
- Full-viewport hero with animated savanna horizon
- Baobab tree silhouette on the right, animated crop field on the left
- Animated sun arc moving across the sky (CSS keyframe, very slow, 60s loop)
- Headline: "Know Your Harvest Before It Happens" in Plus Jakarta Sans, bold, large
- Subheadline: "AI-powered yield forecasting for African smallholder farmers"
- Two CTAs: "Get Started" (primary, soil red) and "See How It Works" (ghost)
- Floating weather badge: animated rain/sun icon with "Rainy Season Advisory Active"

**Features Section:**
- Three cards with animated icons:
  1. 🌱 Yield Prediction — crop growth animation
  2. 🌦️ Weather Advisory — rain/sun toggle animation
  3. 💬 AI Chat — chat bubble with typing indicator animation
- Cards use kente-inspired geometric border pattern

**How It Works:**
- 3-step horizontal flow with connecting animated dotted line
- Step icons animate in sequence on scroll (Framer Motion `whileInView`)

**Footer:**
- Dark indigo background (#1A3C5E)
- Subtle kente pattern border at top
- CMU Africa attribution

---

### 2. Sign Up (`/signup`)

**Layout:** Split screen
- Left: Animated crop field illustration (full height), weather ambient animation
- Right: Form

**Form Steps** (multi-step wizard, progress bar at top):

Step 1 — Personal Info:
- Full name, country (dropdown with African countries prioritised), region/state
- Phone number (with country code selector, African codes first)
- Email address

Step 2 — Farm Details:
- Area of farmland (with unit toggle: hectares / acres)
- Animated farm size visualiser: a field outline that grows as you type the number

Step 3 — Crop Profiles:
- Add one or more crops
- Each crop: type (searchable dropdown with crop icons), planting month, harvest month, avg yield
- Animated crop calendar: a circular year wheel showing planting/harvest months highlighted
- "Add another crop" button with a sprouting animation

Step 4 — Password:
- Password + confirm, strength indicator styled as a growing plant (weak = seedling, strong = full crop)

**Transitions:** Each step slides in from the right with a subtle soil-texture wipe

---

### 3. OTP Verification (`/verify`)

- 6-digit OTP input (individual boxes, auto-advance)
- Animated envelope with a letter flying out (Lottie or CSS)
- On success: animated checkmark with golden confetti burst
- Dev hint shown in development: "Dev OTP: 123456"
- Resend OTP link with countdown timer

---

### 4. Login (`/login`)

- Same split layout as signup
- Toggle: "Login with Email" / "Login with Phone"
- Animated weather greeting based on time of day:
  - Morning (6–12): sunrise animation, "Good morning, farmer"
  - Afternoon (12–17): sun high, "Good afternoon"
  - Evening (17–21): sunset, warm tones
  - Night (21–6): stars/fireflies, deep indigo

---

### 5. Dashboard (`/dashboard`)

This is the most important page. It should feel like a **farm command centre**.

**Layout:** Sidebar (left, collapsible) + Main content area

**Sidebar:**
- Farmer avatar (initials-based, warm earth tones)
- Farmer name + location
- Navigation: Dashboard, Chat, Profile
- Weather widget at bottom of sidebar: current season indicator with animated icon
- Animated crop growth mini-widget: tiny stalk that reflects yield health

**Main Content:**

Top bar:
- Greeting: "Welcome back, [Name] 🌾" with animated waving grain emoji
- Season badge: "Long Rains 2024" with rain drop animation
- Notification bell

Hero Stats Row (4 cards):
1. **Total Farm Area** — field icon, area in ha
2. **Active Crops** — animated crop icons cycling through farmer's crops
3. **Predicted Yield** — large number with trend arrow, colour-coded (green/amber/red)
4. **Season Status** — "Planting" / "Growing" / "Harvest" with animated stage indicator

Each stat card has a subtle weather-appropriate ambient animation in the background.

Crop Profiles Section:
- Card grid, one card per crop
- Each card shows: crop name with icon, planting → harvest timeline bar, avg yield
- Timeline bar animates on load (fills left to right)
- Current month highlighted on the timeline

Yield Forecast Section:
- Recharts AreaChart showing predicted vs actual yield over time
- Chart colours use the palette (green for actual, amber for predicted)
- Animated chart line drawing on mount
- If no yield records yet: empty state with animated "plant a seed" illustration

Recent Chat Section:
- Last 3 conversations as preview cards
- Each card shows: title, last message preview, timestamp, message count badge
- "Start New Chat" button with chat bubble animation

---

### 6. Chat (`/chat`)

This is the AI advisory interface. It should feel like talking to a knowledgeable local agronomist.

**Layout:** Three-column on desktop, single column on mobile
- Column 1 (narrow): Conversation list sidebar
- Column 2 (wide): Active chat
- Column 3 (narrow): Context panel (weather, crop info)

**Conversation Sidebar:**
- "New Conversation" button at top with sprouting animation on click
- List of past conversations with title, timestamp, message count
- Active conversation highlighted with soil-red left border
- Archive button on hover (swipe on mobile)
- Search conversations input

**Chat Area:**

Header:
- Conversation title (editable on click)
- Weather context badge: animated rain/sun based on AI's last weather tool call
- "Powered by YieldSense AI" with subtle pulse animation

Messages:
- Farmer messages: right-aligned, soil-red bubble, white text
- AI messages: left-aligned, white/mist bubble, dark text
- AI avatar: animated crop/leaf icon (not a robot — keep it agricultural)
- Timestamps on hover
- Message animations: slide in from appropriate side with spring physics

AI Typing Indicator:
- Three animated dots styled as growing seedlings (not generic dots)
- Appears while waiting for API response

Chart Messages:
- When `chart` is present in the response, render an inline Recharts chart inside the message bubble
- Chart has the same warm palette
- Animated chart line drawing

Weather Tool Response:
- When AI calls `get_weather`, show a special weather card message:
  - Animated weather icon (sun/rain/cloud)
  - Temperature, conditions, 3-day forecast mini-strip
  - Styled with the weather palette

Input Area:
- Textarea with auto-resize
- Send button with animated arrow
- Suggested prompts (chips) on empty conversation:
  - "What's my yield forecast this season?"
  - "When should I plant my maize?"
  - "What are current market prices?"
  - "How do I protect my crops from drought?"
- Voice input button (UI only, no implementation needed)

**Context Panel (right sidebar):**
- Current weather widget (animated)
- Farmer's active crops with growth stage indicators
- Quick stats: farm size, location
- Collapses to icon bar on medium screens

**Mobile Chat:**
- Full screen chat, bottom sheet for conversation list
- Swipe right to open conversation list
- Swipe left on a message to see timestamp

---

### 7. Profile / Settings (`/profile`)

- Edit all farmer details
- Crop profile management (add/edit/remove)
- Animated save confirmation (crop growing out of a checkmark)
- Danger zone: delete account (with confirmation modal)

---

## Component Library

Build these reusable components:

### `<WeatherCanvas />`
- Full-screen canvas behind all content
- Renders ambient particles based on `weatherState` prop
- States: `sunny | rainy | dry | harvest | storm | morning`
- `pointer-events: none`, `position: fixed`, `z-index: 0`
- Performance: use `requestAnimationFrame`, max 60 particles

### `<CropGrowthAnimation />`
- SVG-based animated crop stalk
- Props: `stage` (seed/seedling/growing/mature/harvest), `cropType`, `yieldScore` (0–1)
- Uses Framer Motion `pathLength` animation
- Sizes: `sm` (sidebar widget), `md` (card), `lg` (hero)

### `<WeatherBadge />`
- Pill badge with animated weather icon
- Props: `condition` (sunny/rainy/dry/storm), `label`
- Icon animates: sun rotates slowly, rain drops fall, clouds drift

### `<SeasonTimeline />`
- Horizontal bar showing 12 months
- Highlights planting month (green) and harvest month (amber)
- Current month has a pulsing indicator
- Animated fill on mount

### `<YieldScoreRing />`
- Circular progress ring showing yield score vs baseline
- Colour: green (above baseline), amber (at baseline), red (below)
- Animated stroke-dashoffset on mount
- Centre shows the yield number with count-up animation

### `<AfricanPatternBorder />`
- SVG kente/geometric pattern border
- Used as card borders, section dividers
- Variants: `kente`, `adinkra`, `geometric`
- Subtle, not overwhelming — 2–4px border or top/bottom accent line

### `<FarmerAvatar />`
- Initials-based avatar with warm earth tone backgrounds
- Background colours cycle through: laterite, savanna green, harvest gold
- Optional: animated ring when farmer is "active"

### `<ChatBubble />`
- Farmer variant: right-aligned, soil-red
- AI variant: left-aligned, mist white, with crop-leaf avatar
- Chart variant: full-width, contains inline Recharts chart
- Weather variant: weather card with animated icon
- All animate in with spring physics

### `<LoadingHarvest />`
- Full-page loading state
- Animated crop field with sun moving across sky
- "YieldSense is thinking..." with animated grain dots
- Used while waiting for AI responses and page loads

---

## Animation Principles

1. **Purposeful** — every animation communicates something (growth = progress, rain = data loading, harvest = success)
2. **Performant** — use CSS transforms and opacity only, avoid layout-triggering properties
3. **Respectful** — honour `prefers-reduced-motion` — all animations should have a static fallback
4. **African rhythm** — animations should feel organic and warm, not mechanical. Use spring physics (stiffness: 100, damping: 15) not linear easing

```js
// Standard spring config
const springConfig = { type: "spring", stiffness: 100, damping: 15 }

// Gentle float (ambient elements)
const floatAnimation = {
  y: [0, -8, 0],
  transition: { duration: 3, repeat: Infinity, ease: "easeInOut" }
}

// Crop growth (path drawing)
const cropGrowth = {
  pathLength: [0, 1],
  transition: { duration: 1.5, ease: "easeOut" }
}
```

---

## Tech Stack

```
Framework:     Next.js 14 (App Router)
Styling:       Tailwind CSS + custom CSS variables for the palette
Animations:    Framer Motion (layout, transitions, spring physics)
               Lottie React (complex looping animations)
Charts:        Recharts (yield data, inline chat charts)
State:         Zustand (auth store, weather state, chat state)
HTTP:          Axios with interceptors (auto token refresh)
Forms:         React Hook Form + Zod validation
Icons:         Lucide React (base) + custom SVG crop/weather icons
Fonts:         Plus Jakarta Sans, Inter (Google Fonts)
Canvas:        Native Canvas API for WeatherCanvas particle system
i18n:          next-intl (English + Swahili + French + Hausa stubs)
```

---

## File Structure

```
src/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   └── verify/page.tsx
│   ├── (app)/
│   │   ├── dashboard/page.tsx
│   │   ├── chat/page.tsx
│   │   ├── chat/[conversationId]/page.tsx
│   │   └── profile/page.tsx
│   ├── layout.tsx
│   └── page.tsx              ← Landing page
├── components/
│   ├── weather/
│   │   ├── WeatherCanvas.tsx
│   │   ├── WeatherBadge.tsx
│   │   └── WeatherIcon.tsx
│   ├── crops/
│   │   ├── CropGrowthAnimation.tsx
│   │   ├── SeasonTimeline.tsx
│   │   └── YieldScoreRing.tsx
│   ├── chat/
│   │   ├── ChatBubble.tsx
│   │   ├── ChatInput.tsx
│   │   ├── ConversationList.tsx
│   │   └── TypingIndicator.tsx
│   ├── ui/
│   │   ├── AfricanPatternBorder.tsx
│   │   ├── FarmerAvatar.tsx
│   │   ├── LoadingHarvest.tsx
│   │   └── StatCard.tsx
│   └── layout/
│       ├── Sidebar.tsx
│       └── TopBar.tsx
├── lib/
│   ├── api.ts                ← Axios instance + interceptors
│   ├── auth.ts               ← Token management
│   └── weather.ts            ← Weather state logic
├── store/
│   ├── authStore.ts          ← Zustand auth store
│   ├── chatStore.ts          ← Zustand chat store
│   └── weatherStore.ts       ← Zustand weather/season store
├── hooks/
│   ├── useAuth.ts
│   ├── useChat.ts
│   └── useWeatherState.ts
└── types/
    ├── api.ts                ← API response types
    └── weather.ts            ← Weather state types
```

---

## API Integration

### Axios Instance (`lib/api.ts`)

```typescript
import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
})

// Attach token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = useAuthStore.getState().refreshToken
      if (refreshToken) {
        const { data } = await axios.post('/auth/refresh', { refresh_token: refreshToken })
        useAuthStore.getState().setTokens(data)
        error.config.headers.Authorization = `Bearer ${data.access_token}`
        return api(error.config)
      }
    }
    return Promise.reject(error)
  }
)

export default api
```

### Auth Store (`store/authStore.ts`)

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  sessionId: string | null
  farmerId: number | null
  farmer: FarmerOut | null
  setTokens: (data: TokenResponse) => void
  setFarmer: (farmer: FarmerOut) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      sessionId: null,
      farmerId: null,
      farmer: null,
      setTokens: (data) => set({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        sessionId: data.session_id,
      }),
      setFarmer: (farmer) => set({ farmer, farmerId: farmer.id }),
      logout: () => set({ accessToken: null, refreshToken: null, sessionId: null, farmerId: null, farmer: null }),
    }),
    { name: 'yieldsense-auth' }
  )
)
```

---

## Weather State Logic

The weather state drives the ambient animations. Derive it from the farmer's crop profiles:

```typescript
// lib/weather.ts
export type WeatherState = 'sunny' | 'rainy' | 'dry' | 'harvest' | 'storm' | 'morning'

const MONTHS = ['January','February','March','April','May','June',
                'July','August','September','October','November','December']

export function deriveWeatherState(cropProfiles: CropProfile[]): WeatherState {
  const currentMonth = MONTHS[new Date().getMonth()]

  for (const crop of cropProfiles) {
    if (crop.harvest_month === currentMonth) return 'harvest'
    if (crop.planting_month === currentMonth) return 'rainy'
  }

  const hour = new Date().getHours()
  if (hour >= 6 && hour < 9) return 'morning'
  if (hour >= 9 && hour < 17) return 'sunny'
  return 'morning'
}
```

---

## Tailwind Config

```js
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        soil:    { DEFAULT: '#C8522A', light: '#E07A52', dark: '#9E3D1A' },
        savanna: { DEFAULT: '#2D6A4F', light: '#52A07A', dark: '#1A4A35' },
        harvest: { DEFAULT: '#F4A261', light: '#F7C08A', dark: '#D4823A' },
        sky:     { DEFAULT: '#1A3C5E', light: '#2A5C8E', dark: '#0A1C2E' },
        rain:    { DEFAULT: '#4A90D9', light: '#7AB0E9', dark: '#2A70B9' },
        earth:   { DEFAULT: '#8B5E3C', light: '#B07E5C', dark: '#6B3E1C' },
        mist:    { DEFAULT: '#E8F4F0', dark: '#C8D4D0' },
        sun:     { DEFAULT: '#FFD166' },
        storm:   { DEFAULT: '#2C3E50' },
      },
      fontFamily: {
        heading: ['Plus Jakarta Sans', 'sans-serif'],
        body:    ['Inter', 'sans-serif'],
        mono:    ['Space Grotesk', 'monospace'],
      },
      animation: {
        'float':        'float 3s ease-in-out infinite',
        'rain-fall':    'rainFall 1.5s linear infinite',
        'sun-rotate':   'sunRotate 60s linear infinite',
        'grain-drift':  'grainDrift 4s ease-in-out infinite',
        'pulse-glow':   'pulseGlow 2s ease-in-out infinite',
        'crop-sway':    'cropSway 4s ease-in-out infinite',
      },
      keyframes: {
        float:      { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-8px)' } },
        rainFall:   { '0%': { transform: 'translateY(-10px) translateX(0)', opacity: '0' }, '100%': { transform: 'translateY(100vh) translateX(-20px)', opacity: '0.6' } },
        sunRotate:  { '0%': { transform: 'rotate(0deg)' }, '100%': { transform: 'rotate(360deg)' } },
        grainDrift: { '0%,100%': { transform: 'translateY(0) translateX(0)', opacity: '0.4' }, '50%': { transform: 'translateY(-15px) translateX(5px)', opacity: '0.8' } },
        pulseGlow:  { '0%,100%': { boxShadow: '0 0 0 0 rgba(200,82,42,0.4)' }, '50%': { boxShadow: '0 0 0 8px rgba(200,82,42,0)' } },
        cropSway:   { '0%,100%': { transform: 'rotate(-1deg)' }, '50%': { transform: 'rotate(1deg)' } },
      },
    },
  },
}
```

---

## Key UX Decisions for Hackathon Judges

1. **Offline-first mindset** — show cached data when API is slow, skeleton loaders everywhere
2. **Low-bandwidth friendly** — lazy load images, compress animations, no autoplay video
3. **Multilingual** — language switcher in header (EN / SW / FR / HA), even if only EN is wired
4. **Accessibility** — WCAG AA contrast ratios, keyboard navigation, screen reader labels
5. **Mobile-first** — the primary user is on a smartphone, possibly 2G
6. **Emotional design** — the app should make farmers feel *seen* and *empowered*, not like they're using enterprise software

---

## Environment Variables

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=YieldSense
NEXT_PUBLIC_DEV_OTP=123456
```

---

## Backend API Summary (Quick Reference)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/onboarding/signup` | No | Register farmer |
| POST | `/onboarding/verify-email` | No | Confirm OTP |
| POST | `/auth/login` | No | Login, get tokens |
| POST | `/auth/refresh` | No | Refresh access token |
| POST | `/auth/logout` | Yes | Logout |
| GET | `/farmers/{id}` | Yes | Get farmer profile |
| PUT | `/farmers/{id}` | Yes | Update profile |
| POST | `/chat` | Yes | Send message, get AI reply |
| POST | `/chat/new-conversation` | Yes | Start new conversation |
| GET | `/chat/conversations` | Yes | List conversations |
| GET | `/chat/conversations/{id}` | Yes | Get conversation + messages |
| POST | `/chat/conversations/{id}/archive` | Yes | Archive conversation |
| GET | `/health` | No | Health check |

**Auth header:** `Authorization: Bearer <access_token>`

**Chat requires:** `session_id` (from login), `farmer_id`, `message`

**Dev OTP:** `123456` (static, no email sent)

---

## What "Winning" Looks Like

The judges will open the app and feel:

> "This was built *for* African farmers. It respects their context, their crops, their seasons.
> The AI feels like a knowledgeable neighbour, not a chatbot. The data is beautiful and
> understandable. I can imagine a farmer in Kisumu or Kano actually using this."

Every pixel should serve that feeling.
