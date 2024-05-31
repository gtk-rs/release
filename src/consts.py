from datetime import date


GH_API_URL = "https://api.github.com"
GITHUB_URL = "https://github.com"
GIT_URL = "git@github.com:"

ORGANIZATION = "gtk-rs"

BLOG_REPO = "gtk-rs.github.io"

CORE_RELEASE_DATE = date.fromisoformat("2024-02-04")
GTK4_RELEASE_DATE = CORE_RELEASE_DATE

REPOSITORIES = [
    {
        "name": "gtk-rs-core",
        "date": CORE_RELEASE_DATE,
    },
    {
        "name": "gtk4-rs",
        "date": GTK4_RELEASE_DATE,
    },
]
