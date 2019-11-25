#!/bin/bash

# Helper script to run PwnAdventure3 client with exploited game logic
# and for loading missing cryptographic libraries.
#
# Note, PwnAdventure3 client requires openssl1.0.0, which is unavaible on Ubuntu after 18.
# To run the client on a later version, extract the missing libraries from a VM and place
# them in openssl1.0.0/ next to the client binary.

PROJECT_ROOT=$(realpath "$(dirname $0)")
BIN_PATH="$PROJECT_ROOT/PwnAdventure3/PwnAdventure3/Binaries/Linux"

# Make sure all libraries can be loaded
missing_libs=(`ldd "$BIN_PATH/PwnAdventure3-Linux-Shipping" | grep "not found" | awk -F' ' '{print $1}'`)
if (( ${#missing_libs[@]} > 0 )); then
    >&2 echo "Missing ${missing_libs[@]}... checking $BIN_PATH/openssl1.0.0"
    if [ -d "$BIN_PATH/openssl1.0.0" ]; then
        for lib in "${missing_libs[@]}"; do
            if [ ! -f "$BIN_PATH/openssl1.0.0/$lib" ]; then
                >&2 echo "Could not find $lib. Exiting"
                exit 1
            fi
        done
        echo "Found missing libs"
        export LD_LIBRARY_PATH="$BIN_PATH/openssl1.0.0"
    else
        >&2 echo "Could not find libraries. Exiting"
        exit 1
    fi
fi

# Inject exploits
echo "Injecting exploited game logic..."
export LD_PRELOAD="$PROJECT_ROOT/tools/hackedLib/build/pwn3.so"

# Run it!
cd $BIN_PATH
echo "Starting the fun!"
./PwnAdventure3-Linux-Shipping