import os

from fastapi.templating import Jinja2Templates

# Calculate paths relative to this file: app/core/templates.py
# We want to reach {project_root}/templates
# app/core/ -> app/ -> {project_root}
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir is app/core
# .. is app
# ../.. is project root
templates_dir = os.path.join(current_dir, "..", "..", "templates")
templates_dir = os.path.normpath(templates_dir)

templates = Jinja2Templates(directory=templates_dir)
