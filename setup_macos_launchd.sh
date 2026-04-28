#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$HOME/Library/LaunchAgents"
SEND_LABEL="com.bunzwebby.scheduled-outreach"
REPORT_LABEL="com.bunzwebby.scheduled-outreach-report"
SEND_PLIST="$AGENTS_DIR/$SEND_LABEL.plist"
REPORT_PLIST="$AGENTS_DIR/$REPORT_LABEL.plist"
GUI_DOMAIN="gui/$(id -u)"

mkdir -p "$AGENTS_DIR" "$PROJECT_DIR/leads_output"
chmod +x "$PROJECT_DIR/run_scheduled_outreach.sh" "$PROJECT_DIR/run_scheduled_report.sh"

write_interval() {
  local weekday="$1"
  local hour="$2"
  local minute="$3"
  cat <<PLIST
    <dict>
      <key>Weekday</key><integer>$weekday</integer>
      <key>Hour</key><integer>$hour</integer>
      <key>Minute</key><integer>$minute</integer>
    </dict>
PLIST
}

write_send_plist() {
  {
    cat <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$SEND_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$PROJECT_DIR/run_scheduled_outreach.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>
  <key>RunAtLoad</key>
  <false/>
  <key>StartCalendarInterval</key>
  <array>
PLIST
    for weekday in 1 2 3 4 5; do
      for hour in 9 10 11 12 13 14 15 16; do
        write_interval "$weekday" "$hour" 0
        write_interval "$weekday" "$hour" 30
      done
    done
    cat <<PLIST
  </array>
  <key>StandardOutPath</key>
  <string>$PROJECT_DIR/leads_output/launchd_outreach.out.log</string>
  <key>StandardErrorPath</key>
  <string>$PROJECT_DIR/leads_output/launchd_outreach.err.log</string>
</dict>
</plist>
PLIST
  } > "$SEND_PLIST"
}

write_report_plist() {
  {
    cat <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$REPORT_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$PROJECT_DIR/run_scheduled_report.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>
  <key>RunAtLoad</key>
  <false/>
  <key>StartCalendarInterval</key>
  <array>
PLIST
    for weekday in 1 2 3 4 5; do
      write_interval "$weekday" 17 5
    done
    cat <<PLIST
  </array>
  <key>StandardOutPath</key>
  <string>$PROJECT_DIR/leads_output/launchd_report.out.log</string>
  <key>StandardErrorPath</key>
  <string>$PROJECT_DIR/leads_output/launchd_report.err.log</string>
</dict>
</plist>
PLIST
  } > "$REPORT_PLIST"
}

write_send_plist
write_report_plist

launchctl bootout "$GUI_DOMAIN" "$SEND_PLIST" 2>/dev/null || true
launchctl bootout "$GUI_DOMAIN" "$REPORT_PLIST" 2>/dev/null || true
launchctl bootstrap "$GUI_DOMAIN" "$SEND_PLIST"
launchctl bootstrap "$GUI_DOMAIN" "$REPORT_PLIST"
launchctl enable "$GUI_DOMAIN/$SEND_LABEL"
launchctl enable "$GUI_DOMAIN/$REPORT_LABEL"

echo "Installed launchd agents:"
echo "  $SEND_LABEL"
echo "  $REPORT_LABEL"
echo "Plists written to:"
echo "  $SEND_PLIST"
echo "  $REPORT_PLIST"
echo "Logs: $PROJECT_DIR/leads_output/scheduled_outreach_task.log"