#!/bin/bash
export DEEPSEEK_API_KEY="sk-16caa5fa996a4beabb02e9ed94b586bc"
source /root/.bashrc
cd /root/ai-project-coach/skills/daily-project-radar/scripts
python3 daily_radar.py --history ../assets/recommended_history.json >>
/tmp/daily_radar.log 2>&1