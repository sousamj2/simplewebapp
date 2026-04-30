from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    current_app,
    flash, # Import flash
)
from markupsafe import Markup
from pprint import pprint
from math import ceil

from mysql.DBhelpers import (
    get_user_profile_tier1,
    get_user_profile_tier2,
)
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
    Renders the user's profile page with content tailored to their account tier.

    This function first ensures that the user is logged in by checking for session metadata.
    If the user is not authenticated, they are redirected to the sign-in page.

    The function retrieves the user's profile information from the database. The level of detail
    depends on the user's tier:
    - Tier 1: Basic profile information.
    - Tier 2: Includes additional details such as a full address.

    After fetching the data, it is processed and formatted for display (e.g., constructing a
    full name and address). Finally, it renders the 'profile.html' template with the
    retrieved information and embeds it within the main 'index.html' layout. The content
    displayed on the profile page is conditionally rendered based on the user's tier.
    """
    source_method = request.args.get("source_method", "GET")
    email = None
    mypict = ""

    if session and session.get("metadata"):
        email = session.get("metadata").get("email")
    else:
        return redirect(url_for("signin.signin"))

    if session and session.get("userinfo"):
        mypict = session.get("userinfo").get("picture", "")

    if email:
        # pprint("Rendering profile page...")

        # Get full profile from DB
        session["metadata"] = get_user_profile_tier1(email)
        # GET USER TIER FROM DATABASE - critical for conditional rendering
        user_tier = session["metadata"].get("tier", 1)  # Default to tier 1
        full_address = None
        zip_full = None

        if user_tier > 1:
            session["metadata"] = get_user_profile_tier2(email)
            # Build address
            g_address = session["metadata"]["address"]
            if session["metadata"]["number"] != "NA":
                g_address = (
                    session["metadata"]["address"]
                    + ", "
                    + str(session["metadata"]["number"])
                )
            full_address = g_address
            if session["metadata"]["floor"] != "NA":
                full_address = full_address + " " + str(session["metadata"]["floor"])
            if session["metadata"]["door"] != "NA":
                full_address = full_address + " " + str(session["metadata"]["door"])
            session["metadata"]["full_address"] = full_address
            session["metadata"]["g_address"] = g_address
            zip_full = (
                str(session["metadata"].get("zip_code1", ""))
                + "-"
                + str(session["metadata"].get("zip_code2", ""))
            )

        session["metadata"]["full_name"] = (
            session["metadata"]["first_name"] + " " + session["metadata"]["last_name"]
        )
        session["metadata"]["greeting"] = get_lisbon_greeting()
        # pprint(session)
        # print()


        # Render content template with tier information
        main_content_html = render_template(
            "content/profile.html",
            greeting=session["metadata"]["greeting"],
            full_name=session["metadata"].get("full_name", ""),
            email=session["metadata"].get("email", ""),
            lastlogin=format_data(session["metadata"].get("lastlogints", "")),
            user_picture=mypict,
            morada=session["metadata"].get("full_address", ""),
            codigopostal=zip_full,
            nif=session["metadata"].get("nfiscal", ""),
            telemovel=session["metadata"].get("cell_phone", ""),
            tier=user_tier,  # Pass tier to template
            vpn_check_color="green",
            primeiro_contacto_color="yellow",
            primeira_aula_color="red",
        )

        return render_template(
            "index.html",
            admin_email=current_app.config["ADMIN_EMAIL"],
            user=session.get("userinfo"),
            metadata=session.get("metadata"),
            page_title="Explicações em Lisboa",
            title="Explicações em Lisboa",
            main_content=Markup(main_content_html),
        )

    else:
        return redirect(url_for("index"))
