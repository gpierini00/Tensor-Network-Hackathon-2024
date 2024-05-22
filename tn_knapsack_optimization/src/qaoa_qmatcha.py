# -*- coding: utf-8 -*-
"""QAOA_qmatcha.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1BLAdPbMtFRhWb0U-KFO5zngADNDHaRcf
"""

!pip install qiskit==0.45.0

!pip install qiskit_algorithms

pip install -U qiskit-aer

from qiskit.circuit.library import TwoLocal, RZZGate, SwapGate
import numpy as np
from scipy.optimize import minimize
import qtealeaves.observables as obs
from qmatchatea import QCOperators, run_simulation
from qiskit import QuantumCircuit

def qaoa_step(theta, ansatz, observables):
    ops = QCOperators()
    ops.ops["Z"] = np.array([[1, 0], [0, -1]])
    # bind the parametric ansatz to the parameters
    binded_ansatz = ansatz.assign_parameters(theta)
    # Run the simulation
    res = run_simulation(binded_ansatz, observables=observables, operators=ops)

    return np.real(res.observables["hamiltonian"])

def qaoa_all(H, reps=2):
    num_qubits = np.shape(H.to_matrix())[0]
    qc = QuantumCircuit(num_qubits)

    gamma = []
    beta = []
    for ii in range(num_qubits):
        qc.h(ii)

    for ii in range(num_qubits):
        qc.rz(2 * gamma * h[ii], ii)

    for ii in range(num_qubits):
        for jj in range(ii):
            qc.rzz(2 * gamma * J[(jj,ii)], jj, ii)

    for ii in range(num_qubits):
        qc.rx(2 * beta, ii)

    return qc



def operators(H, h, J):
    num_qubits = np.shape(H.to_matrix())[0]
    local = [
            {
                "label": "I" * ii + "Z" + "I" * (num_qubits - ii - 1),
                "coeff": {"real": h[ii], "imag": 0},
            }
            for ii in range(num_qubits)
        ]


    for (i, j), J_ij in J.items():
          two_body = [
          {
              "label": "I" * i + "Z" + "I" * (j - i - 1) + "Z" + "I" * (num_qubits - j - 1),
              "coeff": {"real": J_ij, "imag": 0},
          }
      ]

    pauli_dict_hamiltonian = {"paulis": local + two_body}

    return pauli_dict_hamiltonian

def main():

    pauli_dict_hamiltonian = operators(H, h, J)
    obsv = obs.TNObservables()
    ham = obs.TNObsWeightedSum.from_pauli_string("hamiltonian", pauli_dict_hamiltonian)
    obsv += ham

    qc = qaoa_all(H, 3)
    qaoa_step_opt = lambda x: qaoa_step(x, qc, obsv)
    initial_guess = np.random.normal(np.pi / 2, 0.05, qc.num_parameters)
    initial_energy = qaoa_step_opt(initial_guess)
    print(f"Initial energy: {initial_energy}")

    res = minimize(qaoa_step_opt, initial_guess, method="COBYLA")

    final_energy = qaoa_step_opt(res.x)
    print(f"Final energy: {final_energy}")
