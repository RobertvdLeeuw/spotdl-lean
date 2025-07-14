{
  description = "Hello world flake using uv2nix";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        nixpkgs.follows = "nixpkgs";
      };
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        uv2nix.follows = "uv2nix";
        nixpkgs.follows = "nixpkgs";
      };
    };
  };
  outputs =
    {
    self,
    nixpkgs,
    uv2nix,
    pyproject-nix,
    pyproject-build-systems,
    ...
    }:
    let
      inherit (nixpkgs) lib;
      # Load a uv workspace from a workspace root.
      # Uv2nix treats all uv projects as workspace projects.
      workspace = uv2nix.lib.workspace.loadWorkspace {
        workspaceRoot = ./.;
        config.deps = "all";
      };  # Loading in pyproject and project data.

      # Create package overlay from workspace.
      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";  # Wheel is best, apparently.
      };

      # Extend generated overlay with build fixups, uv can only do so much on its own.
      pyprojectOverrides = final: prev: {
        numba = prev.numba.overrideAttrs (old: {
          buildInputs = (old.buildInputs or []) ++ [ pkgs.tbb_2022_0 ];
        });

        # Fix hatchling first
        hatchling = prev.hatchling.overrideAttrs (old: {
          nativeBuildInputs = (old.nativeBuildInputs or []) ++
            final.resolveBuildSystem {
              setuptools = [];
              wheel = [];
            };
        });

        # Fix editables package
        editables = prev.editables.overrideAttrs (old: {
          nativeBuildInputs = (old.nativeBuildInputs or []) ++
            final.resolveBuildSystem { setuptools = []; };
        });

        # # Fix spotdl-lean with all required build dependencies
        # spotdl-lean = prev.spotdl-lean.overrideAttrs (old: {
        #   nativeBuildInputs = (old.nativeBuildInputs or []) ++
        #     final.resolveBuildSystem {
        #       hatchling = [];
        #       editables = [];
        #       setuptools = [];  # Fallback
        #       wheel = [];
        #     };
        #   # Add system dependencies if needed
        #   buildInputs = (old.buildInputs or []) ++ [
        #     pkgs.ffmpeg  # spotdl often needs ffmpeg
        #   ];
        # });

        jaconv = prev.jaconv.overrideAttrs (old: {
          nativeBuildInputs = (old.nativeBuildInputs or []) ++
            final.resolveBuildSystem { setuptools = []; };
        });

        # Add other common problematic packages
        jukemirlib = prev.jukemirlib.overrideAttrs (old: {
          nativeBuildInputs = (old.nativeBuildInputs or []) ++
            final.resolveBuildSystem { setuptools = []; };
        });
      };

      # This example is only using x86_64-linux
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      python = pkgs.python312;

      # Construct package set
      pythonSet =
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
        (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            overlay
            pyprojectOverrides
          ]
        );
    in
      {
      # Nix build
      packages.x86_64-linux.default = pythonSet.mkVirtualEnv "venv" workspace.deps.default;

      apps.x86_64-linux = {
        default = {
          type = "app";
          program = "${self.packages.x86_64-linux.default}/bin/spotdl";
        };
      };

      devShells.x86_64-linux =
        let
          setup = {
            packages = [
              python
              pkgs.uv
              pkgs.libsndfile
              pkgs.postgresql_16
              pkgs.ffmpeg  # Add ffmpeg to shell
            ];
            env = {
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              unset PYTHONPATH
            '';
          };
        in {
          impure = pkgs.mkShell {
            packages = setup.packages;
            env = setup.env // {
              UV_PYTHON = python.interpreter;
            } // lib.optionalAttrs pkgs.stdenv.isLinux {
                LD_LIBRARY_PATH = "${lib.makeLibraryPath pkgs.pythonManylinuxPackages.manylinux1}";
              };
            shellHook = setup.shellHook;
          };

          default =
            let
              # Create an overlay enabling editable mode for LOCAL packages only
              editableOverlay = workspace.mkEditablePyprojectOverlay {
                root = "$REPO_ROOT";
                # Only enable editable for your actual local packages, not Git dependencies
                members = [ "music-embed" ];  # Your actual package name
              };

              editablePythonSet = pythonSet.overrideScope (
                lib.composeManyExtensions [
                  editableOverlay
                  # Only apply editable fixups to your local packages
                  (final: prev: {
                    music-embed = prev.music-embed.overrideAttrs (old: {
                      src = lib.fileset.toSource {
                        root = old.src;
                        fileset = lib.fileset.unions [
                          (old.src + "/pyproject.toml")
                          (old.src + "/README.md")
                          (lib.fileset.maybeMissing (old.src + "/src"))
                        ];
                      };
                      nativeBuildInputs =
                        old.nativeBuildInputs
                        ++ final.resolveBuildSystem {
                          setuptools = [];  # Your project uses setuptools
                          wheel = [];
                          editables = [];
                        };
                    });
                  })
                ]
              );

              virtualenv = editablePythonSet.mkVirtualEnv "music-embed-dev-env" workspace.deps.all;
            in
              pkgs.mkShell {
                packages = setup.packages;
                env = setup.env // {
                  UV_NO_SYNC = "1";
                  UV_PYTHON = "${virtualenv}/bin/python";
                };
                shellHook = setup.shellHook + ''
                  export REPO_ROOT=$(git rev-parse --show-toplevel)
                  export PATH="${virtualenv}/bin:$PATH"
                '';
              };
        };
    };
}
