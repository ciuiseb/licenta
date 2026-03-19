# from app import create_app, socketio
#
# app = create_app()
#
# if __name__ == "__main__":
#     socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
import importlib.metadata

# The specific list of packages you want to verify
packages_to_check = [
    "Flask",
    "Flask-Cors",       # Note: PyPI uses dashes for distribution names, not underscores
    "Flask-SocketIO",
    "fontTools",
    "numpy",
    "scipy",
    "sympy",
    "torch"
]

print("Checking your active Python environment...\n")
print("-" * 40)

for pkg in packages_to_check:
    try:
        # This grabs the exact installed version
        version = importlib.metadata.version(pkg)
        print(f"{pkg}=={version}")
    except importlib.metadata.PackageNotFoundError:
        # If the package isn't installed at all, it will tell you
        print(f"⚠️ {pkg} is NOT installed in this environment.")

print("-" * 40)