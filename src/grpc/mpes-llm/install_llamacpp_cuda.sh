#!/bin/bash

## Use this if you got the error "CudaToolkit not found" while compiling
# CMAKE_ARGS="-DGGML_CUDA=ON -DCUDAToolkit_INCLUDE_DIR=/usr/local/cuda/include -DCUDAToolkit_ROOT=/usr/local/cuda -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc" FORCE_CMAKE=1 pip install llama-cpp-python --no-cache-dir

## Use this if you got the error "Error: unsupported instruction `vpdpbusd'" while compiling
# CMAKE_ARGS="-DGGML_CUDA=ON -DCMAKE_C_FLAGS='-mno-avx512vnni -mno-avxvnni' -DCMAKE_CXX_FLAGS='-mno-avx512vnni -mno-avxvnni' -DCMAKE_CUDA_ARCHITECTURES=89" FORCE_CMAKE=1 pip install llama-cpp-python --force-reinstall --verbose
