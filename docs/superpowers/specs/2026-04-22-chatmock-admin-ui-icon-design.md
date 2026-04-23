# ChatMock Admin UI Install Icon Design

## Status

Proposed

## Date

2026-04-22

## Goal

Set the provided bird icon as the install/home-screen icon for the ChatMock admin UI only, covering:

- iOS Add to Home Screen
- Android Add to Home Screen / install surfaces
- Desktop install surfaces that honor the web app manifest

## Scope

This applies only to the browser admin UI served under `/admin/ui`.

It does not change the root ChatMock site branding or favicon behavior outside the admin UI.

## Current State

The admin UI currently has:

- no manifest
- no dedicated app icon assets
- no Apple touch icon
- no install metadata for Android/Desktop

## Design

Add a small installable-web-app asset set under the admin UI build surface.

### Source Asset

Use the uploaded PNG as the canonical source image.

### Generated Outputs

Generate and store install icon assets under an admin-UI-owned public path, for example:

- `ui/admin/public/icons/apple-touch-icon.png`
- `ui/admin/public/icons/icon-192.png`
- `ui/admin/public/icons/icon-512.png`
- `ui/admin/public/icons/icon-maskable-512.png`
- optional favicon PNG/ICO derived from the same source

### Manifest

Add `ui/admin/public/manifest.webmanifest` with:

- name: `ChatMock Admin`
- short_name: `ChatMock`
- start_url: `/admin/ui/`
- scope: `/admin/ui/`
- display: `standalone`
- background/theme colors matching the current dark admin shell
- icon entries for standard and maskable installs

### HTML Metadata

Update the admin UI HTML shell to include:

- manifest link
- apple touch icon
- theme-color
- mobile-web-app capable metadata as needed for iOS/WebKit

### Build/Serve Behavior

Keep this compatible with the existing Vite + Flask setup:

- assets should be emitted into the built admin UI output
- manifest and icons should resolve correctly when served from `/admin/ui/`
- no root-site manifest or favicon changes

## Constraints

- Admin UI only
- Reuse the provided image without redesigning it
- Keep the change lightweight: no service worker or broader PWA rollout
- Ensure asset URLs work with the `/admin/ui/` base path

## Success Criteria

- iOS home-screen add for `/admin/ui` uses the new icon
- Android/Desktop install surfaces for `/admin/ui` use the new icon set
- The built admin UI serves the manifest and icon files without path errors
- No changes leak into non-admin ChatMock routes
