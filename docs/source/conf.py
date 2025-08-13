# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file contains configuration options for building the Nopayloaddb documentation.
# For a full list of options, see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys
sys.path.insert(0, os.path.abspath('../../'))

import nopayloaddb
import cdb_rest
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'nopayloaddb.settings'
django.setup()

# -- Project information -----------------------------------------------------

project = u'Nopayloaddb'
copyright = u'2025, The HEP Software Foundation'
author = u'HEP Software Foundation'

# The short X.Y version
version = u'0.3'  # TODO: Implement automatic versioning from package
# The full version, including alpha/beta/rc tags
release = u'0.3'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    # Core Sphinx extensions
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    
    # Third-party extensions for enhanced documentation
    'sphinxcontrib_django',
    'sphinx_tabs.tabs',
    'sphinx_copybutton',
    'sphinx_design',
    'sphinxcontrib.httpdomain',
]

# Source file suffix
source_suffix = '.rst'

# The master toctree document
master_doc = 'index'

# Language for content autogeneration and localization
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Extension configuration -------------------------------------------------

# -- Options for autodoc extension ------------------------------------------

# Autodoc configuration for API documentation
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'special-members': '__init__',
    'private-members': False,
    'inherited-members': False,
}

# Don't sort members alphabetically, preserve source order
autodoc_member_order = 'bysource'

# Mock imports for modules that might not be available during doc build
autodoc_mock_imports = []

# -- Options for napoleon extension -----------------------------------------

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# -- Options for todo extension ---------------------------------------------

# Show todos in output
todo_include_todos = True

# -- Options for intersphinx extension --------------------------------------

# Intersphinx mapping to link to other documentation
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'django': ('https://docs.djangoproject.com/en/stable/', 'https://docs.djangoproject.com/en/stable/_objects/'),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

# Disable problematic intersphinx auto-linking
intersphinx_disabled_reftypes = ["*"]

# -- Options for HTML output ------------------------------------------------

# The theme to use for HTML and HTML Help pages
html_theme = "sphinx_book_theme"

# Theme options are theme-specific and customize the look and feel
html_theme_options = {
    "repository_url": "https://github.com/BNLNPPS/nopayloaddb",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
    "use_download_button": True,
    "path_to_docs": "docs/source/",
    "repository_branch": "master",
    "logo": {
        "image_light": "_static/HSFLogo.png",
        "image_dark": "_static/HSFLogo.png",
    },
    # Navigation
    "collapse_navigation": False,
    "navigation_depth": 4,
    "show_navbar_depth": 2,
    
    # Table of contents
    "show_toc_level": 2,
    "toc_title": "Contents",
    
    # Header/Footer
    "extra_footer": "",
    
    # Theme styling
    "primary_sidebar_end": ["sidebar-ethical-ads"],
    "secondary_sidebar_items": ["page-toc", "edit-this-page"],
}

# Custom CSS files (relative to _static path)
html_css_files = [
    'custom.css',
]

# Logo
html_logo = "_static/HSFLogo.png"

# Favicon
html_favicon = "_static/HSFLogo.png"

# The name of an image file (within the static path) to use as favicon
html_title = f"{project} v{version}"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Don't show "Built with Sphinx" in footer
html_show_sphinx = False

# Don't show copyright in footer (we have custom footer)
html_show_copyright = True

# Show last updated timestamp
html_last_updated_fmt = '%b %d, %Y'

# -- Options for LaTeX output -----------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper')
    'papersize': 'letterpaper',
    
    # The font size ('10pt', '11pt' or '12pt')
    'pointsize': '10pt',
    
    # Additional stuff for the LaTeX preamble
    'preamble': '',
    
    # Latex figure (float) alignment
    'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files
latex_documents = [
    (master_doc, 'nopayloaddb.tex', u'Nopayloaddb Documentation',
     u'HEP Software Foundation', 'manual'),
]

# -- Options for manual page output -----------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'nopayloaddb', u'Nopayloaddb Documentation',
     [author], 1)
]

# -- Options for Texinfo output ---------------------------------------------

# Grouping the document tree into Texinfo files
texinfo_documents = [
    (master_doc, 'nopayloaddb', u'Nopayloaddb Documentation',
     author, 'nopayloaddb', 'Conditions Database for HEP Experiments.',
     'Miscellaneous'),
]

# -- Options for Epub output ------------------------------------------------

# Bibliographic Dublin Core info
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# The unique identifier of the text
epub_identifier = 'nopayloaddb'

# A unique identification for the text
epub_uid = 'nopayloaddb'

# A list of files that should not be packed into the epub file
epub_exclude_files = ['search.html']

# -- Options for linkcheck builder ------------------------------------------

# Regular expressions that match URIs that should not be checked
linkcheck_ignore = [
    # Local links that might not be available during CI
    r'http://localhost.*',
    r'http://127\.0\.0\.1.*',
    # Anchors that might not exist yet
    r'.*#.*',
]

# -- Options for sphinx-copybutton ------------------------------------------

# Strip prompts from copied code
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True
copybutton_only_copy_prompt_lines = True

# -- Options for sphinx-tabs --------------------------------------------

# Configure sphinx-tabs behavior
sphinx_tabs_disable_tab_closing = True
sphinx_tabs_valid_builders = ['html', 'linkcheck']

# -- Custom configuration for Django autodoc -------------------------------

# Configure Django settings for autodoc
def setup(app):
    """Custom setup for Sphinx application."""
    # Add custom CSS
    app.add_css_file('custom.css')
    
    # Configure Django for autodoc
    import django
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'rest_framework',
                'cdb_rest',
            ],
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            SECRET_KEY='docs-secret-key',
        )
    django.setup()

# -- HTML context configuration ---------------------------------------------

html_context = {
    # GitHub integration
    "github_url": "https://github.com/BNLNPPS/nopayloaddb",
    "github_user": "BNLNPPS",
    "github_repo": "nopayloaddb",
    "github_version": "master",
    "doc_path": "docs/source",
    
    # Version information
    "version": version,
    "release": release,
    
    # Additional context for templates
    "project_name": "Nopayloaddb",
    "project_description": "Conditions Database for High Energy Physics",
    "organization": "HEP Software Foundation",
}