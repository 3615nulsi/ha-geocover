# Geocover (Decathlon) for Home Assistant

Unofficial Home Assistant integration for **Decathlon connected e-bikes** using the
*Decathlon Geocover* app (e.g. LD 920 E): GPS position, battery, range, odometer and last ride.

> ⚠️ **Unofficial project, not affiliated with, endorsed or supported by Decathlon or Conneqtech.**
> It uses the same cloud API as the mobile app, which may change or stop working at any time.
> Use at your own risk and in accordance with the service's terms.

*Version française plus bas.*

## Features
One device per bike, with:

| Entity | Description |
|---|---|
| `device_tracker` | GPS position (works with zones) |
| Battery, Range | bike battery (%) and estimated range (km) |
| Odometer | total distance (km) |
| Speed, Last position update | from the last GPS fix |
| Moving, Charging, Powered on, Ride in progress | binary sensors |
| Last ride, distance, duration, average speed, elevation gain | latest recorded ride |
| Last connection, GPS tracker battery | diagnostics |

Data is refreshed every **5 minutes** (the bike only reports its position when it moves or
connects, so polling faster would not help and would put unnecessary load on the service).

## Installation (HACS)
1. HACS → ⋮ → *Custom repositories* → add `https://github.com/3615nulsi/ha-geocover`, category *Integration*.
2. Install **Geocover (Decathlon)**, then restart Home Assistant.
3. *Settings → Devices & services → Add integration → Geocover (Decathlon)*.

## Sign-in
The Geocover app only accepts a sign-in redirect to itself, so the integration uses a small
copy/paste step:
1. Click the link shown by the setup dialog and sign in to your Decathlon account
   (e-mail + code, or Apple/Google).
2. You end up on a page saying **"Whoops! Looks like something went wrong"** — *this is expected*.
3. Copy the full address of that page (`https://login.ids.conneq.tech/redirect?code=…`) and paste it
   in the dialog. Do it quickly: the code expires after a short time.

Your tokens are stored only in your Home Assistant. If the session expires, Home Assistant asks you
to sign in again the same way.

## Privacy
The integration talks only to the Geocover servers (`*.conneq.tech`). Diagnostics downloads redact
tokens, positions, IMEI, e-mail and frame number.

---

## En français
Intégration **non officielle** pour les vélos électriques connectés Decathlon (application
*Decathlon Geocover*) : position GPS, batterie, autonomie, odomètre, dernier trajet.
**Sans lien avec Decathlon ni Conneqtech.**

**Connexion** : cliquez sur le lien de l'assistant, connectez-vous à votre compte Decathlon ; une page
« Whoops! Looks like something went wrong » s'affiche à la fin — c'est normal. Copiez l'adresse
complète de cette page (`https://login.ids.conneq.tech/redirect?code=…`) et collez-la dans
l'assistant, rapidement.

## Credits
Built on [`pygeocover`](https://github.com/3615nulsi/pygeocover). Licence: MIT.
