

## 🛠️ Dependency Management (Updating Python Libraries)

We use **`pip-tools`** to manage and lock all Python dependencies, ensuring a fully reproducible environment across all containers. Direct dependencies are listed in the `.in` files, and the full dependency tree is frozen in the `.txt` files.

### The Two-File Principle

| File | Purpose | Management |
| :--- | :--- | :--- |
| **`requirements.in`** | **Source of Truth.** Lists only the top-level packages (e.g., `django==5.0.3`). **Manually edited** for adding new libraries or changing major version pins. |
| **`requirements.txt`** | **Lock File.** Contains *every* dependency and sub-dependency, with specific versions and hashes. **Generated automatically** by `pip-compile`. |

### How to Update Dependencies

To ensure reproducibility, use the dedicated update script. This script automatically runs `pip-compile` to determine the latest compatible versions, and then uses `./pin_in_file.sh` to lock those versions back into the `.in` file.

1.  **Activate Your Environment** 💻
    Always ensure your virtual environment is active before running `pip-tools` commands on your host system:

    ```bash
    source venv/bin/activate
    ```

2.  **Edit the `.in` File (If needed)** 📝
    If you are adding a new package or explicitly want to upgrade a major version (e.g., from Django 4 to Django 5), manually edit the relevant file:

      * `project0/api/requirements.in`
      * `project0/django_app/requirements.in`

3.  **Run the Automated Update Script** 🚀
    Execute the wrapper script, passing the path to the project directory you want to update. This will update both the `.txt` and `.in` files.

    ```bash
    # For the FastAPI/API project:
    ./update_deps.sh project0/api

    # For the Django project:
    ./update_deps.sh project0/django_app
    ```

4.  **Commit Both Files** ✅
    You **must** commit the changes to both the `.in` and `.txt` files in a single commit to ensure consistency in the repository.

    ```bash
    git add project0/api/requirements.in project0/api/requirements.txt
    git commit -m "chore(deps): Upgrade Django and lock dependencies"
    ```

### To Upgrade to the Latest Patch Versions

If you want to upgrade *all* packages to their latest compatible patch versions without changing the major versions currently pinned in your `.in` file, you can run the update script with the `--upgrade` flag (assuming you modify your `update_deps.sh` to pass this flag through to `pip-compile`):

```bash
# Example update command (requires modification to update_deps.sh to support flags):
./update_deps.sh project0/api --upgrade
```