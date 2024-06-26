import numpy as np

from qiskit.quantum_info import Pauli, SparsePauliOp
from typing import List, Literal
from numpy.typing import NDArray

import qubo, brute_force

def qubo_to_hamiltonian(qubo):
    nq = qubo.shape[0]

    h = {}
    J = {}

    # generate the h_k and J_k_k' values
    for k in range(nq):
        h_k_sum = sum(qubo[k, i] for i in range(0, nq))
        h_k_sum -= qubo[k,k]
        h[k] = 0.5 * qubo[k, k] + 0.25 * h_k_sum
        for j in range(k + 1, nq):
            J[(k, j)] = 0.25 * qubo[k, j]

    # Q_kk = sum(qubo[k, k] for k in range(n))
    # Q_kk_prime = sum(qubo[k, k_prime] for k in range(n) for k_prime in range(k + 1, n))
    Q_kk = np.sum(np.diag(qubo))
    Q_kk_prime = np.sum(np.triu(qubo, 1))
    Cte = 0.5 * Q_kk + 0.25 * Q_kk_prime

    return h, J, Cte

def construct_quantum_hamiltonian_qiskit(h, J, Cte):
    # ⚠️ QISKIT USES LITTLE ENDIANNESS >:(
    n = len(h)
    pauli_list = []
    coeffs = []

    # Constant term
    pauli_list.append(Pauli('I' * n))
    coeffs.append(Cte)

    # Linear terms
    for i in range(n):
        z_pauli = 'I' * i + 'Z' + 'I' * (n - i - 1)
        pauli_list.append(Pauli(z_pauli))
        coeffs.append(h[i])

    # Quadratic terms
    for (i, j), J_ij in J.items():
        zz_pauli = 'I' * i + 'Z' + 'I' * (j - i - 1) + 'Z' + 'I' * (n - j - 1)
        pauli_list.append(Pauli(zz_pauli))
        coeffs.append(J_ij)

    coeffs = np.array(coeffs, dtype=np.float32)
    H = SparsePauliOp(pauli_list, coeffs)
    return H

def construct_quantum_hamiltonian_diag(h, J, Cte):
    n = len(h)

    # ⚠️ THIS USES BIG ENDIANNESS :)

    # as the operator is diagonal, we just calculate the diagonal elements
    I = np.array([1,1], dtype=np.int32)

    def create_operator_diag(ops : List[NDArray], indices : List[int],  n_qubits : int):
        result = 1

        assert len(ops) == len(indices)
        if np.any([op.ndim > 1 for op in ops]):
            raise ValueError("Ops must be diagonal")

        for i in range(n_qubits):
            if i in indices:
                op = ops[indices.index(i)]
            else:
                op = I

            result = np.kron(result, op)

        return result
        
    H = np.ones((2**n), dtype=np.float32) * Cte

    Z = np.array([1,-1], dtype=np.int32)
    for i in range(n):
        H += h[i]*create_operator_diag([Z], [i], n)
    for (i, j), J_ij in J.items():
        H += J_ij*create_operator_diag([Z,Z], [i,j], n)
    return H 

def diagonalization(problem : dict, lam : float, verbose : bool = True, method : Literal['qiskit', 'diag'] = 'diag'):
    if verbose: 
        print(problem)

    Q = qubo.get_Q(problem['weights'], problem['profits'], problem['C'], lam)

    if method == 'qiskit':  
        H = construct_quantum_hamiltonian_qiskit(*qubo_to_hamiltonian(Q))
        eigvals = np.real(H.to_matrix(sparse=True).diagonal())
    elif method == 'diag':
        H = construct_quantum_hamiltonian_diag(*qubo_to_hamiltonian(Q))
        eigvals = H.data
    else: 
        raise NotImplementedError(f'{method} is not a valid method')

    lowest_eigval = np.min(eigvals)
    lowest_idx    = np.argmin(eigvals)

    if verbose:
        print('\nEigenvalue:')
        print(f'  {lowest_eigval:.2f} at position {lowest_idx}')

    # bitstring   = np.logical_not(brute_force.toBitstrings([lowest_idx], Q.shape[0])[0]).astype(int)[::-1]
    bitstring   = np.logical_not(brute_force.toBitstrings(lowest_idx, Q.shape[0])).astype(int)
    bitstring_x = bitstring[:problem['n']]
    bitstring_b = bitstring[problem['n']:]

    b = sum([bit*2**alpha for alpha, bit in enumerate(bitstring_b[:-1])])
    b += (problem['C'] + 1 - 2**(len(bitstring_b)-1))*bitstring_b[-1]
    total_weight = sum([w*x for w, x in zip(problem["weights"], bitstring_x)])
    total_profit = sum([p*x for p, x in zip(problem["profits"], bitstring_x)])
    if verbose: 
        print('\nBitstrings:')
        print(f'x : {bitstring_x} : {total_profit}')
        print(f'C = {problem["C"]} | total weight : {total_weight}')
        print(f'b : {bitstring_b} : {b}')

    return total_profit, bitstring_x, total_weight

