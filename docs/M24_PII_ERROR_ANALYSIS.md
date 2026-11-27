# MEDILOCKER M24 — PII ERROR ANALYSIS & TARGETED IMPROVEMENTS

| Failure Category | Example from Held-Out Set | Root Cause | Generalisable Fix |
|---|---|---|---|
| Context / Hinglish Label | `Mareez ka naam: Farhan Siddiqui` | `RX_LABELED_NAME` lacked `(?:\s+ka\s+naam)?` after `Mareez` | Updated `names.py:RX_LABELED_NAME` to `(?:Mareez\|Rogi)(?:\s+ka\s+naam)?` |
| Case-Sensitivity in Relative Label | `Pita ka naam: Tariq Siddiqui` | `RX_RELATIVE` lacked `(?i:...)` around Romanized Hindi kinship labels | Added `(?i:pita\s+ka\s+naam\|mata\s+ka\s+naam\|pati\s+ka\s+naam\|...)` |
| Indian Voter ID (EPIC) | `MHX4829103`, `DLQ9912345`, `UPK7712390` | Missing `VOTER_ID` column rule & `RX_VOTER_ID` pattern | Added `VOTER_ID` to `patterns.py:_COL_RULES` & `RX_VOTER_ID = \b[A-Z]{3}\d{7}\b` |
| Indian Driving Licence | `UP32 20190045123` | Missing `DRIVING_LICENCE` pattern | Added `RX_DRIVING_LICENCE` (`[A-Z]{2}\d{2}[\s-]?(?:19\|20)\d{2}\d{7}`) |
| Passport Number (Contextual) | `Passport: K4829104` | Missing contextual `RX_PASSPORT_LABEL` | Added `RX_PASSPORT_LABEL` (`Passport ... : [A-Z]\d{7}`) |
| Canary Tokens | `CANARY_M24_UNSEEN_991` | No `CANARY_*` pattern in `sanitizer.py` | Added `RX_CANARY = \bCANARY_[A-Z0-9_]{3,}\b` |
