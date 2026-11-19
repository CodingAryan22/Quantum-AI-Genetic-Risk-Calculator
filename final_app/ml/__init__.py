"""
Machine-learning layer for RiskPredict.

    schema          - the 10 model features and how a patient form maps to them
    synthetic_data  - generates the synthetic training cohort
    quantum_kernel  - Qiskit ZZ feature map + fidelity kernel
    train           - trains and evaluates every model, writes models/ + metrics.json
    predictor       - loads the saved models and scores one patient
"""
