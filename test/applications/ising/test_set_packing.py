# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

""" Test Set Packing """

import unittest
import json
from test import QiskitOptimizationTestCase
import numpy as np

from qiskit.circuit.library import TwoLocal
from qiskit.utils import QuantumInstance, algorithm_globals
from qiskit.algorithms import NumPyMinimumEigensolver, VQE
from qiskit.algorithms.optimizers import SPSA
from qiskit_optimization.applications.ising import set_packing
from qiskit_optimization.applications.ising.common import sample_most_likely


class TestSetPacking(QiskitOptimizationTestCase):
    """Cplex Ising tests."""

    def setUp(self):
        super().setUp()
        algorithm_globals.random_seed = 2752
        input_file = self.get_resource_path('sample.setpacking',
                                            'applications/ising')
        with open(input_file) as file:
            self.list_of_subsets = json.load(file)
            self.qubit_op, _ = set_packing.get_operator(self.list_of_subsets)

    def _brute_force(self):
        # brute-force way: try every possible assignment!
        def bitfield(n, length):
            result = np.binary_repr(n, length)
            return [int(digit) for digit in result]  # [2:] to chop off the "0b" part

        subsets = len(self.list_of_subsets)
        maximum = 2 ** subsets
        max_v = -np.inf
        for i in range(maximum):
            cur = bitfield(i, subsets)
            cur_v = set_packing.check_disjoint(cur, self.list_of_subsets)
            if cur_v:
                if np.count_nonzero(cur) > max_v:
                    max_v = np.count_nonzero(cur)
        return max_v

    def test_set_packing(self):
        """ set packing test """
        algo = NumPyMinimumEigensolver()
        result = algo.compute_minimum_eigenvalue(operator=self.qubit_op, aux_operators=[])
        x = sample_most_likely(result.eigenstate)
        ising_sol = set_packing.get_solution(x)
        np.testing.assert_array_equal(ising_sol, [0, 1, 1])
        oracle = self._brute_force()
        self.assertEqual(np.count_nonzero(ising_sol), oracle)

    def test_set_packing_vqe(self):
        """ set packing vqe test """
        try:
            # pylint: disable=import-outside-toplevel
            from qiskit import Aer
        except Exception as ex:  # pylint: disable=broad-except
            self.skipTest("Aer doesn't appear to be installed. Error: '{}'".format(str(ex)))
            return

        wavefunction = TwoLocal(rotation_blocks='ry', entanglement_blocks='cz',
                                reps=3, entanglement='linear')
        q_i = QuantumInstance(Aer.get_backend('qasm_simulator'),
                              seed_simulator=algorithm_globals.random_seed,
                              seed_transpiler=algorithm_globals.random_seed)
        result = VQE(wavefunction,
                     SPSA(maxiter=200),
                     max_evals_grouped=2,
                     quantum_instance=q_i).compute_minimum_eigenvalue(operator=self.qubit_op)
        x = sample_most_likely(result.eigenstate)
        ising_sol = set_packing.get_solution(x)
        oracle = self._brute_force()
        self.assertEqual(np.count_nonzero(ising_sol), oracle)


if __name__ == '__main__':
    unittest.main()