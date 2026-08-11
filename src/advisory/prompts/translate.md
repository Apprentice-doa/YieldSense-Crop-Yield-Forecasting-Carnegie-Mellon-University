Translate the following farm advisory from English into {language_name}
(`{lang}`).

# Rules

1. **Keep every number exactly as written.** Do not convert units, re-round, or
   change digit grouping. Numerals stay numerals.
2. **Keep the meaning of each action exact.** An action is an instruction a
   farmer will follow; a softened or generalised translation is a failure.
3. Use the words a farmer in the region actually uses for crops, seasons, and
   farm operations — not literal dictionary equivalents.
4. Keep crop names recognisable locally. If there is no established local term,
   keep the English name rather than inventing one.
5. Preserve the JSON structure and keys exactly. Translate only the values.
6. Do not add, remove, explain or annotate anything.

# Input

```json
{advisory_json}
```

Return only the translated JSON object, with the same keys.
