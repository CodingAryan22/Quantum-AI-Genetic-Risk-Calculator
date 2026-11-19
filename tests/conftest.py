import os
import sys

# The app's modules import each other as top-level modules (`import ui_modules`,
# `from ml import predictor`), the way `streamlit run final_app.py` loads them.
FINAL_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "final_app"))
if FINAL_APP not in sys.path:
    sys.path.append(FINAL_APP)
