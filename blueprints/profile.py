from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    current_app,
    flash,
)
from markupsafe import Markup
from math import ceil

import subprocess
import json
import tempfile
import os
from mysql.DBhelpers import get_user_profile_tier1, update_mc_stats
from simplewebapp.Funhelpers import get_lisbon_greeting
from datetime import datetime
import time as _time

bp_profile = Blueprint("profile", __name__, url_prefix="/profile")


# Register the custom filter
@bp_profile.app_template_filter()
def format_data(value):
    from simplewebapp.Funhelpers.format_data import format_data as f_data
    return f_data(value)


@bp_profile.route("/")
def profile():
    """
    Renders the user's profile page.
    """
    _t0 = _time.monotonic()
    email = None
    mypict = ""

    if session and session.get("metadata"):
        email = session.get("metadata").get("email")
    else:
        return redirect(url_for("signin.signin"))

    if session and session.get("userinfo"):
        mypict = session.get("userinfo").get("picture", "")

    if email:
        # Refresh profile from DB
        _t1 = _time.monotonic()
        db_profile = get_user_profile_tier1(email)
        print(f"⏱️  PROFILE [get_user_profile_tier1]: {_time.monotonic()-_t1:.2f}s", flush=True)
        if db_profile:
            session["metadata"].update(db_profile)

        session["metadata"]["full_name"] = (
            (session["metadata"].get("first_name") or "") + " " +
            (session["metadata"].get("last_name") or "")
        ).strip()
        session["metadata"]["greeting"] = get_lisbon_greeting()

        # Fetch Minecraft stats
        from simplewebapp.Funhelpers.mc_server_status import get_mc_status
        
        _t2 = _time.monotonic()
        mc_status = get_mc_status()
        print(f"⏱️  PROFILE [get_mc_status]: {_time.monotonic()-_t2:.2f}s (online={mc_status.get('online')})", flush=True)
        ign = session["metadata"].get("ign")
        stats = {}
        last_online_display = "Unknown"
        
        # Default stats from DB
        stats = {
            "uuid": session["metadata"].get("mc_uuid") or "NA",
            "rank": session["metadata"].get("mc_rank") or "NA",
            "bank": session["metadata"].get("mc_bank") or "NA",
            "claims": session["metadata"].get("mc_claims") or "NA",
        }
        
        last_online_dt = session["metadata"].get("mc_last_online")
        if last_online_dt:
            last_online_display = format_data(last_online_dt)

        # Determine if online (heuristic based on last online timestamp vs current time, or just use server list players if available)
        is_online = False
        if mc_status.get("online") and ign:
            # simplewebapp's mc_server_status might return players_list
            players = mc_status.get("players_list", [])
            is_online = ign in players

        if is_online:
            last_online_display = "Now"
        
        # Merge mc_status into metadata for the template
        session["metadata"]["mc_status"] = mc_status

        # --- Session Cleanup Logic ---
        # 1. If server is online, clear all resume-related flags
        if mc_status.get("online"):
            session.pop("resume_in_progress", None)
            session.pop("waiting_for_resume_code", None)
            session.pop("new_resume_request", None)
        else:
            # 2. Handle "Refresh resets the token" requirement
            if session.get("waiting_for_resume_code"):
                if session.get("new_resume_request"):
                    # This is the first load after the redirect. Consume the flag.
                    session["new_resume_request"] = False
                else:
                    # The user refreshed the page or came back later. Reset to Start button.
                    session.pop("waiting_for_resume_code", None)
                    session.pop("resume_email", None)

            # 3. Check for stale progress bar
            if session.get("resume_in_progress"):
                from authenticate.server_actions import server_progress
                session_id = session.get("session_id") or session.get("resume_email")
                if not session_id or session_id not in server_progress:
                    # Task is finished, failed or lost. Clear flag to show Start button again.
                    session.pop("resume_in_progress", None)
        # -----------------------------
        print(f"⏱️  PROFILE [TOTAL]: {_time.monotonic()-_t0:.2f}s", flush=True)
        return render_template(
            "index.html",
            admin_email=current_app.config["ADMIN_EMAIL"],
            user=session.get("metadata"),
            metadata=session.get("metadata"),
            page_title="Mostly Jovial Crafters",
            title="Mostly Jovial Crafters",
            content_template="content/profile.html",
            greeting=session["metadata"]["greeting"],
            nome=session["metadata"].get("full_name", ""),
            email=session["metadata"].get("email", ""),
            ign=session["metadata"].get("ign", ""),
            lastlogin=format_data(session["metadata"].get("lastlogints", "")),
            last_online_display=last_online_display,
            user_picture=mypict,
            player_rank=stats.get("rank", "NA"),
            player_bank=stats.get("bank", "NA"),
            player_claims=stats.get("claims", "NA"),
            player_location=session["metadata"].get("mc_location", "NA"),
            player_first_login=format_data(session["metadata"].get("mc_first_login", "")),
            player_uuid=stats.get("uuid", "NA"),
        )

    else:
        return redirect(url_for("signin.signin"))
