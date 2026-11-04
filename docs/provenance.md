# Case provenance

Public source distribution: SentryWard `421ff2c7d140341f64d2bc1f1edd045b65a7c403`.

| Case | Record origin | Public source mapping |
| --- | --- | --- |
| WeightNorm | Local record | [public distribution](https://github.com/gpu-verifier/sentryward/tree/421ff2c7d140341f64d2bc1f1edd045b65a7c403) |
| Shared exchange | Local record | Original project microfixture; not upstream kernel code |
| Barrier control | Local record | Original project microfixture; not upstream kernel code |
| MultiMarginLoss | Local record | [public distribution](https://github.com/gpu-verifier/sentryward/tree/421ff2c7d140341f64d2bc1f1edd045b65a7c403) |
| LayerNorm | Upstream record | [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/layer_norm_kernel.cu); [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/block_reduce.cuh); [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/SharedReduceOps.h) |
| MaxUnpooling | Upstream record | [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/MaxUnpooling.cu#L30-L50); [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/MaxUnpooling.cu#L116-L213); [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/cuda/detail/KernelUtils.h#L15-L19) |
| Softmax | Upstream record | [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/SoftMax.cu); [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/block_reduce.cuh); [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/PersistentSoftmax.cuh); [source](https://github.com/pytorch/pytorch/blob/2b3ec34829036a65cd9d1398ea72a0167dc37470/aten/src/ATen/native/cuda/MemoryAccess.cuh) |
| Async copy | Upstream record | [source](https://github.com/triton-lang/triton/blob/c01b6774b1865984607d89d89d3a10833de92037/python/tutorials/gluon/03-async-copy.py) |
| TMA pipeline | Upstream record | [source](https://github.com/triton-lang/triton/blob/c01b6774b1865984607d89d89d3a10833de92037/python/tutorials/gluon/04-tma.py#L266-L363) |
| Tensor-memory copy | Upstream record | [source](https://github.com/triton-lang/triton/blob/c01b6774b1865984607d89d89d3a10833de92037/python/tutorials/gluon/10-tcgen05-copy.py#L116-L157) |
| Online softmax | Upstream record | [public distribution](https://github.com/gpu-verifier/sentryward/tree/421ff2c7d140341f64d2bc1f1edd045b65a7c403/examples/tilelang-online-softmax); exact generator URL unavailable |
| RMSNorm | Upstream record | [source](https://github.com/mlc-ai/TIRx-kernels/blob/01130e3bb1cf8a009fc1e7e6db2a860cd51df9ed/tirx_kernels/norm/rmsnorm.py); corroborating, not exact generator |

Four local CPU archives are original project runs. Eight upstream records are saved public outputs, not new local executions.
B200 trials and the one Meta diagnosis are separate evidence layers. Raw records retain timestamps and hashes; request IDs are diagnostic identifiers, not credentials.
Public manifests distinguish normalized PTX text from original upstream hashes. No model-quality win or GPU speedup is established.
