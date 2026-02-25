# Pokémon Data Extraction Project Summary
_Last updated: 2025-10-22 17:11_

---

## ✅ Current Script Status

### Orchestration-ready (fully tested and verified)
1. **export_all_data.py** – Orchestrator  
2. **export_tutors.py** – Tutor definitions (overlay block)  
3. **export_moves.py** – Move data  
4. **export_evolutions.py** – Species evolution data  
5. **export_tutor_learnsets.py** – Tutor learnsets (handles Egg/Bad Egg alignment correctly)  
6. **export_personal_data.py** – Personal species data + machine learnsets  
7. **export_egg_learnsets.py** – Variable-length egg move lists  
8. **export_level_up_learnsets.py** – Level-up learnsets with correct terminator handling  
9. **export_weight.py** – Species weights (validated padding & data length)  
10. **export_offspring.py** – Offspring species mapping  
11. **export_encounters.py** – Wild encounter data  
12. **export_trainers.py** – Trainer properties and party data

---

### 🧱 Awaiting Development
1. **export_items.py** – Item data block (structure TBD)

---

## 🧾 Project Notes / Completed Improvements
- Full orchestration integration completed for all worker scripts  
- Consistent configuration & logging conventions  
- Timestamped output folder creation  
- Skipping logic unified (`SKIP_FIRST = True` format)  
- INFO/WARN log system standardised  
- Documentation note to review species 494–507 handling added  

---

## 🧭 Next Steps / Action Plan

### 3️⃣ Develop `export_items.py`
**Goal:** Item definitions (price, effect, name).  
**Complexity:** Low–moderate.  
**Dependency:** None, but required before trainer exports.

### 5️⃣ Ongoing Standardisation
- Add inline config parameter documentation.  
- Maintain consistent logging style and output format.  
- Keep orchestrator/worker interface modular and predictable.

---

