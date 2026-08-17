# Database Schema

Six tables hosted on [Neon](https://neon.tech) (PostgreSQL).

## farmers

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, indexed |
| `name` | varchar | not null |
| `farm_country` | varchar | not null |
| `farm_state_region` | varchar | not null |
| `phone_number` | varchar | unique, not null |
| `email_address` | varchar | unique, not null |
| `area_of_farmland` | float | default 0.0 |
| `password_hash` | varchar | not null |
| `is_verified` | boolean | default false |
| `otp_verified` | boolean | default false |
| `created_at` | timestamp | not null, default now() |
| `updated_at` | timestamp | not null, default now(), on update now() |

## crop_profiles

One farmer → many crop profiles.

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, indexed |
| `farmer_id` | integer | FK → farmers.id, not null |
| `crop_type` | varchar | not null |
| `planting_month` | varchar | not null |
| `harvest_month` | varchar | not null |
| `average_yield_tons` | float | default 0.0 |

## yield_records

One record per farmer per season. `actual_yield_kg_per_ha` is filled in later when the farmer reports back.

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, indexed |
| `farmer_id` | integer | FK → farmers.id, not null |
| `crop_type` | varchar | not null |
| `season` | varchar | not null (e.g. `"Long Rains 2024"`) |
| `planting_date` | date | nullable |
| `harvest_date` | date | nullable |
| `predicted_yield_kg_per_ha` | float | not null |
| `actual_yield_kg_per_ha` | float | nullable |
| `created_at` | date | server default: current_date() |

## farmer_sessions

One row per active login session. Supports JWT access tokens and opaque refresh tokens.

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, indexed |
| `farmer_id` | integer | FK → farmers.id, not null, indexed |
| `session_id` | varchar | unique, not null, indexed (GUID) |
| `access_token` | varchar | not null |
| `refresh_token` | varchar | unique, not null |
| `access_token_expires_at` | timestamp | not null |
| `refresh_token_expires_at` | timestamp | not null |
| `is_active` | boolean | default true |
| `ip_address` | varchar | nullable |
| `user_agent` | varchar | nullable |
| `created_at` | timestamp | not null, default now() |
| `updated_at` | timestamp | not null, default now(), on update now() |

## conversations

One thread per farmer per topic. Live chat sessions are linked via `external_id` (the Redis UUID).

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, indexed |
| `farmer_id` | integer | FK → farmers.id, not null, indexed |
| `external_id` | varchar(36) | unique, nullable, indexed (UUID from live chat) |
| `title` | varchar | nullable |
| `context_type` | varchar | nullable (e.g. `"ai_chat"`, `"yield_prediction"`, `"weather_advisory"`) |
| `is_active` | varchar | default `"active"` (`"active"`, `"archived"`) |
| `created_at` | timestamp | not null, default now() |
| `updated_at` | timestamp | not null, default now(), on update now() |

## messages

Individual messages within a conversation.

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, indexed |
| `conversation_id` | integer | FK → conversations.id, not null, indexed |
| `farmer_id` | integer | FK → farmers.id, not null, indexed |
| `sender_type` | enum | not null — `farmer`, `ai` |
| `content` | text | not null |
| `context` | text | nullable (JSON string for tool call metadata) |
| `created_at` | timestamp | not null, default now(), indexed |

## Relationships

```
farmers
  ├── crop_profiles     (cascade delete)
  ├── yield_records     (cascade delete)
  ├── farmer_sessions   (backref: sessions)
  ├── conversations     (backref: conversations)
  └── messages          (backref: messages)

conversations
  └── messages          (cascade delete)
```

Deleting a farmer removes all their crop profiles, yield records, sessions, conversations, and messages.
