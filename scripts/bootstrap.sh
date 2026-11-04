#!/bin/sh
set -eu
relay_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$relay_root"
relay_revision=421ff2c7d140341f64d2bc1f1edd045b65a7c403
if [ ! -d vendor/sentryward ]; then
    mkdir -p vendor/sentryward
    git -C vendor/sentryward init
    git -C vendor/sentryward remote add origin https://github.com/gpu-verifier/sentryward.git
    git -C vendor/sentryward fetch --depth 1 origin "$relay_revision"
    git -C vendor/sentryward checkout --detach FETCH_HEAD
fi
test "$(git -C vendor/sentryward rev-parse HEAD)" = "$relay_revision"
test -z "$(git -C vendor/sentryward status --porcelain --untracked-files=no)"
cmake -S vendor/sentryward -B .build/sentryward -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="${CMAKE_PREFIX_PATH:-/opt/homebrew}" \
    -DSENTRYWARD_BUILD_TESTS=OFF -DSENTRYWARD_BUILD_INTERNAL_TOOLS=OFF \
    -DSENTRYWARD_ENABLE_DEVELOPMENT_DIAGNOSTICS=OFF
cmake --build .build/sentryward --parallel 2
python3 -m warp_relay doctor
