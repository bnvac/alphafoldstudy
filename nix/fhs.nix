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

  # Commands arrive through AFS_RUN, not through nix-shell's --run.
  #
  # buildFHSEnv's .env works by way of a shell hook that execs straight into
  # the sandbox. nix-shell appends its --run command after that hook, so the
  # exec means --run is never reached: the sandbox starts a plain interactive
  # bash, which sees EOF on non-tty stdin and exits 0. A setup script driven
  # that way reports success while doing nothing at all, with no venv built and
  # no error printed. That silent no-op is worse than a failure, so the command
  # is passed in through the environment instead.
  #
  # AFS_RUN is unset before the command runs, so a nested shell started from
  # inside it does not run the command a second time. With AFS_RUN unset the
  # behaviour is an interactive shell, exactly as the documentation describes.
  runScript = pkgs.writeShellScript "alphafold-study-run" ''
    if [ -n "''${AFS_RUN:-}" ]; then
      command_to_run="$AFS_RUN"
      unset AFS_RUN
      exec bash -c "$command_to_run"
    fi
    exec bash
  '';
}).env
