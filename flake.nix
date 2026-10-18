{
  description = "Agent Self-Help development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
  };

  outputs =
    { nixpkgs, ... }:
    let
      supportedSystems = [
        "aarch64-darwin"
        "x86_64-linux"
        "aarch64-linux"
      ];

      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.actionlint
              pkgs.commitlint
              pkgs.deadnix
              pkgs.git
              pkgs.markdownlint-cli
              pkgs.marksman
              pkgs.nil
              pkgs.nixfmt
              pkgs.statix
              pkgs.yamllint
              pkgs.yaml-language-server
            ];

            shellHook = ''
              echo "Agent Self-Help development environment loaded"
            '';
          };
        }
      );
    };
}
