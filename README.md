# Simple Web App Module

This module serves as the primary entry point and front-end host for the application.

## Responsibilities

- **Application Factory:** Contains the `create_app()` logic (`app.py`) which initializes Flask, loads configurations, and registers all blueprints from other modules.
- **Routing:** Manages non-authentication routes such as the home page (`bp_home`), user profile (`bp_profile`), maps, calendar, and administration panel.
- **Templating:** Houses all Jinja2 HTML templates (`/templates`) used across the application.
- **Static Assets:** Serves CSS, JavaScript, and images (`/static`). It features a modern, variable-based theme switcher supporting Light, Dark, and System modes.

## Architecture Notes
- Operates primarily using Flask Blueprints.
- Connects to the `mysql` module to retrieve profile data (e.g., handling tiered user profiles).
- Employs `ProxyFix` for secure operation behind reverse proxies.