#!/usr/bin/env bash

echo "[hiddenAI] Installing CLI..."

# create user bin folder if not exists
mkdir -p ~/.local/bin

# link command globally (no sudo needed)
ln -sf "$(pwd)/hiddenAI" ~/.local/bin/hiddenAI

echo "[hiddenAI] Done!"
echo "Restart terminal or run:"
echo "export PATH=\$HOME/.local/bin:\$PATH"
