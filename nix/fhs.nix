# An FHS sandbox for running this project on NixOS.
#
# The problem this solves: NixOS has no /usr/lib and no /lib64/ld-linux, so a
# prebuilt Python wheel downloaded from PyPI cannot start. The wheel is fine,
# but its interpreter path points at a loader that does not exist on this
# system, and the failure surfaces as a confusing "No such file or directory"
# for a file that is plainly there. numpy, scipy, matplotlib and torch are all
# distributed this way, so a plain venv full of pip installs does not work.
#
# buildFHSEnv puts a conventional Linux filesystem layout in place inside a
# namespace, so those wheels find the loader and the shared libraries they were
# built against. Nothing is installed system-wide and no root access is needed.
#
# Enter it with:  nix-shell nix/fhs.nix
# though setup_nixos.sh and run_nixos.sh do that for you.

{ pkgs ? import <nixpkgs> { } }:

let
  # Renamed in nixpkgs 23.11; accept either spelling so this works on older
  # channels too.
  mkFHS = pkgs.buildFHSEnv or pkgs.buildFHSUserEnv;
in
(mkFHS {
  name = "alphafold-study-fhs";

  targetPkgs = p: with p; [
    python311
    python311Packages.pip
    python311Packages.virtualenv

    # Present so pip can compile from source if a wheel is ever unavailable
    # for the running Python version.
    gcc
    gnumake
    binutils
    pkg-config

    # The shared libraries manylinux wheels expect to find in an FHS layout.
    stdenv.cc.cc.lib
    zlib
    openssl
    bzip2
    xz
    libffi
    ncurses
    readline
    sqlite

    # matplotlib's font and image handling.
    freetype
    libpng

    # The study downloads every structure over HTTPS.
    curl
    cacert
    git
    which
    coreutils
  ];

  # Made available as both 32- and 64-bit, which is what wheels link against.
  multiPkgs = p: with p; [ zlib stdenv.cc.cc.lib ];

  profile = ''
    # Without these, requests inside the sandbox cannot verify certificates.
    export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
    export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    # Nothing here uses a GPU, and torch probing for one is slow and noisy.
    export CUDA_VISIBLE_DEVICES=""
  '';

  runScript = "bash";
}).env
