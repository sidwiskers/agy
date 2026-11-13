#!/usr/bin/env python3
"""
web/patch_main.py - Dynamic patcher for web/main.js.

1. Locates the Appearance settings block and injects the Desktop Mode toggle.
2. Locates the vKa trajectory state manager class and injects host-resume
   stream reconnect/recovery logic to prevent UI stalling when backgrounded.
3. Injects live notification shade and lockscreen progress callbacks into
   Hca (ConnectRPC StreamAgentStateUpdates) and Hja (state provider sync).
4. Patches default dark themes and Vesper to pure AMOLED pitch black (#000000).
Safe, idempotent, and resilient to upstream changes.
"""

import sys
import os
import re

def patch_desktop_mode(content):
    if "Desktop Mode" in content or "ag_desktop_mode" in content:
        print("[web-patch] Desktop Mode toggle already present in main.js")
        return content

    # 1. State hook injection pattern in Appearance component:
    hook_pattern = re.compile(r'(var\s+[A-Za-z0-9_$]+=[A-Za-z0-9_$]+!==3,\s*[A-Za-z0-9_$]+=[A-Za-z0-9_$]+!==2,\s*[A-Za-z0-9_$]+=[A-Za-z0-9_$]+=>\s*[A-Za-z0-9_$]+=>\{.*?\};)')
    hook_match = hook_pattern.search(content)

    # 2. JSX Theme element injection: find Theme element in Appearance
    theme_idx = content.find('{label:"Theme"')
    theme_match = None
    react_id = "A"
    if theme_idx != -1:
        window_start = max(0, theme_idx - 100)
        window_end = min(len(content), theme_idx + 500)
        window_text = content[window_start:window_end]
        theme_pattern = re.compile(
            r'([A-Za-z0-9_$]+)\.createElement\(([A-Za-z0-9_$]+),\{label:"Theme",.*?onSelect:[A-Za-z0-9_$]+\}\)'
        )
        theme_match = theme_pattern.search(window_text)
        if theme_match:
            react_id = theme_match.group(1)

    if not hook_match or not theme_match:
        print(f"[web-patch] desktop mode patterns not matched: hook={bool(hook_match)}, theme={bool(theme_match)}", file=sys.stderr)
        return content

    orig_hook = hook_match.group(1)
    injected_hook = (
        f"var [isDesktop,setIsDesktop]=(0,{react_id}.useState)(()=>{{"
        "try{if(window.Android&&typeof window.Android.isDesktopMode==='function')return window.Android.isDesktopMode();"
        "var s=localStorage.getItem('ag_desktop_mode');return s===null?!1:s==='true'}catch(_){return !1}});"
        f"var onDesktopToggle=(0,{react_id}.useCallback)(v=>{{"
        "setIsDesktop(v);try{localStorage.setItem('ag_desktop_mode',String(v));"
        "if(window.Android&&typeof window.Android.setDesktopMode==='function')window.Android.setDesktopMode(v)}catch(_){}},[]);"
        + orig_hook
    )

    item_comp = "v3"
    switch_comp = "dX"
    re_idx = content.find('rightElement:')
    if re_idx != -1:
        re_window = content[max(0, re_idx - 150):min(len(content), re_idx + 150)]
        item_m = re.search(r'([A-Za-z0-9_$]+)\.createElement\(([A-Za-z0-9_$]+),\{label:[^,]+,description:[^,]+,rightElement:', re_window)
        if item_m:
            item_comp = item_m.group(2)
        sw_m = re.search(r'rightElement:[A-Za-z0-9_$]+\.createElement\(([A-Za-z0-9_$]+),\{checked:', re_window)
        if sw_m:
            switch_comp = sw_m.group(1)

    orig_theme = theme_match.group(0)
    injected_theme = (
        orig_theme
        + f',{react_id}.createElement({item_comp},{{label:"Desktop Mode",description:"Use desktop viewport and user agent for the workspace",'
        + f'rightElement:{react_id}.createElement({switch_comp},{{checked:isDesktop,onCheckedChange:onDesktopToggle}})}})'
    )

    content = content.replace(orig_hook, injected_hook, 1)
    content = content.replace(orig_theme, injected_theme, 1)
    print("[web-patch] Successfully patched Desktop Mode toggle into main.js")
    return content

