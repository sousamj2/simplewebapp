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
from pprint import pprint
from math import ceil

from mysql.DBhelpers import get_user_profile_tier1, update_mc_stats
from simplewebapp.Funhelpers import get_lisbon_greeting
from datetime import datetime

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
        db_profile = get_user_profile_tier1(email)
        if db_profile:
            session["metadata"].update(db_profile)

        session["metadata"]["full_name"] = (
            (session["metadata"].get("first_name") or "") + " " +
            (session["metadata"].get("last_name") or "")
        ).strip()
        session["metadata"]["greeting"] = get_lisbon_greeting()

        # Fetch Minecraft stats
        from simplewebapp.Funhelpers.mc_rcon import get_player_stats
        from simplewebapp.Funhelpers.mc_server_status import get_mc_status
        
        mc_status = get_mc_status()
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

        if ign and (mc_status.get("online") or True): # Try RCON if server might be online
            rcon_stats = get_player_stats(ign)
            if rcon_stats and rcon_stats.get("uuid") != "NA":
                stats = rcon_stats
                # Update last online if RCON says they are online
                current_time = datetime.now()
                
                print(f"[SYNC DEBUG] Online: {stats.get('is_online')}, UUID: {stats.get('uuid')}", flush=True)
                if stats.get("is_online"):
                    last_online_display = "Now"
                    last_online_val = current_time
                    
                    # Sync stats to DB ONLY while online to preserve them when offline
                    print(f"[SYNC DEBUG] Attempting DB update for {email}...", flush=True)
                    res = update_mc_stats(
                        email, 
                        stats["uuid"], 
                        stats["rank"], 
                        stats["bank"], 
                        stats["claims"], 
                        last_online_val
                    )
                    print(f"[SYNC DEBUG] DB Update Result: {res}", flush=True)
                else:
                    # If RCON returned an 'Offline for X' string, use it for display
                    if "ago" in str(stats.get("last_online", "")):
                        last_online_display = stats["last_online"]
                    
                    # Keep the timestamp value we loaded from the DB earlier
                    last_online_val = last_online_dt
                    # If RCON returned a rank/bank/claims even while offline, we can still show them
                    # but we DON'T update the database mc_last_online column with NULL.
            else:
                # If RCON failed, keep the DB value
                last_online_val = last_online_dt
        
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
            player_uuid=stats.get("uuid", "NA"),
        )

    else:
        return redirect(url_for("signin.signin"))
