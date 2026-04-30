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

from mysql.DBhelpers import get_user_profile_tier1
from simplewebapp.Funhelpers import get_lisbon_greeting

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

        return render_template(
            "index.html",
            admin_email=current_app.config["ADMIN_EMAIL"],
            user=session.get("metadata"),
            metadata=session.get("metadata"),
            page_title="Mostly Jovial Crafters",
            title="Mostly Jovial Crafters",
            content_template="content/profile.html",
            greeting=session["metadata"]["greeting"],
            full_name=session["metadata"].get("full_name", ""),
            email=session["metadata"].get("email", ""),
            ign=session["metadata"].get("ign", ""),
            lastlogin=format_data(session["metadata"].get("lastlogints", "")),
            user_picture=mypict,
        )

    else:
        return redirect(url_for("signin.signin"))
