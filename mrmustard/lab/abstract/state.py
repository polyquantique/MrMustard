# Copyright 2021 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module contains the implementation of the :class:`State` class."""

from __future__ import annotations
from typing import TYPE_CHECKING

import warnings
import numpy as np

from mrmustard.types import (
    Matrix,
    Vector,
    Array,
    Tensor,
    Sequence,
    Union,
    Tuple,
    Optional,
    List,
    Iterable,
)
from mrmustard.utils import graphics
from mrmustard import settings
from mrmustard.physics import gaussian, fock
from mrmustard.math import Math

if TYPE_CHECKING:
    from .transformation import Transformation

math = Math()

# pylint: disable=too-many-instance-attributes
class State:
    r"""Base class for quantum states."""

    def __init__(
        self,
        cov: Matrix = None,
        means: Vector = None,
        eigenvalues: Array = None,
        symplectic: Matrix = None,
        ket: Array = None,
        dm: Array = None,
        modes: Sequence[int] = None,
        cutoffs: Sequence[int] = None,
        _norm: float = 1.0,
    ):
        r"""Initializes the state.

        Supply either:
            * a covariance matrix and means vector
            * an eigenvalues array and symplectic matrix
            * a fock representation (ket or dm)

        Args:
            cov (Matrix): the covariance matrix
            means (Vector): the means vector
            eigenvalues (Array): the eigenvalues of the covariance matrix
            symplectic (Matrix): the symplectic matrix mapping the thermal state with given eigenvalues to this state
            fock (Array): the Fock representation
            modes (optional, Sequence[int]): the modes in which the state is defined
            cutoffs (Sequence[int], default=None): set to force the cutoff dimensions of the state
            _norm (float, default=1.0): the norm of the state. Warning: only set if you know what you are doing.

        """
        self._purity = None
        self._fock_probabilities = None
        self._cutoffs = cutoffs
        self._cov = cov
        self._means = means
        self._eigenvalues = eigenvalues
        self._symplectic = symplectic
        self._ket = ket
        self._dm = dm
        self._norm = _norm
        if cov is not None and means is not None:
            self.is_gaussian = True
            self.num_modes = cov.shape[-1] // 2
        elif eigenvalues is not None and symplectic is not None:
            self.is_gaussian = True
            self.num_modes = symplectic.shape[-1] // 2
        elif ket is not None or dm is not None:
            self.is_gaussian = False
            self.num_modes = len(ket.shape) if ket is not None else len(dm.shape) // 2
            self._purity = 1.0 if ket is not None else None
        else:
            raise ValueError(
                "State must be initialized with either a covariance matrix and means vector, an eigenvalues array and symplectic matrix, or a fock representation"
            )
        self._modes = modes
        if modes is not None:
            assert (
                len(modes) == self.num_modes
            ), f"Number of modes supplied ({len(modes)}) must match the representation dimension {self.num_modes}"

    @property
    def modes(self):
        r"""Returns the modes of the state."""
        if self._modes is None:
            return list(range(self.num_modes))
        return self._modes

    def indices(self, modes) -> Union[Tuple[int], int]:
        r"""Returns the indices of the given modes.

        Args:
            modes (Sequence[int] or int): the modes or mode

        Returns:
            Tuple[int] or int: a tuple of indices of the given modes or the single index of a single mode
        """
        if isinstance(modes, int):
            return self.modes.index(modes)
        return tuple(self.modes.index(m) for m in modes)

    @property
    def purity(self) -> float:
        """Returns the purity of the state."""
        if self._purity is None:
            if self.is_gaussian:
                self._purity = gaussian.purity(self.cov, settings.HBAR)
                # TODO: add symplectic representation
            else:
                self._purity = fock.purity(self.fock)  # has to be dm
        return self._purity

    @property
    def is_mixed(self):
        r"""Returns whether the state is mixed."""
        return not self.is_pure

    @property
    def is_pure(self):
        r"""Returns ``True`` if the state is pure and ``False`` otherwise."""
        return np.isclose(self.purity, 1.0, atol=1e-6)

    @property
    def means(self) -> Optional[Vector]:
        r"""Returns the means vector of the state."""
        return self._means

    @property
    def cov(self) -> Optional[Matrix]:
        r"""Returns the covariance matrix of the state."""
        return self._cov

    @property
    def number_stdev(self) -> Vector:
        r"""Returns the square root of the photon number variances (standard deviation) in each mode."""
        if self.is_gaussian:
            return math.sqrt(math.diag_part(self.number_cov))

        return math.sqrt(
            fock.number_variances(self.fock, is_dm=len(self.fock.shape) == self.num_modes * 2)
        )

    @property
    def cutoffs(self) -> List[int]:
        r"""Returns the cutoff dimensions for each mode."""
        if self._cutoffs is not None:
            return self._cutoffs  # TODO: allow self._cutoffs = [N, None]
        if self._ket is None and self._dm is None:
            return fock.autocutoffs(
                self.number_stdev, self.number_means
            )  # TODO: move autocutoffs in gaussian.py and pass cov, means

        return list(
            self.fock.shape[: self.num_modes]
        )  # NOTE: triggered only if the fock representation already exists

    @property
    def shape(self) -> List[int]:
        r"""Returns the shape of the state, accounting for ket/dm representation.

        If the state is in Gaussian representation, the shape is inferred from
        the first two moments of the number operator.
        """
        # NOTE: if we initialize State(dm=pure_dm), self.fock returns the dm, which does not have shape self.cutoffs
        return self.cutoffs if self.is_pure else self.cutoffs + self.cutoffs

    @property
    def fock(self) -> Array:
        r"""Returns the Fock representation of the state."""
        if self._dm is None and self._ket is None:
            _fock = fock.fock_representation(
                self.cov, self.means, shape=self.shape, return_dm=self.is_mixed
            )
            if self.is_mixed:
                self._dm = _fock
                self._ket = None
            else:
                self._ket = _fock
                self._dm = None
        return self._ket if self._ket is not None else self._dm

    @property
    def number_means(self) -> Vector:
        r"""Returns the mean photon number for each mode."""
        if self.is_gaussian:
            return gaussian.number_means(self.cov, self.means, settings.HBAR)

        return fock.number_means(tensor=self.fock, is_dm=self.is_mixed)

    @property
    def number_cov(self) -> Matrix:
        r"""Returns the complete photon number covariance matrix."""
        if not self.is_gaussian:
            raise NotImplementedError("number_cov not yet implemented for non-gaussian states")

        return gaussian.number_cov(self.cov, self.means, settings.HBAR)

    @property
    def norm(self) -> float:
        r"""Returns the norm of the state."""
        if self.is_gaussian:
            return self._norm

        return fock.norm(self.fock, self.is_mixed)

    def ket(self, cutoffs: List[int] = None) -> Optional[Tensor]:
        r"""Returns the ket of the state in Fock representation or ``None`` if the state is mixed.

        Args:
            cutoffs List[int or None]: The cutoff dimensions for each mode. If a mode cutoff is
                ``None``, it's guessed automatically.

        Returns:
            Tensor: the ket
        """
        if self.is_mixed:
            return None

        cutoffs = (
            self.cutoffs
            if cutoffs is None
            else [c if c is not None else self.cutoffs[i] for i, c in enumerate(cutoffs)]
        )

        if self.is_gaussian:
            self._ket = fock.fock_representation(
                self.cov, self.means, shape=cutoffs, return_dm=False
            )
        else:  # only fock representation is available
            if self._ket is None:
                # if state is pure and has a density matrix, calculate the ket
                if self.is_pure:
                    self._ket = fock.dm_to_ket(self._dm)
                    return self._ket
                return None
            current_cutoffs = list(self._ket.shape[: self.num_modes])
            if cutoffs != current_cutoffs:
                paddings = [(0, max(0, new - old)) for new, old in zip(cutoffs, current_cutoffs)]
                if any(p != (0, 0) for p in paddings):
                    padded = fock.math.pad(self._ket, paddings, mode="constant")
                else:
                    padded = self._ket
                return padded[tuple(slice(s) for s in cutoffs)]
        return self._ket

    def dm(self, cutoffs: List[int] = None) -> Tensor:
        r"""Returns the density matrix of the state in Fock representation.

        Args:
            cutoffs List[int]: The cutoff dimensions for each mode. If a mode cutoff is ``None``,
                it's automatically computed.

        Returns:
            Tensor: the density matrix
        """
        if cutoffs is None:
            cutoffs = self.cutoffs
        else:
            cutoffs = [c if c is not None else self.cutoffs[i] for i, c in enumerate(cutoffs)]
        if self.is_pure:
            ket = self.ket(cutoffs=cutoffs)
            if ket is not None:
                return fock.ket_to_dm(ket)
        else:
            if self.is_gaussian:
                self._dm = fock.fock_representation(
                    self.cov, self.means, shape=cutoffs * 2, return_dm=True
                )
            elif cutoffs != (current_cutoffs := list(self._dm.shape[: self.num_modes])):
                paddings = [(0, max(0, new - old)) for new, old in zip(cutoffs, current_cutoffs)]
                if any(p != (0, 0) for p in paddings):
                    padded = fock.math.pad(self._dm, paddings + paddings, mode="constant")
                else:
                    padded = self._dm
                return padded[tuple(slice(s) for s in cutoffs + cutoffs)]
        return self._dm

    def fock_probabilities(self, cutoffs: Sequence[int]) -> Tensor:
        r"""Returns the probabilities in Fock representation.

        If the state is pure, they are the absolute value squared of the ket amplitudes.
        If the state is mixed they are the multi-dimensional diagonals of the density matrix.

        Args:
            cutoffs List[int]: the cutoff dimensions for each mode

        Returns:
            Array: the probabilities
        """
        if self._fock_probabilities is None:
            if self.is_mixed:
                dm = self.dm(cutoffs=cutoffs)
                self._fock_probabilities = fock.dm_to_probs(dm)
            else:
                ket = self.ket(cutoffs=cutoffs)
                self._fock_probabilities = fock.ket_to_probs(ket)
        return self._fock_probabilities

    def primal(self, other: Union[State, Transformation]) -> State:
        r"""Returns the post-measurement state after ``other`` is projected onto ``self``.

        ``other << self`` is other projected onto ``self``.

        If ``other`` is a ``Transformation``, it returns the dual of the transformation applied to
        ``self``: ``other << self`` is like ``self >> other^dual``.

        Note that the returned state is not normalized. To normalize a state you can use
        ``mrmustard.physics.normalize``.
        """
        if issubclass(other.__class__, State):
            remaining_modes = [m for m in other.modes if m not in self.modes]

            if self.is_gaussian and other.is_gaussian:
                prob, cov, means = gaussian.general_dyne(
                    other.cov,
                    other.means,
                    self.cov,
                    self.means,
                    other.indices(self.modes),
                    settings.HBAR,
                )
                if len(remaining_modes) > 0:
                    return State(
                        means=means,
                        cov=cov,
                        modes=remaining_modes,
                        _norm=prob if not getattr(self, "_normalize", False) else 1.0,
                    )
                return prob

            # either self or other is not gaussian
            other_cutoffs = [
                None if m not in self.modes else other.cutoffs[other.indices(m)]
                for m in other.modes
            ]
            try:
                out_fock = self._preferred_projection(other, other.indices(self.modes))
            except AttributeError:
                # matching other's cutoffs
                self_cutoffs = [other.cutoffs[other.indices(m)] for m in self.modes]
                out_fock = fock.contract_states(
                    stateA=other.ket(other_cutoffs) if other.is_pure else other.dm(other_cutoffs),
                    stateB=self.ket(self_cutoffs) if self.is_pure else self.dm(self_cutoffs),
                    a_is_mixed=other.is_mixed,
                    b_is_mixed=self.is_mixed,
                    modes=other.indices(self.modes),  # TODO: change arg name to indices
                    normalize=self._normalize if hasattr(self, "_normalize") else False,
                )

            if len(remaining_modes) > 0:
                return (
                    State(dm=out_fock, modes=remaining_modes)
                    if other.is_mixed or self.is_mixed
                    else State(ket=out_fock, modes=remaining_modes)
                )

            return (
                fock.math.abs(out_fock) ** 2
                if other.is_pure and self.is_pure
                else fock.math.abs(out_fock)
            )

        try:
            return other.dual(self)
        except AttributeError as e:
            raise TypeError(
                f"Cannot apply {other.__class__.__qualname__} to {self.__class__.__qualname__}"
            ) from e

    def __iter__(self) -> Iterable[State]:
        """Iterates over the modes and their corresponding tensors."""
        return (self.get_modes(i) for i in range(self.num_modes))

    def __and__(self, other: State) -> State:
        r"""Concatenates two states."""
        if not self.is_gaussian or not other.is_gaussian:  # convert all to fock now
            # TODO: would be more efficient if we could keep pure states as kets
            if self.is_mixed or other.is_mixed:
                self_fock = self.dm()
                other_fock = other.dm()
                dm = fock.math.tensordot(self_fock, other_fock, [[], []])
                # e.g. self has shape [1,3,1,3] and other has shape [2,2]
                # we want self & other to have shape [1,3,2,1,3,2]
                # before transposing shape is [1,3,1,3]+[2,2]
                self_idx = list(range(len(self_fock.shape)))
                other_idx = list(range(len(self_idx), len(self_idx) + len(other_fock.shape)))
                return State(
                    dm=math.transpose(
                        dm,
                        self_idx[: len(self_idx) // 2]
                        + other_idx[: len(other_idx) // 2]
                        + self_idx[len(self_idx) // 2 :]
                        + other_idx[len(other_idx) // 2 :],
                    ),
                    modes=self.modes + [m + max(self.modes) + 1 for m in other.modes],
                )
            # else, all states are pure
            self_fock = self.ket()
            other_fock = other.ket()
            return State(
                ket=fock.math.tensordot(self_fock, other_fock, [[], []]),
                modes=self.modes + [m + max(self.modes) + 1 for m in other.modes],
            )
        cov = gaussian.join_covs([self.cov, other.cov])
        means = gaussian.join_means([self.means, other.means])
        return State(
            cov=cov, means=means, modes=self.modes + [m + self.num_modes for m in other.modes]
        )

    def __getitem__(self, item):
        "setting the modes of a state (same API of `Transformation`)"
        if isinstance(item, int):
            item = [item]
        elif isinstance(item, Iterable):
            item = list(item)
        else:
            raise TypeError("item must be int or iterable")
        if len(item) != self.num_modes:
            raise ValueError(
                f"there are {self.num_modes} modes (item has {len(item)} elements, perhaps you're looking for .get_modes()?)"
            )
        self._modes = item
        return self

    def get_modes(self, item):
        r"""Returns the state on the given modes."""
        if isinstance(item, int):
            item = [item]
        elif isinstance(item, Iterable):
            item = list(item)
        else:
            raise TypeError("item must be int or iterable")

        if self.is_gaussian:
            cov, _, _ = gaussian.partition_cov(self.cov, item)
            means, _ = gaussian.partition_means(self.means, item)
            return State(cov=cov, means=means, modes=item)

        # if not gaussian
        fock_partitioned = fock.trace(
            self.dm(self.cutoffs), keep=[m for m in range(self.num_modes) if m in item]
        )
        return State(dm=fock_partitioned, modes=item)

    # TODO: refactor
    def __eq__(self, other):
        r"""Returns whether the states are equal."""
        if self.num_modes != other.num_modes:
            return False
        if not np.isclose(self.purity, other.purity, atol=1e-6):
            return False
        if self.is_gaussian and other.is_gaussian:
            if not np.allclose(self.means, other.means, atol=1e-6):
                return False
            if not np.allclose(self.cov, other.cov, atol=1e-6):
                return False
            return True
        try:
            return np.allclose(
                self.ket(cutoffs=other.cutoffs), other.ket(cutoffs=other.cutoffs), atol=1e-6
            )
        except TypeError:
            return np.allclose(
                self.dm(cutoffs=other.cutoffs), other.dm(cutoffs=other.cutoffs), atol=1e-6
            )

    def __rshift__(self, other):
        r"""Applies other (a Transformation) to self (a State), e.g., ``Coherent(x=0.1) >> Sgate(r=0.1)``."""
        if issubclass(other.__class__, State):
            raise TypeError(
                f"Cannot apply {other.__class__.__qualname__} to a state. Are you looking for the << operator?"
            )
        return other.primal(self)

    def __lshift__(self, other: State):
        r"""Implements projection onto a state or the dual transformation applied on a state.

        E.g., ``self << other`` where other is a ``State`` and ``self`` is either a ``State`` or a ``Transformation``.
        """
        return other.primal(self)

    def __add__(self, other: State):
        r"""Implements a mixture of states (only available in fock representation for the moment)."""
        if not isinstance(other, State):
            raise TypeError(f"Cannot add {other.__class__.__qualname__} to a state")
        warnings.warn("mixing states forces conversion to fock representation", UserWarning)
        return State(dm=self.dm(self.cutoffs) + other.dm(self.cutoffs))

    def __rmul__(self, other):
        r"""Implements multiplication by a scalar from the left.

        E.g., ``0.5 * psi``.
        """
        if self.is_gaussian:
            warnings.warn(
                "scalar multiplication forces conversion to fock representation", UserWarning
            )
            return self.fock  # trigger creation of fock representation
        if self._dm is not None:
            return State(dm=self.dm() * other, modes=self.modes)
        if self._ket is not None:
            return State(ket=self.ket() * other, modes=self.modes)
        raise ValueError("No fock representation available")

    def __truediv__(self, other):
        r"""Implements division by a scalar from the left.

        E.g. ``psi / 0.5``
        """
        if self.is_gaussian:
            warnings.warn("scalar division forces conversion to fock representation", UserWarning)
            return self.fock

        if self._dm is not None:
            return State(dm=self.dm() / other, modes=self.modes)
        if self._ket is not None:
            return State(ket=self.ket() / other, modes=self.modes)
        raise ValueError("No fock representation available")

    def _repr_markdown_(self):
        table = (
            f"#### {self.__class__.__qualname__}\n\n"
            + "| Purity | Norm | Num modes | Bosonic size | Gaussian | Fock |\n"
            + "| :----: | :----: | :----: | :----: | :----: | :----: |\n"
            + f"| {self.purity :.2e} | {self.norm :.2e} | {self.num_modes} | {'1' if self.is_gaussian else 'N/A'} | {'✅' if self.is_gaussian else '❌'} | {'✅' if self._ket is not None or self._dm is not None else '❌'} |"
        )

        if self.num_modes == 1:
            graphics.mikkel_plot(math.asnumpy(self.dm(cutoffs=self.cutoffs)))

        if settings.DEBUG:
            detailed_info = f"\ncov={repr(self.cov)}\n" + f"means={repr(self.means)}\n"
            return f"{table}\n{detailed_info}"

        return table
