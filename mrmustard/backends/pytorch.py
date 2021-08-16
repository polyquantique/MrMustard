import numpy as np
import torch
from mrmustard.backends import BackendInterface, Autocast
from thewalrus._hermite_multidimensional import hermite_multidimensional_numba, grad_hermite_multidimensional_numba
from mrmustard._typing import *

#  NOTE: the reason why we have a class with methods and not a namespace with functions
#  is that we want to enforce the interface, in order to ensure compatibility
#  of new backends with the rest of the codebase.

class Backend(BackendInterface):

    float64 = torch.float64
    float32 = torch.float32
    complex64 = torch.complex64
    complex128 = torch.complex128

    # ~~~~~~~~~
    # Basic ops
    # ~~~~~~~~~

    def atleast_1d(self, array: torch.Tensor, dtype=None) -> torch.Tensor:
        return self.cast(tf.reshape(array, [-1]), dtype)

    def astensor(self, array: Union[np.ndarray, torch.Tensor], dtype=None) -> torch.Tensor:
        return tf.convert_to_tensor(array, dtype=dtype)
    
    def conj(self, array: torch.Tensor) -> torch.Tensor:
        return torch.conj(array)

    def real(self, array: torch.Tensor) -> torch.Tensor:
        return torch.real(array)

    def imag(self, array: torch.Tensor) -> torch.Tensor:
        return torch.imag(array)

    def cos(self, array: torch.Tensor) -> torch.Tensor:
        return torch.cos(array)

    def cosh(self, array: torch.Tensor) -> torch.Tensor:
        return torch.cosh(array)

    def sinh(self, array: torch.Tensor) -> torch.Tensor:
        return torch.sinh(array)

    def sin(self, array: torch.Tensor) -> torch.Tensor:
        return torch.sin(array)

    def exp(self, array: torch.Tensor) -> torch.Tensor:
        return torch.exp(array)

    def sqrt(self, x: torch.Tensor, dtype=None) -> torch.Tensor:
        return self.cast(torch.sqrt(x), dtype)

    def lgamma(self, x: torch.Tensor) -> torch.Tensor:
        return torch.lgamma(x)

    def log(self, x: torch.Tensor) -> torch.Tensor:
        return torch.log(x)

    def cast(self, x: torch.Tensor, dtype=None) -> torch.Tensor:
        if dtype is None:
            return x
        return x.to(dtype)

    @Autocast()
    def maximum(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return torch.maximum(a, b)

    @Autocast()
    def minimum(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return torch.minimum(a, b)

    def abs(self, array: torch.Tensor) -> torch.Tensor:
        return torch.abs(array)

    def expm(self, matrix: torch.Tensor) -> torch.Tensor:
        return torch.matrix_exp(matrix)

    def norm(self, array: torch.Tensor) -> torch.Tensor:
        'Note that the norm preserves the type of array'
        return torch.norm(array)

    @Autocast()
    def matmul(self, a: torch.Tensor, b: torch.Tensor, transpose_a=False, transpose_b=False, adjoint_a=False, adjoint_b=False)  -> torch.Tensor:
        return torch.matmul(a, b)

    @Autocast()
    def matvec(self, a: torch.Tensor, b: torch.Tensor, transpose_a=False, adjoint_a=False) -> torch.Tensor:
        return tf.linalg.matvec(a, b, transpose_a, adjoint_a)

    @Autocast()
    def tensordot(self, a: torch.Tensor, b: torch.Tensor, axes: List[int]) -> torch.Tensor:
        return torch.Tensordot(a, b, axes)

    def einsum(self, string: str, *tensors) -> torch.Tensor:
        return torch.einsum(string, *tensors)

    def inv(self, a: torch.Tensor) -> torch.Tensor:
        return torch.inverse(a)

    def pinv(self, array: torch.Tensor) -> torch.Tensor:
        return torch.pinv(array)

    def det(self, a: torch.Tensor) -> torch.Tensor:
        return torch.det(a)

    def tile(self, array: torch.Tensor, repeats: Sequence[int]) -> torch.Tensor:
        return torch.tile(array, repeats)

    def diag(self, array: torch.Tensor, k: int = 0) -> torch.Tensor:
        return torch.diag(array, k=k)

    def diag_part(self, array: torch.Tensor) -> torch.Tensor:
        return torch.diag_embed(array)

    def pad(self, array: torch.Tensor, paddings: Sequence[Tuple[int, int]], mode='CONSTANT', constant_values=0) -> torch.Tensor:
        return tf.pad(array, paddings, mode, constant_values)

    @Autocast()
    def convolution(self, array: torch.Tensor, filters: torch.Tensor, strides: Optional[List[int]] = None, padding='VALID', data_format='NWC', dilations: Optional[List[int]] = None) -> torch.Tensor:
        return tf.nn.convolution(array, filters, strides, padding, data_format, dilations)

    def transpose(self, a: torch.Tensor, perm: List[int] = None) -> torch.Tensor:
        if a is None:
            return None  # TODO: remove and address None inputs where transpose is used
        return torch.transpose(a, perm[0], perm[1])

    def reshape(self, array: torch.Tensor, shape: Sequence[int]) -> torch.Tensor:
        return torch.reshape(array, shape)

    def sum(self, array: torch.Tensor, axes: Sequence[int]=None):
        return torch.sum(array, axes)

    def arange(self, start: int, limit: int = None, delta: int = 1, dtype=tf.float64) -> torch.Tensor:
        return torch.arange(start, limit, delta, dtype=dtype)

    @Autocast()
    def outer(self, array1: torch.Tensor, array2: torch.Tensor) -> torch.Tensor:
        return torch.Tensordot(array1, array2, [[], []])

    def eye(self, size: int, dtype=tf.float64) -> torch.Tensor:
        return torch.eye(size, dtype=dtype)

    def zeros(self, shape: Sequence[int], dtype=tf.float64) -> torch.Tensor:
        return torch.zeros(shape, dtype=dtype)

    def zeros_like(self, array: torch.Tensor) -> torch.Tensor:
        return torch.zeros_like(array)

    def ones(self, shape: Sequence[int], dtype=tf.float64) -> torch.Tensor:
        return torch.ones(shape, dtype=dtype)

    def ones_like(self, array: torch.Tensor) -> torch.Tensor:
        return torch.ones_like(array)

    def gather(self, array: torch.Tensor, indices: torch.Tensor, axis: int = None) -> torch.Tensor:
        return tf.gather(array, indices, axis=axis)

    def trace(self, array: torch.Tensor, dtype=None) -> torch.Tensor:
        return self.cast(tf.linalg.trace(array), dtype)

    def concat(self, values: Sequence[torch.Tensor], axis: int) -> torch.Tensor:
        return torch.cat(values, axis)

    def update_tensor(self, tensor: torch.Tensor, indices: torch.Tensor, values: torch.Tensor):
        return torch.Tensor_scatter_nd_update(tensor, indices, values)

    def update_add_tensor(self, tensor: torch.Tensor, indices: torch.Tensor, values: torch.Tensor):
        return torch.Tensor_scatter_nd_add(tensor, indices, values)

    def constraint_func(self, bounds: Tuple[Optional[float], Optional[float]]) -> Optional[Callable]:
        bounds = (-np.inf if bounds[0] is None else bounds[0], np.inf if bounds[1] is None else bounds[1])
        if not bounds == (-np.inf, np.inf):
            constraint: Optional[Callable] = lambda x: tf.clip_by_value(x, bounds[0], bounds[1])
        else:
            constraint = None
        return constraint

    def new_variable(self, value, bounds: Tuple[Optional[float], Optional[float]], name: str, dtype=tf.float64):
        return tf.Variable(value, name=name, dtype=dtype, constraint=self.constraint_func(bounds))

    def new_constant(self, value, name: str, dtype=tf.float64):
        return tf.constant(value, dtype=dtype, name=name)

    def asnumpy(self, tensor: torch.Tensor) -> Tensor:
        return tensor.numpy()

    def hash_tensor(self, tensor: torch.Tensor) -> str:
        raise NotImplementedError

    @tf.custom_gradient
    def hermite_renormalized(self, A: torch.Tensor, B: torch.Tensor, C: torch.Tensor, shape: Tuple[int]) -> torch.Tensor:  # TODO this is not ready
        r"""
        Renormalized multidimensional Hermite polynomial given by the "exponential" Taylor series
        of exp(Ax^2 + Bx + C) at zero, where the series has `sqrt(n!)` at the denominator rather than `n!`.

        Args:
            A: The A matrix.
            B: The B vector.
            C: The C scalar.
            shape: The shape of the final tensor.
        Returns:
            The renormalized Hermite polynomial of given shape.
        """
        raise NotImplementedError

    def DefaultEuclideanOptimizer(self) -> tf.keras.optimizers.Optimizer:
        r"""
        Default optimizer for the Euclidean parameters.
        """
        raise NotImplementedError

    def loss_and_gradients(self, cost_fn: Callable, parameters: Dict[str, List[Trainable]]) -> Tuple[torch.Tensor, Dict[str, List[torch.Tensor]]]:
        r"""
        Computes the loss and gradients of the given cost function.

        Arguments:
            cost_fn (Callable with no args): The cost function.
            parameters (Dict): The parameters to optimize in three kinds:
                symplectic, orthogonal and euclidean.
        
        Returns:
            The loss and the gradients.
        """
        raise NotImplementedError