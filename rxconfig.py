import reflex as rx

config = rx.Config(
    app_name="reflex_app",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
    show_built_with_reflex=False,
)
