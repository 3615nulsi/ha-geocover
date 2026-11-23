# 🚲 Geocover pour Home Assistant

[![Release](https://img.shields.io/github/v/release/3615nulsi/ha-geocover)](https://github.com/3615nulsi/ha-geocover/releases)
[![HACS](https://img.shields.io/badge/HACS-custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/3615nulsi/ha-geocover/actions/workflows/validate.yml/badge.svg)](https://github.com/3615nulsi/ha-geocover/actions/workflows/validate.yml)

🇬🇧 *[English version](README.md)*

Votre vélo électrique Decathlon, dans Home Assistant.

Si votre vélo apparaît dans l'application **Decathlon Geocover**, cette intégration le ramène à la
maison : où il est, ce qu'il reste de batterie, jusqu'où vous pouvez encore aller, et tous les
trajets que vous avez faits avec.

> [!WARNING]
> C'est un projet personnel, ni conçu, ni approuvé, ni soutenu par Decathlon ou Conneqtech.
> Il utilise les mêmes serveurs que l'application, qui peuvent changer sans prévenir.

## ✨ Ce que ça apporte

- 🗺️ **Le vélo sur votre carte**, avec sa photo et son niveau de batterie
- 🔋 **Batterie, autonomie et charge** : savoir quand brancher, et quand débrancher
- 🏁 **Une notification à la fin de chaque trajet**, avec distance, durée et dénivelé
- 📅 **Un calendrier de tous vos trajets**, même ceux d'avant l'installation
- 📈 **Des statistiques long terme** : kilomètres par semaine, par mois, par an
- 🚨 **Des alertes** si le vélo bouge en votre absence, s'il est déclaré volé ou si son traceur se décharge
- 🧩 **Des blueprints prêts à l'emploi** et un tableau de bord à copier

## 📦 Installation

Il vous faut Home Assistant **2026.3.1** ou plus récent, et [HACS](https://hacs.xyz).

[![Ouvrir ce dépôt dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=3615nulsi&repository=ha-geocover&category=integration)

1. Cliquez sur le bouton ci-dessus (ou ajoutez `https://github.com/3615nulsi/ha-geocover` comme
   dépôt personnalisé dans HACS, catégorie *Intégration*).
2. Téléchargez **Geocover (Decathlon)** et redémarrez Home Assistant.
3. [![Ajouter l'intégration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=geocover)

### 🔑 Connexion

Decathlon ne laisse que sa propre application recevoir la connexion. Il y a donc un petit
copier-coller :

1. Ouvrez le lien affiché par l'assistant et connectez-vous comme d'habitude (code par e-mail,
   Apple ou Google).
2. Vous arrivez sur une page **« Whoops! Looks like something went wrong »**. C'est normal,
   c'est précisément la page qu'il nous faut.
3. Copiez l'adresse de cette page et collez-la dans l'assistant. Faites vite : le code expire
   au bout d'une minute ou deux.

C'est tout, il n'y a rien d'autre à régler. Si Decathlon met fin à la session un jour, Home
Assistant vous demandera de vous reconnecter de la même façon.

## 🚴 Vélos compatibles

Tout vélo équipé d'un traceur GPS qui apparaît dans l'application *Decathlon Geocover*
(anciennement *Decathlon Mobility*). L'intégration tourne tous les jours sur un **Elops LD 920 E**.
Un autre modèle ? [Dites-moi si ça marche](https://github.com/3615nulsi/ha-geocover/issues/new?template=new_bike.yml).

## 🧭 Ce qui apparaît dans Home Assistant

Un appareil par vélo, nommé comme dans l'application. Les entités du quotidien sont activées
d'office ; les plus techniques sont créées désactivées, et s'activent depuis la page de l'appareil.

<details>
<summary><b>Voir toutes les entités</b></summary>

| Entité | Ce qu'elle indique |
|---|---|
| 📍 *(nom de votre vélo)* | Position sur la carte, avec photo et batterie. Compatible avec les zones |
| 🔋 Batterie | Niveau de batterie (%) |
| 🛣️ Autonomie | Autonomie estimée (km) |
| 🔢 Odomètre | Distance totale (km) |
| 🔌 En charge | Activé quand le vélo est branché |
| 🏃 En mouvement | D'après la dernière position GPS |
| ⚡ Allumé | Vélo allumé |
| 🚴 Trajet en cours | Un trajet est en cours d'enregistrement |
| 🔒 Verrou moteur | *Activé* veut dire déverrouillé |
| 🚨 Déclaré volé | Selon la déclaration dans l'application |
| 🏁 Dernier trajet, distance, durée | Le dernier trajet enregistré |
| 🧮 Trajets enregistrés | Nombre de trajets connus de l'application |
| 🎉 Trajet *(événement)* | Se déclenche une fois à la fin de chaque trajet |
| 📅 Trajets *(calendrier)* | Tous les trajets, avec distance et durée |

Désactivées par défaut : vitesse, dernière position, vitesse moyenne, dénivelés positif et négatif,
calories et CO₂ économisé au dernier trajet, dernière charge complète, verrou de roue arrière,
et trois diagnostics (dernière connexion, batterie du traceur GPS, système du vélo).

Le traceur liste aussi les géorepères créés dans l'application (`geofences`) et ceux où se
trouve le vélo en ce moment (`in_geofences`).

</details>

## 🔄 À quel rythme ça se met à jour

L'intégration s'adapte à ce que fait le vélo :

| Le vélo… | Fréquence |
|---|---|
| 🚴 roule | chaque minute |
| 🔌 charge, est allumé ou a bougé dans les 3 dernières heures | toutes les 5 minutes |
| 😴 est garé depuis plus de 3 heures | toutes les 15 minutes |

Les trajets sont enregistrés par le vélo lui-même : rien n'est perdu quand Home Assistant
interroge moins souvent. Distances, durées et trace GPS sont toujours complètes. Seule la
position en direct attend : après un long repos, Home Assistant peut mettre jusqu'à
15 minutes à voir que le vélo est parti.

## 🎉 Automatisations

### Blueprints

Un clic pour importer, puis choisissez votre vélo et votre téléphone :

| | |
|---|---|
| 🚨 Le vélo bouge alors que personne n'est à la maison | [![Importer](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fbike_moving_while_away.yaml) |
| 🔋 Batterie pleine, on peut débrancher | [![Importer](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fbike_charged.yaml) |
| 🔌 Rappel de charge la veille d'un jour travaillé | [![Importer](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fcharge_reminder.yaml) |
| 🏁 Résumé du trajet sur votre téléphone | [![Importer](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fride_summary.yaml) |

Les blueprints envoient leurs notifications en anglais ; vous pouvez changer les textes après
l'import.

### Tableau de bord

Une vue complète (batterie, autonomie, carte, dernier trajet, kilomètres par semaine, calendrier
des trajets) vous attend dans [`examples/dashboard.yaml`](examples/dashboard.yaml). Remplacez
`my_bike` par le nom de votre vélo et collez-la.

<details>
<summary><b>Écrire vos propres automatisations</b></summary>

L'événement **Trajet** transporte `distance_km`, `duration_min`, `average_speed_kmh`,
`elevation_gain_m`, `elevation_loss_m`, `calories_kcal`, `co2_saved_g`, `start` et `end` :

```yaml
triggers:
  - trigger: state
    entity_id: event.mon_velo_trajet
    not_from: unavailable
conditions:
  - condition: state
    entity_id: event.mon_velo_trajet
    attribute: event_type
    state: ride_finished
actions:
  - action: notify.mobile_app_mon_telephone
    data:
      message: >-
        {{ state_attr('event.mon_velo_trajet', 'distance_km') }} km en
        {{ state_attr('event.mon_velo_trajet', 'duration_min') }} min 🚴
```

Deux actions renvoient des données utilisables dans vos scripts :

- `geocover.get_rides` : les derniers trajets, ou ceux d'une période
- `geocover.get_locations` : la trace GPS entre deux dates (7 jours au plus)

```yaml
action: geocover.get_locations
data:
  device_id: 0123456789abcdef0123456789abcdef
  start: "2026-11-23 06:00:00"
  end: "2026-11-23 09:00:00"
response_variable: trace
```

Les statistiques long terme s'appellent `geocover:bike_<id>_distance` et
`geocover:bike_<id>_rides`. Glissez-les dans une carte *Graphique de statistiques*.

</details>

## 🛠️ Réparations

Home Assistant vous prévient dans *Paramètres → Réparations* quand :

- 🚨 le vélo est déclaré volé dans l'application
- 🪫 la batterie du traceur GPS passe sous 20 %
- 📡 le traceur n'a pas donné signe de vie depuis 3 jours

## 🆘 Dépannage

<details>
<summary><b>« Adresse invalide ou code expiré »</b></summary>

Le code ne sert qu'une fois et ne vit qu'une minute ou deux. L'assistant vous a déjà préparé un
nouveau lien : connectez-vous avec, puis collez la nouvelle adresse aussitôt.
</details>

<details>
<summary><b>Je ne vois jamais la page « Whoops! »</b></summary>

Copiez bien l'adresse de l'onglet ouvert par le lien, *après* la connexion, et non le lien
lui-même. Sur un téléphone où l'application Geocover est installée, c'est elle qui peut
intercepter la connexion : faites-le plutôt depuis un ordinateur.
</details>

<details>
<summary><b>Tout est « indisponible »</b></summary>

Les serveurs Geocover n'ont pas répondu. L'intégration réessaie à la mise à jour suivante. Les
détails sont dans *Paramètres → Système → Journaux*.
</details>

<details>
<summary><b>Home Assistant me demande de me reconnecter</b></summary>

La session a été fermée côté Decathlon, par exemple après « se déconnecter de partout » dans
l'application. Suivez la notification et reconnectez-vous comme la première fois.
</details>

Toujours coincé ? [Ouvrez une issue](https://github.com/3615nulsi/ha-geocover/issues/new?template=bug_report.yml)
avec les **diagnostics** (page de l'appareil → ⋮ → *Télécharger les diagnostics*). Positions,
jetons et données personnelles en sont retirés.

## ⚠️ Bon à savoir

- 📡 La position n'est jamais plus fraîche que le dernier signal du vélo.
- 👀 Lecture seule : l'intégration ne peut ni verrouiller le vélo ni déclencher l'alarme.
- 👥 Un vélo partagé entre deux comptes configurés dans le même Home Assistant n'apparaît qu'une fois.
- 🔧 L'API de Decathlon n'est pas publique et peut changer. Si quelque chose casse, ouvrez une issue.

## 🗑️ Désinstallation

*Paramètres → Appareils et services → Geocover (Decathlon) → ⋮ → Supprimer*, puis retirez-la de
HACS si vous le souhaitez.

## 🔒 Confidentialité

L'intégration ne parle qu'aux serveurs Geocover (`*.conneq.tech`). Votre connexion reste dans
votre Home Assistant.

## 🤝 Contribuer

Signalements de bugs, retours sur d'autres modèles et pull requests sont les bienvenus, voir
[CONTRIBUTING.md](CONTRIBUTING.md). L'interface existe en anglais, français, allemand, espagnol,
italien, néerlandais et portugais. Si vous êtes natif et qu'une tournure sonne faux, corrigez-la !

S'appuie sur [pygeocover](https://github.com/3615nulsi/pygeocover). Licence MIT.
