#!/bin/bash
cd "$(dirname "$0")"
/usr/bin/python3 claude_fingerprint_detect.py
echo
if [ "${CFD_LANG:-}" = "zh" ] || { [ -z "${CFD_LANG:-}" ] && defaults read -g AppleLanguages 2>/dev/null | sed -n 2p | grep -q '"\?zh'; }; then
    read -n 1 -s -r -p "按任意键关闭窗口……"
else
    read -n 1 -s -r -p "Press any key to close..."
fi