def patch_trajectory_resume(content):
    if "__agTrajManager" in content:
        print("[web-patch] Trajectory resume manager already present in main.js")
        return content

    traj_pattern = re.compile(
        r'(class vKa\{constructor\([A-Za-z0-9_$]+\)\{this\.([A-Za-z0-9_$]+)=new Map;this\.getAgentStates=\(\)=>this\.\2;this\.setFactory=([A-Za-z0-9_$]+)=>\{this\._factory=\3;for\(let \[([A-Za-z0-9_$]+),([A-Za-z0-9_$]+)\]of this\.\2\.entries\(\)\)\{.*?\}\};)'
    )
    m = traj_pattern.search(content)
    if not m:
        print("[web-patch] vKa trajectory manager pattern not matched in main.js", file=sys.stderr)
        return content

    orig = m.group(1)
    states_prop = m.group(2)
    injected = (
        orig
        + f"this.refresh=()=>{{try{{if(this._factory&&this.{states_prop}){{for(let [c,e]of this.{states_prop}.entries()){{let b=c,f=e;try{{f.link&&f.link.dispose()}}catch(_){{}}try{{f.underlyingProvider&&f.underlyingProvider.dispose()}}catch(_){{}}f.underlyingProvider=this._factory(b);f.link=Hja(f.underlyingProvider,f.provider,{{omitInitial:!0}});try{{if(window.__agUpdateProgress&&f.provider&&f.provider.getState){{window.__agUpdateProgress(f.provider.getState())}}}}catch(_){{}}}}}}}}catch(err){{console.warn(\"[vKa] refresh error:\",err)}}}};"
        + "window.__agTrajManager=this;"
        + "window.addEventListener(\"agy:host-resume\",()=>{{this.refresh()}});"
    )
    content = content.replace(orig, injected, 1)
    print("[web-patch] Successfully patched Trajectory resume recovery into main.js")
    return content

def patch_notification_progress(content):
    if "window.__agUpdateProgress&&window.__agUpdateProgress(B)" in content:
        print("[web-patch] Notification progress hook already present in main.js")
        return content

    # 1. Hook Hca (ConnectRPC stream handler)
    hca_target = "c(B),t?.(B)"
    if hca_target in content:
        content = content.replace(
            hca_target,
            "c(B),t?.(B),window.__agUpdateProgress&&window.__agUpdateProgress(B)",
            1
        )
        print("[web-patch] Successfully hooked Hca agent state stream for notifications")
    else:
        print("[web-patch] WARNING: Hca target not found in main.js", file=sys.stderr)

    # 2. Hook Hja (state provider event link)
    hja_target = "a.onDidChange(e=>b.setState(e))"
    if hja_target in content:
        content = content.replace(
            hja_target,
            "a.onDidChange(e=>{b.setState(e);window.__agUpdateProgress&&window.__agUpdateProgress(e)})",
            1
        )
        print("[web-patch] Successfully hooked Hja state provider link for notifications")
    else:
        print("[web-patch] WARNING: Hja target not found in main.js", file=sys.stderr)

    return content

def patch_amoled_theme(content):
    patched = False
    # 1. SY default dark theme preset
    sy_target = 'SY={background:"#101010",foreground:"#cccccc",primary:"#007acc"}'
    if sy_target in content:
        content = content.replace(
            sy_target,
            'SY={background:"#000000",foreground:"#cccccc",primary:"#007acc"}',
            1
        )
        patched = True

    # 2. "Default Dark" theme preset
    def_dark_target = '"Default Dark":{background:"#101010"'
    if def_dark_target in content:
        content = content.replace(
            def_dark_target,
            '"Default Dark":{background:"#000000"',
            1
        )
        patched = True

    # 3. "Vesper" dark theme preset
    vesper_target = 'Vesper:{background:"#101010"'
    if vesper_target in content:
        content = content.replace(
            vesper_target,
            'Vesper:{background:"#000000"',
            1
        )
        patched = True

    if patched:
        print("[web-patch] Successfully patched dark themes to pure AMOLED (#000000)")
    else:
        print("[web-patch] AMOLED theme patterns already applied or not matched")

    return content

def patch_main(file_path):
    if not os.path.isfile(file_path):
        print(f"[web-patch] file not found: {file_path}", file=sys.stderr)
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = patch_desktop_mode(content)
    new_content = patch_trajectory_resume(new_content)
    new_content = patch_notification_progress(new_content)
    new_content = patch_amoled_theme(new_content)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    return True

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "main.js")
    if not patch_main(path):
        sys.exit(1)
