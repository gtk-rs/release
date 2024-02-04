GH_API_URL = "https://api.github.com"
GITHUB_URL = "https://github.com"
GIT_URL = "git@github.com:"

ORGANIZATION = "gtk-rs"

BLOG_REPO = "gtk-rs.github.io"

CORE_PREVIOUS_RELEASE = "0.18"
CORE_CURRENT_RELEASE = "0.19"
GTK4_PREVIOUS_RELEASE = "0.7"
GTK4_CURRENT_RELEASE = "0.8"

CRATE_LIST = [
    # Sys crates
    {
        "crate": "glib-sys",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "gobject-sys",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "graphene-sys",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "gio-sys",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "pango-sys",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "gdk-pixbuf-sys",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "glib-macros",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    # glib must be published before cairo-sys (because of macros)
    {
        "crate": "glib",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "cairo-sys-rs",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "pangocairo-sys",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "gdk4-sys",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    {
        "crate": "gdk4-wayland-sys",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    {
        "crate": "gdk4-x11-sys",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    {
        "crate": "gsk4-sys",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    {
        "crate": "gtk4-sys",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    # Non-sys crates
    {
        "crate": "gtk4-macros",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    {
        "crate": "graphene",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "gio",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "pango",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "cairo-rs",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "gdk-pixbuf",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "pangocairo",
        "repository": "gtk-rs-core",
        "current": CORE_CURRENT_RELEASE,
        "previous": CORE_PREVIOUS_RELEASE,
    },
    {
        "crate": "gdk4",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    {
        "crate": "gdk4-wayland",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    {
        "crate": "gdk4-x11",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    {
        "crate": "gsk4",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
    {
        "crate": "gtk4",
        "repository": "gtk4-rs",
        "current": GTK4_CURRENT_RELEASE,
        "previous": GTK4_PREVIOUS_RELEASE,
    },
]
