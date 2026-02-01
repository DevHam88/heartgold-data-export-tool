# heartgold-data-export-tool
Extraction tool for documenting and consolidating the state of a modified Heartgold ROM. Pokemon personal data, evolutions, learnsets (level-up, egg, tutor, machine), encounters, locations, trainer classes, trainers, trainer teams, moves...etc

Pre-requisites:
- Download all script files from the repo, and all placed in the same location/directory
- Ensure Python is installed
- Ensure an unpacked ROM folder is available for HeartGold

How to use:
1. Open a CLI (e.g. PowerShell)
2. Navigate to the location of the script files: `cd ...`
3. Run the orchestration script using the command: `python export_all_data.py --source "[file_path_to_the_unpacked_folder]"`
