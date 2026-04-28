@echo off
cd /d "%~dp0"
if not exist "leads_output" mkdir "leads_output"
".venv\Scripts\python.exe" "scheduled_outreach.py" report --reason "business day ended" >> "leads_output\scheduled_outreach_task.log" 2>&1