import pennylane as qml
from pennylane import numpy as np

# Setting up a 2-qubit simulator
dev = qml.device("default.qubit", wires=2)

@qml.qnode(dev)
def risk_circuit(inputs, weights):
    # Encoding: Map genetic markers (0 or 1) to qubit rotations
    qml.AngleEmbedding(inputs, wires=range(2))
    
    # Trainable Layer: This 'processes' the data
    qml.StronglyEntanglingLayers(weights, wires=range(2))
    
    # Measurement: Returns the probability of 'High Risk'
    return qml.expval(qml.PauliZ(0))