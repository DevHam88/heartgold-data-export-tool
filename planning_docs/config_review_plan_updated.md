# 🧩 Configuration Consistency Review Plan

**Goal:** Ensure all export scripts follow a unified, clean, and well-documented configuration format.

---

## 🔹 Step 1: Verify Configuration Section
- [ ] Confirm all scripts have a **Configuration** block at the top.  
- [ ] Ensure parameters use the **same order** and naming across all scripts:
  1. `SOURCE_FILENAME`
  2. `OUTPUT_FILENAME` (or `OUTPUT_1_FILENAME`, `OUTPUT_2_FILENAME`)
  3. `LOG_FILENAME`
  4. `SKIP_FIRST` (if applicable)
  5. Any custom script parameters (e.g., `START_OFFSET`, `ENTRY_SIZE`, etc.)  

---

## 🔹 Step 2: Standardize Parameter Usage
- [ ] All Boolean parameters use `True` / `False` — **never `1` or `0`**.  
- [ ] File path parameters (`SOURCE_FILENAME`) use forward slashes `/` for cross-platform compatibility.  
- [ ] Optional parameters (like `START_OFFSET`) have sensible defaults and inline comments.

---

## 🔹 Step 3: Add Inline Documentation
Each configuration variable should include a brief comment:
```python
# Relative path to source data within the ROM contents directory
SOURCE_FILENAME = "data/a/0/1/1"

# Output filename for CSV export
OUTPUT_FILENAME = "personal_data.csv"

# Skip the first record (species_id 0)
SKIP_FIRST = True  # options: True / False
```

---

## 🔹 Step 4: Output and Logging
- [ ] Confirm terminal messages use `[OK]`, `[ERROR]`, `[WARN]`, and `[INFO]` consistently.  
- [ ] Each script should report its final output as:
  ```
  [OK] Export complete: output\<timestamp>\filename.csv
  ```
- [ ] Logs should be written to a unified `.txt` file (e.g. `log_personal_data.txt`) containing both info and warnings.  

---

## 🔹 Step 5: Orchestrator Integration
- [ ] Verify each worker script uses consistent argument parsing (`--source`, `--output`).  
- [ ] All workers should exit with a return code (`0` for success, `1` for error`).  
- [ ] Orchestrator (`export_all_data.py`) should not need per-script customization once standardization is complete.  

---

## 🔹 Step 6: Species ID Consistency and Validation
- [ ] Confirm consistent handling of **species_id 494–507** (Egg, Bad Egg, alternate forms) across all scripts to ensure alignment.  
- [ ] Review that scripts correctly skip these IDs where necessary, using `while` logic instead of single `if` checks.  
- [ ] Validate that total species counts align with expected output sizes.

---

## 🔹 Step 7: Final Sanity Check
- [ ] Confirm all filenames and paths match the intended ROM directory structure.  
- [ ] Test one standalone run and one orchestrated run to confirm behavior is identical.  
- [ ] Verify all generated CSVs appear in the timestamped output folder.
