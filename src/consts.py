GH_API_URL = 'https://api.github.com'
GITHUB_URL = "https://github.com"
GIT_URL = "git@github.com:"

ORGANIZATION = "gtk-rs"
MASTER_TMP_BRANCH = "master-release-update"

BLOG_REPO = "gtk-rs.github.io"

CRATE_LIST = [
    # Sys crates
    {"crate": "glib-sys",         "repository": "gtk-rs-core", "path": "glib/sys"},
    {"crate": "gobject-sys",      "repository": "gtk-rs-core", "path": "glib/gobject-sys"},
    {"crate": "graphene-sys",     "repository": "gtk-rs-core", "path": "graphene/sys"},
    {"crate": "gio-sys",          "repository": "gtk-rs-core", "path": "gio/sys"},
    {"crate": "pango-sys",        "repository": "gtk-rs-core", "path": "pango/sys"},
    {"crate": "gdk-pixbuf-sys",   "repository": "gtk-rs-core", "path": "gdk-pixbuf/sys"},
    {"crate": "glib-macros",      "repository": "gtk-rs-core", "path": "glib-macros"},
    # glib must be published before cairo-sys (because of macros)
    {"crate": "glib",             "repository": "gtk-rs-core", "path": "glib"},
    {"crate": "cairo-sys-rs",     "repository": "gtk-rs-core", "path": "cairo/sys"},
    {"crate": "pangocairo-sys",   "repository": "gtk-rs-core", "path": "pangocairo/sys"},
    {"crate": "atk-sys",          "repository": "gtk3-rs",     "path": "atk/sys"},
    {"crate": "gdkx11-sys",       "repository": "gtk3-rs",     "path": "gdkx11/sys"},
    {"crate": "gdk-sys",          "repository": "gtk3-rs",     "path": "gdk/sys"},
    {"crate": "gtk-sys",          "repository": "gtk3-rs",     "path": "gtk/sys"},
    {"crate": "gdk4-sys",         "repository": "gtk4-rs",     "path": "gdk4/sys"},
    {"crate": "gdk4-wayland-sys", "repository": "gtk4-rs",     "path": "gdk4-wayland/sys"},
    {"crate": "gdk4-x11-sys",     "repository": "gtk4-rs",     "path": "gdk4-x11/sys"},
    {"crate": "gsk4-sys",         "repository": "gtk4-rs",     "path": "gsk4/sys"},
    {"crate": "gtk4-sys",         "repository": "gtk4-rs",     "path": "gtk4/sys"},

    # Non-sys crates
    {"crate": "gtk3-macros",      "repository": "gtk3-rs",     "path": "gtk3-macros"},
    {"crate": "gtk4-macros",      "repository": "gtk4-rs",     "path": "gtk4-macros"},
    {"crate": "graphene",         "repository": "gtk-rs-core", "path": "graphene"},
    {"crate": "atk",              "repository": "gtk3-rs",     "path": "atk"},
    {"crate": "gio",              "repository": "gtk-rs-core", "path": "gio"},
    {"crate": "pango",            "repository": "gtk-rs-core", "path": "pango"},
    {"crate": "cairo-rs",         "repository": "gtk-rs-core", "path": "cairo"},
    {"crate": "gdk-pixbuf",       "repository": "gtk-rs-core", "path": "gdk-pixbuf"},
    {"crate": "gdk",              "repository": "gtk3-rs",     "path": "gdk"},
    {"crate": "gtk",              "repository": "gtk3-rs",     "path": "gtk"},
    {"crate": "gdkx11",           "repository": "gtk3-rs",     "path": "gdkx11"},
    {"crate": "pangocairo",       "repository": "gtk-rs-core", "path": "pangocairo"},
    {"crate": "gdk4",             "repository": "gtk4-rs",     "path": "gdk4"},
    {"crate": "gdk4-wayland",     "repository": "gtk4-rs",     "path": "gdk4-wayland"},
    {"crate": "gdk4-x11",         "repository": "gtk4-rs",     "path": "gdk4-x11"},
    {"crate": "gsk4",             "repository": "gtk4-rs",     "path": "gsk4"},
    {"crate": "gtk4",             "repository": "gtk4-rs",     "path": "gtk4"},
    # {"crate": "gtk-test",         "repository": "gtk-test",    "path": ""},
]
