# Release process

Since gtk-rs has multiple crates which have inter-dependencies, it's a bit painful to make a new release. So here are the multiple steps:

 * Get the current version for all crates (all crates in one repository should all have the same!).
 * Replace git dependencies with crates.io ones.
 * Push those changes to a branch with `MAJOR.MEDIUM` name.
 * Push tags.
 * Write a blog post (add the file into `_posts` folder in `gtk-rs.github.io` repository) announcing the new release.
 * Publish crates.
 * Update dev branch crates' version.

Note that the github token is used for two things:

 1. Gathering the merged pull requests.
 2. Opening pull requests (for the version updates).

## Using this tool

I don't recommend it if you're not a member of the `gtk-rs` organization but just in case:

```bash
python3 src/release.py -m MEDIUM -t [Your github token here]
```
