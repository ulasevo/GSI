"""Source-owned build stages for GSI.

Each module has one job: source preparation, route manifests, page data, or
template rendering. ``build.py`` remains the friendly command-line entry point,
while these modules accept explicit paths so they can be tested without writing
to the real generated site.
"""
