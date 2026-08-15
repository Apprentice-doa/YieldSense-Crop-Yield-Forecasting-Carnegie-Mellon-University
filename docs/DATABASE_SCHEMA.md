# Database Schema

Three tables hosted on [Neon](https://neon.tech) (PostgreSQL).

## farmers

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, indexed |
| `name` | string | not null |
| `farm_country` | string | not null |
| `farm_state_region` | string | not null |
| `phone_number` | string | unique, not null |
| `email_address` | string | unique, nullable |
| `area_of_farmland` | float | default 0.0 |

## crop_profiles

Stores the crops a farmer grows. One farmer → many crop profiles.

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, indexed |
| `farmer_id` | integer | FK → farmers.id, not null |
| `crop_type` | string | not null |
| `planting_month` | string | not null |
| `harvest_month` | string | not null |
| `average_yield_tons` | float | default 0.0 |

## yield_records

One record per farmer per season. `actual_yield_kg_per_ha` is filled in later when the farmer reports back.

| Column | Type | Constraints |
|---|---|---|
| `id` | integer | PK, indexed |
| `farmer_id` | integer | FK → farmers.id, not null |
| `crop_type` | string | not null |
| `season` | string | not null (e.g. `"Long Rains 2024"`) |
| `planting_date` | date | nullable |
| `harvest_date` | date | nullable |
| `predicted_yield_kg_per_ha` | float | not null |
| `actual_yield_kg_per_ha` | float | nullable |
| `created_at` | date | server default: current date |

## Relationships

```
farmers
  ├── crop_profiles  (cascade delete)
  └── yield_records  (cascade delete)
```

Deleting a farmer removes all their crop profiles and yield records.
