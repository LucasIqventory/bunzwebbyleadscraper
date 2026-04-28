#!/usr/bin/env bash
set -euo pipefail

AGENTS_DIR="$HOME/Library/LaunchAgents"
SEND_LABEL="com.bunzwebby.scheduled-outreach"
REPORT_LABEL="com.bunzwebby.scheduled-outreach-report"
SEND_PLIST="$AGENTS_DIR/$SEND_LABEL.plist"
REPORT_PLIST="$AGENTS_DIR/$REPORT_LABEL.plist"
GUI_DOMAIN="gui/$(id -u)"

launchctl bootout "$GUI_DOMAIN" "$SEND_PLIST" 2>/dev/null || true
launchctl bootout "$GUI_DOMAIN" "$REPORT_PLIST" 2>/dev/null || true
rm -f "$SEND_PLIST" "$REPORT_PLIST"

echo "Removed launchd agents:"
echo "  $SEND_LABEL"
echo "  $REPORT_LABEL"