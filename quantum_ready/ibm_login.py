"""
Saves your IBM Quantum API key on this computer (once), so run_experiment.py
can use real quantum hardware.

    python ibm_login.py

1. Create a free account at https://quantum.cloud.ibm.com
2. Copy your API key from the dashboard.
3. Run this script and paste it when asked (it is not shown while you type).

The key is stored by Qiskit in your user folder (~/.qiskit/qiskit-ibm.json),
never in this project, so it cannot be committed to git by accident.
"""

from getpass import getpass

import qready  # noqa: F401
from qiskit_ibm_runtime import QiskitRuntimeService

from qready.backends import IBM_CHANNEL


def main():
    token = getpass("IBM Quantum API key: ").strip()
    if not token:
        print("No key entered; nothing saved.")
        return
    instance = input("Instance CRN (press Enter to use your default): ").strip() or None
    QiskitRuntimeService.save_account(channel=IBM_CHANNEL, token=token, instance=instance,
                                      set_as_default=True, overwrite=True)
    print("Saved. Checking the connection ...")
    service = QiskitRuntimeService()
    names = [b.name for b in service.backends(operational=True, simulator=False)]
    print("Connected. Devices you can use:", ", ".join(names) or "(none right now)")


if __name__ == "__main__":
    main()