@bp_profile.route("/update_stats", methods=["POST"])
def update_stats():
    print("DEBUG: update_stats called", flush=True)
    if not session.get("metadata"):
        print("DEBUG: No session metadata found!", flush=True)
        return redirect(url_for("signin.signin"))
        
    ign = session["metadata"].get("ign")
    email = session["metadata"].get("email")
    print(f"DEBUG: ign={ign}, email={email}", flush=True)
    if not ign:
        flash("No Minecraft username linked to this account.")
        return redirect(url_for("profile.profile"))

    # Connect to MC server and run the script
    mc_user = current_app.config.get("MC_SERVER_USER", "goals_locust8006_eagereverest_co")
    mc_host = current_app.config.get("MC_SERVER_HOST", "2600:1900:4010:58a::")
    print(f"DEBUG: Connecting to {mc_user}@{mc_host}", flush=True)
    
    # Common paths for the MC server
    script_path = "/home/sargedas/mcserver/ingame_scripts/travel_time_report.py"
    stats_dir = "/home/minecraft/world/players/stats"
    remote_tmp = f"/tmp/usecache_db_{ign}.txt"
    
    cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no", f"{mc_user}@{mc_host}",
        f"python3 {script_path} {stats_dir} --server-root /home/minecraft --user {ign} --with-rank --export-db {remote_tmp}"
    ]
    
    try:
        print(f"DEBUG: Running command: {' '.join(cmd)}", flush=True)
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        print("DEBUG: SSH command succeeded", flush=True)
        
        # SCP it back
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            local_tmp = tmp_file.name
            
        scp_cmd = [
            "scp", "-o", "StrictHostKeyChecking=no",
            f"{mc_user}@{mc_host}:{remote_tmp}", local_tmp
        ]
        print(f"DEBUG: Running SCP command: {' '.join(scp_cmd)}", flush=True)
        subprocess.run(scp_cmd, check=True, timeout=10)
        print(f"DEBUG: SCP succeeded. local_tmp={local_tmp}", flush=True)
        
        # Read the file and update DB
        updated = False
        with open(local_tmp, "r", encoding="utf-8") as f:
            for line in f:
                print(f"DEBUG: Read line from SCP file: {line.strip()}", flush=True)
                data = json.loads(line.strip())
                res = update_mc_stats(
                    email,
                    data.get("uuid", "NA"),
                    data.get("rank", "NA"),
                    data.get("bank", "0.0"),
                    data.get("claims", "NA"),
                    data.get("last_online"),
                    data.get("first_login"),
                    data.get("location")
                )
                print(f"DEBUG: update_mc_stats result: {res}", flush=True)
                updated = True
                break # Only one line expected for --user <ign>
                
        os.remove(local_tmp)
        
        if updated:
            # Re-fetch the user data to update the session
            user_data = get_user_profile_tier1(email)
            if user_data:
                # Merge mc_status to preserve it
                user_data["mc_status"] = session["metadata"].get("mc_status", {})
                user_data["greeting"] = session["metadata"].get("greeting", "")
                session["metadata"] = user_data
                print(f"DEBUG: Session metadata updated successfully. location={user_data.get('mc_location')}", flush=True)
            flash("Minecraft stats updated successfully!", "success")
        else:
            print("DEBUG: No line was read from SCP file, updated=False", flush=True)
            flash("Failed to retrieve updated stats from the server.", "danger")
            
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode('utf-8') if e.stderr else 'timeout or ssh error'
        print(f"DEBUG: subprocess.CalledProcessError: {err_msg}", flush=True)
        flash(f"Failed to update stats from server: {err_msg}", "danger")
    except Exception as e:
        print(f"DEBUG: Exception: {str(e)}", flush=True)
        flash(f"An error occurred: {str(e)}", "danger")
        
    return redirect(url_for("profile.profile"))
