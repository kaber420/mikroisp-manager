# OmniWISP Project Guidelines

This file provides key environment and tooling guidelines for Gemini and other AI assistants working on the OmniWISP codebase.

## 🛠️ Package Manager (Frontend)

The frontend project is located in `frontend-v2-daisy/` and **must** be managed using **`pnpm`**.
- Do **not** use `npm` or `yarn` to install dependencies or run scripts.
- To install dependencies, run:
  ```bash
  pnpm install
  ```
- To run the development server, use:
  ```bash
  pnpm dev
  ```

## 🐍 Python Virtual Environment (Backend/Scripts)

The python backend and project script environment uses a local virtual environment named **`.venv`** in the root of the workspace.
- **Virtual Environment Path:** `.venv` in the project root.
- Always activate this virtual environment before running python scripts or backend servers:
  ```bash
  source .venv/bin/activate
  ```
- Install python dependencies with pip inside the active virtual environment:
  ```bash
  pip install -r requirements.txt
  ```

## ⚠️ Editing and Modification Policy

- **Explicit Request Required:** AI assistants must **only** proceed to edit, modify, or create files when explicitly requested by the user. Do not preemptively modify or write code unless direct instruction is given.

---
*Note: Always respect these tools to keep lockfiles, dependencies, and environment configurations clean and consistent.*

