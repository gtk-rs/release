# Release process

- Create a new branch for the release `$version` for `gir`, `gir-files`, `gtk-rs-core`, `gtk4-rs`
- Check that the `gir` and `gir-files` submodules are up to date
- Switch to using released versions of the dependencies
  - keep the git urls and add the `branch` and keep `path` for the local ones
- Ensure things are building properly
- Run `cargo publish`
- Create a new release from Github named `$version`
- Add the new `$version` to `.github/workflows/docs.yml` for the `main` branch
- Update `/latest/stable` link on `gh-pages`
  - `git clone $repo -b gh-pages --depth=1`
  - `cd $repo`
  - `unlink ./stable/latest/docs`
  - `cd ./stable/latest`
  - `ln -sf ../$version/docs ./docs`
- Squash the commits in `gh-pages` while you are at it
- Update versions in main to the next one
- 🎉
