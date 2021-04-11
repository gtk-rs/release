GH_API_URL = 'https://api.github.com'
GITHUB_URL = "https://github.com"

ORGANIZATION = "gtk-rs"
MASTER_TMP_BRANCH = "master-release-update"
CRATE_TMP_BRANCH = "crate-release-update"

BLOG_REPO = "gtk-rs.github.io"

CRATE_LIST = [
    {"crate": "glib-sys",       "repository": "sys",        "path": "glib-sys"},
    {"crate": "gobject-sys",    "repository": "sys",        "path": "gobject-sys"},
    {"crate": "gio-sys",        "repository": "sys",        "path": "gio-sys"},
    {"crate": "pango-sys",      "repository": "sys",        "path": "pango-sys"},
    {"crate": "gdk-pixbuf-sys", "repository": "sys",        "path": "gdk-pixbuf-sys"},
    {"crate": "atk-sys",        "repository": "sys",        "path": "atk-sys"},
    {"crate": "gdkx11-sys",     "repository": "sys",        "path": "gdkx11-sys",
     "doc_name": "gdk_x11_sys"},
    {"crate": "glib-macros",    "repository": "glib",       "path": "glib-macros"},
    # glib must be published before cairo-sys (because of macros)
    {"crate": "glib",           "repository": "glib",       "path": ""},
    {"crate": "cairo-sys-rs",   "repository": "cairo",      "path": "cairo-sys-rs",
     "doc_name": "cairo-sys"},
    {"crate": "gdk-sys",        "repository": "sys",        "path": "gdk-sys"},
    {"crate": "gtk-sys",        "repository": "sys",        "path": "gtk-sys"},
    {"crate": "pangocairo-sys", "repository": "sys",        "path": "pangocairo-sys",
     "doc_name": "pango_cairo_sys"},
    {"crate": "atk",            "repository": "atk",        "path": ""},
    {"crate": "gio",            "repository": "gio",        "path": ""},
    {"crate": "pango",          "repository": "pango",      "path": ""},
    {"crate": "cairo-rs",       "repository": "cairo",      "path": "",
     "doc_name": "cairo"},
    {"crate": "gdk-pixbuf",     "repository": "gdk-pixbuf", "path": ""},
    {"crate": "gdk",            "repository": "gdk",        "path": ""},
    {"crate": "gtk",            "repository": "gtk",        "path": ""},
    {"crate": "gdkx11",         "repository": "gdkx11",     "path": ""},
    {"crate": "pangocairo",     "repository": "pangocairo", "path": ""},
    {"crate": "gtk-test",       "repository": "gtk-test",   "path": ""},
]
