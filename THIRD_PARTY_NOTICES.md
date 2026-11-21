# Third-party notices

## VulnCastle

Source: https://github.com/0x6d61/vulncastle

The prototype is adapted from VulnCastle. Its original README is preserved in
prototype/UPSTREAM.md, and its original application/service source remains under
prototype/lab. Paper Vianden changes packaging, lifecycle, access, limits and
logging. This repository is a separate project rather than an upstream fork.

VulnCastle declares MIT in its README. No separate licence text or copyright
notice was present in the inspected upstream tree. We retain that declaration
and attribution without presenting the imported code as original Paper Vianden
authorship. The root licence does not replace that upstream declaration or
assert authorship of the imported applications.

## Ethical Hacking Docker Labs

Source: https://github.com/michael-borck/ethical-hacking-docker-labs

Copyright (c) 2025 Michael Borck. MIT licence. The pinned source is retained as a
Git submodule under upstream/ethical-hacking-docker-labs, including its original
LICENSE file. Preserve that licence and attribution when importing files.

## Runtime and service images

Sysbox, Docker and individual service images retain their respective licences.
The root MIT licence applies to original Paper Vianden work, not to a relicensing
of bundled or referenced third-party software. Keep their notices and applicable
distribution obligations when preparing release artifacts.

## FUSE mount helper

The pinned Debian fuse3 package supplies fusermount3 for private runtime use.
Its complete copyright/licence notice is preserved beside the extracted helper.
The helper is GPL-2.0-or-later; corresponding source is available at
https://sources.debian.org/src/fuse3/3.14.0-4/. No changes are made to it.

## Suricata IDS

The offline library includes the unmodified Suricata 8.0.8 image from
[jasonish/docker-suricata](https://github.com/jasonish/docker-suricata), pinned by
digest in `runtime/image-sources.json`. Suricata is GPL-2.0; retain the image's
notices. Corresponding upstream source is available from the
[OISF 8.0.8 release](https://github.com/OISF/suricata/releases/tag/suricata-8.0.8)
and the image build repository. Original lab rules and wrappers are in `runtime/`.
