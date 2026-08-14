# SMS translation review

These are the exact strings sent over 2G. For many farmers this is the
**only** form of the advisory they will ever see, so a vague or overly
formal translation is a real failure, not a style preference.

For each row, either tick it or write the correction in the last column.

Ask of each one:

- Would a farmer in the region **use these words**?
- Is the instruction still **exact**? ("irrigate within a few days" must
  not become "look after the crop")
- Is it short enough to read on a basic phone screen?

When a language is done, set `review_status: reviewed` and add your name
to `reviewed_by` in `configs/advisory_i18n.yaml`. A reviewed language is
never overwritten by the translation script.

## Kiswahili (`sw`)

Status: **unreviewed**
 · machine translation by `azure_openai:gpt-5.2`

### band_labels

| key | English | Proposed | Correction (leave blank if OK) |
|---|---|---|---|
| `critical` | Well below typical | Chini sana ya kawaida | |
| `below` | Below typical | Chini ya kawaida | |
| `on_track` | About typical | Karibu kawaida | |
| `above` | Above typical | Juu ya kawaida | |
| `unknown` | No baseline available for this crop | Hakuna kumbukumbu ya zao hili | |

### sms_actions

| key | English | Proposed | Correction (leave blank if OK) |
|---|---|---|---|
| `rainfall_low` | Rain is low. Irrigate if you can, and delay top-dressing until after watering. | Mvua ni kidogo. Mwagilia ukipata maji; subiri kuweka mbolea juu hadi umwagilie. | |
| `rainfall_high` | Heavy rain. Check drainage and clear your water channels. | Mvua nyingi. Kagua mifereji na safisha njia za maji. | |
| `soil_moisture_low` | Soil is very dry. Irrigate within a few days if water is available. | Udongo umekauka sana. Mwagilia ndani ya siku chache ukipata maji. | |
| `soil_moisture_high` | Soil is wet. Hold off irrigation and watch for root disease. | Udongo una unyevu. Acha kumwagilia; angalia ugonjwa wa mizizi. | |
| `ndvi_low` | Crop looks less green than usual. Walk the field and check for pests or dry patches. | Zao si la kijani kama kawaida. Tembea shambani; kagua wadudu au sehemu kavu. | |
| `ndvi_high` | Crop is growing well. Keep your current management. | Zao linamea vizuri. Endelea na utunzaji uliopo. | |
| `heat_stress` | Very hot. Water early morning or evening and mulch to cool the soil. | Joto kali. Mwagilia asubuhi mapema au jioni; tandaza matandazo kupooza udongo. | |
| `cold_stress` | Cold is slowing growth. Expect a later harvest. | Baridi inapunguza ukuaji. Tarajia kuvuna kuchelewa. | |
| `all_clear` | No problems found. Continue as normal and prepare for harvest. | Hakuna tatizo. Endelea kawaida na jiandae kuvuna. | |

### ui_strings

| key | English | Proposed | Correction (leave blank if OK) |
|---|---|---|---|
| `what_to_do` | What to do: | Cha kufanya: | |

## Kinyarwanda (`rw`)

Status: **unreviewed**
 · machine translation by `azure_openai:gpt-5.2`

### band_labels

| key | English | Proposed | Correction (leave blank if OK) |
|---|---|---|---|
| `critical` | Well below typical | Hasi cyane | |
| `below` | Below typical | Hasi | |
| `on_track` | About typical | Bisanzwe | |
| `above` | Above typical | Hejuru | |
| `unknown` | No baseline available for this crop | Nta bipimo by’uyu musaruro | |

### sms_actions

| key | English | Proposed | Correction (leave blank if OK) |
|---|---|---|---|
| `rainfall_low` | Rain is low. Irrigate if you can, and delay top-dressing until after watering. | Imvura ni nkeya. Niba ushoboye, kuhira; ifumbire hejuru uyitinde. | |
| `rainfall_high` | Heavy rain. Check drainage and clear your water channels. | Imvura nyinshi. Reba amazi asohoka, usukure imiyoboro y’amazi. | |
| `soil_moisture_low` | Soil is very dry. Irrigate within a few days if water is available. | Ubutaka bwumye cyane. Niba amazi ahari, hira mu minsi mike. | |
| `soil_moisture_high` | Soil is wet. Hold off irrigation and watch for root disease. | Ubutaka burimo amazi. Reka kuhira; wite ku ndwara z’imizi. | |
| `ndvi_low` | Crop looks less green than usual. Walk the field and check for pests or dry patches. | Ibihingwa ntibisa n’ibyatsi. Genda mu murima urebe udukoko n’ahumye. | |
| `ndvi_high` | Crop is growing well. Keep your current management. | Ibihingwa birakura neza. Komeza uko usanzwe ubyitaho. | |
| `heat_stress` | Very hot. Water early morning or evening and mulch to cool the soil. | Harashyushye cyane. Hira kare/ku mugoroba, usasireho ibyatsi. | |
| `cold_stress` | Cold is slowing growth. Expect a later harvest. | Ubukonje buradindiza. Teganya gusarura bitinze. | |
| `all_clear` | No problems found. Continue as normal and prepare for harvest. | Nta kibazo. Komeza bisanzwe, witegure gusarura. | |

### ui_strings

| key | English | Proposed | Correction (leave blank if OK) |
|---|---|---|---|
| `what_to_do` | What to do: | Icyo gukora: | |

## French (`fr`)

Status: **unreviewed**
 · machine translation by `azure_openai:gpt-5.2`

### band_labels

| key | English | Proposed | Correction (leave blank if OK) |
|---|---|---|---|
| `critical` | Well below typical | Bien sous la normale | |
| `below` | Below typical | Sous la normale | |
| `on_track` | About typical | Dans la normale | |
| `above` | Above typical | Au-dessus normal | |
| `unknown` | No baseline available for this crop | Pas de référence pour cette culture | |

### sms_actions

| key | English | Proposed | Correction (leave blank if OK) |
|---|---|---|---|
| `rainfall_low` | Rain is low. Irrigate if you can, and delay top-dressing until after watering. | Peu de pluie. Irriguez si possible; mettez l'engrais de couverture après. | |
| `rainfall_high` | Heavy rain. Check drainage and clear your water channels. | Fortes pluies. Vérifiez le drainage et débouchez les canaux. | |
| `soil_moisture_low` | Soil is very dry. Irrigate within a few days if water is available. | Sol très sec. Irriguez d'ici quelques jours si vous avez de l'eau. | |
| `soil_moisture_high` | Soil is wet. Hold off irrigation and watch for root disease. | Sol humide. N'irriguez pas et surveillez les maladies des racines. | |
| `ndvi_low` | Crop looks less green than usual. Walk the field and check for pests or dry patches. | Culture moins verte. Parcourez le champ: ravageurs ou zones sèches? | |
| `ndvi_high` | Crop is growing well. Keep your current management. | Culture pousse bien. Gardez vos pratiques actuelles. | |
| `heat_stress` | Very hot. Water early morning or evening and mulch to cool the soil. | Très chaud. Arrosez matin/soir et paillez pour rafraîchir le sol. | |
| `cold_stress` | Cold is slowing growth. Expect a later harvest. | Froid: la croissance ralentit. Récolte plus tardive à prévoir. | |
| `all_clear` | No problems found. Continue as normal and prepare for harvest. | Rien à signaler. Continuez normal et préparez la récolte. | |

### ui_strings

| key | English | Proposed | Correction (leave blank if OK) |
|---|---|---|---|
| `what_to_do` | What to do: | À faire : | |
