# Signing the releases

Three separate things get called signing, they cost different amounts, and they
buy different things. The pipeline is wired for all three and uses whichever
credentials exist, so nothing here has to be done all at once — and a build
with no credentials at all still produces installers, which is what a fork
needs.

| | Cost | What it buys | Status |
|---|---|---|---|
| GPG over `SHA256SUMS` | a key, so nothing | Anyone can prove the download is what was built | Wired, tested, needs a key |
| Windows Authenticode | a certificate, yearly | Stops SmartScreen calling the installer unrecognised | Wired, untested, needs a certificate |
| Apple Developer ID + notarization | $99/year at the time of writing | Stops Gatekeeper refusing to open the app | Wired, untested, needs an account |

The second and third are the ones users notice. The first is the one that lets
somebody who already trusts the project check they got the right bytes, and
it is the only one that covers the command-line archives as well as the
installers.

## What each signature does not do

A code signature says who built something. It does not say the thing is
correct, or safe, or that the numbers it produces mean anything. The reason to
read [VALIDATION.md](VALIDATION.md) does not go away because the installer
stopped warning.

Nor does any of this authenticate the model weights. Those are verified by the
SHA-256 in each head's metadata, which `opendna models` checks, and are
published separately on Hugging Face. A signed installer containing no weights
tells you nothing about the weights you later download.

## GPG over the checksums

The release workflow writes a `SHA256SUMS` naming every artefact, and
`scripts/sign-release.sh` signs it. One signature, every file on every
platform.

Generate a key for the purpose, rather than reusing a personal one:

```bash
gpg --quick-generate-key "OpenDNA Release Signing <releases@example.org>" default sign 2y
```

Then export the public half to `docs/signing-key.asc`, commit it, and put the
fingerprint in this file so there is a second place to check it against:

```bash
gpg --armor --export <fingerprint> > docs/signing-key.asc
```

Put the private half in the `GPG_SIGNING_KEY` repository secret, and its
passphrase in `GPG_PASSPHRASE`:

```bash
gpg --armor --export-secret-keys <fingerprint>
```

The script imports it into a throwaway keyring, signs, verifies its own output,
and deletes the keyring. If `GPG_SIGNING_KEY` is unset it exits 3 and says
nothing was signed, which the workflow treats as "this build was not meant to
be signed" rather than as a failure.

**Fingerprint of the signing key:** not yet generated. Fill this in when it is,
because a public key committed next to the thing it signs proves nothing on its
own — the fingerprint has to be checkable somewhere else too, and a reader
comparing this line against the key file is at least a second place.

Anybody can verify a release:

```bash
gpg --import docs/signing-key.asc
gpg --verify SHA256SUMS.asc SHA256SUMS
sha256sum --check --ignore-missing SHA256SUMS
```

Or, from a checkout, `scripts/sign-release.sh --verify <dir>`, which does both
and fails if either does. A good signature over tampered checksums, or good
checksums with no signature, both fail.

## Windows

The build merges `app/desktop/tauri.signing.conf.json` only when a Windows
credential is present, which points Tauri at `scripts/sign-windows.ps1`.

**The awkward part is where the private key lives.** Since June 2023 a new
publicly-trusted code-signing certificate must keep its private key on
certified hardware, so the old approach — a `.pfx` file in a secret — is not
available for a new certificate. In practice that leaves two options:

- **A cloud signing service.** Azure Trusted Signing, SSL.com eSigner, DigiCert
  KeyLocker and others hold the key and sign on request, which is what works in
  CI. Set `WINDOWS_SIGN_COMMAND` to that vendor's command with `{}` where the
  file path goes. For example, with
  [`trusted-signing-cli`](https://crates.io/crates/trusted-signing-cli)
  installed on the runner:

  ```text
  trusted-signing-cli -e https://eus.codesigning.azure.net -a <account> -c <profile> {}
  ```

  The flags belong to the vendor's tool and change with it, which is why this
  is a template rather than something baked into the script.

- **A hardware token in front of a person.** Put the certificate in the machine
  store and set `WINDOWS_CERT_THUMBPRINT` to its SHA-1 thumbprint; the script
  then calls `signtool.exe` from the Windows SDK. This cannot work on a hosted
  runner, so it means building releases on a machine with the token plugged in.

Either way the script timestamps with `http://timestamp.digicert.com` unless
`WINDOWS_TIMESTAMP_URL` says otherwise, so signatures outlive the certificate.

With neither variable set the script fails loudly. It is only reached when the
overlay was merged, and the overlay is only merged when the workflow saw a
credential, so reaching it without one means the two disagree — which is worth
stopping for rather than quietly shipping unsigned binaries from a build that
announced it was signing.

## macOS

No configuration at all: Tauri signs when `APPLE_SIGNING_IDENTITY` is set and
notarizes when `APPLE_ID`, `APPLE_PASSWORD` and `APPLE_TEAM_ID` are. The
workflow creates a keychain of its own for the certificate and lets it die with
the runner.

Secrets:

| | |
|---|---|
| `APPLE_CERTIFICATE` | the Developer ID Application `.p12`, base64 |
| `APPLE_CERTIFICATE_PASSWORD` | its password |
| `APPLE_SIGNING_IDENTITY` | e.g. `Developer ID Application: Name (TEAMID)` |
| `APPLE_ID` | the Apple ID used for notarization |
| `APPLE_PASSWORD` | an app-specific password, not the account password |
| `APPLE_TEAM_ID` | the ten-character team id |

`APPLE_PASSWORD` must be an app-specific password generated at
appleid.apple.com. The account password will not work and should not be put in
a repository secret.

Notarization uploads the build to Apple and waits, which adds minutes to a job
that already takes twenty-four.

## Linux

There is no equivalent of Authenticode or notarization: no desktop Linux
checks a signature before running an AppImage, a `.deb` or an `.rpm` from a
download. Signing the checksums is the whole of what is useful here.

Distribution-level signing — a `.deb` in an apt repository with a `Release`
file signed by the archive key — would be real, and would mean running an
archive. That is not a signature on the artefacts; it is a different way of
shipping them.

## What is verified, and what is not

**Tested:** `scripts/sign-release.sh`, through every path. Signing produces a
signature that verifies; a tampered artefact fails the checksum while the
signature still passes, which is the correct split of responsibilities; a
tampered `SHA256SUMS` fails the signature; a missing signature, a missing
public key and an unset key each exit with their own status. The CI
`signing` job does the same round trip on every commit with a key it generates
itself, so the script cannot rot unnoticed.

**Not tested:** everything needing a certificate. The Windows script has never
signed a file, the Apple keychain import has never run, and no notarization has
been attempted. The flags in `sign-windows.ps1`'s `signtool` path come from the
documentation rather than from a run. The first real certificate will find
whatever is wrong with all of it, and that is worth expecting rather than being
surprised by.

**Also not addressed:** nothing here signs a git tag or a commit. Tags are
annotated and unsigned. `git tag -s` would need the same key and is a separate
decision, because it changes what a maintainer needs on their own machine
rather than what CI needs in a secret.
