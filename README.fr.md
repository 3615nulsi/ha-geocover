# Geocover (Decathlon) pour Home Assistant

[![Release](https://img.shields.io/github/v/release/3615nulsi/ha-geocover)](https://github.com/3615nulsi/ha-geocover/releases)
[![HACS](https://img.shields.io/badge/HACS-custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/3615nulsi/ha-geocover/actions/workflows/validate.yml/badge.svg)](https://github.com/3615nulsi/ha-geocover/actions/workflows/validate.yml)

*[English version](README.md)*

Intégration Home Assistant **non officielle** pour les **vélos électriques connectés Decathlon**
utilisant l'application *Decathlon Geocover* : position GPS sur la carte, batterie, autonomie,
odomètre, charge et dernier trajet.

> ⚠️ **Projet non officiel, sans lien avec Decathlon ni Conneqtech, ni approuvé ou soutenu par eux.**
> Il utilise la même API cloud que l'application mobile, qui peut changer ou cesser de
> fonctionner à tout moment. À utiliser à vos risques et dans le respect des conditions du service.

## À quoi ça sert

- Voir le vélo sur la carte de Home Assistant, avec sa photo et son niveau de batterie.
- Être prévenu si le vélo bouge en votre absence, ou quand la charge est terminée.
- Recevoir un rappel de charge quand l'autonomie est faible la veille d'un jour travaillé.
- Garder un historique de la batterie, de l'autonomie et des trajets dans Home Assistant.

## Vélos compatibles

Les vélos électriques Decathlon équipés d'un traceur GPS qui apparaissent dans l'application
*Decathlon Geocover* (anciennement *Decathlon Mobility*). Testé avec un **Elops LD 920 E**.
Les autres vélos de la même application devraient fonctionner ; ouvrez une issue avec vos
diagnostics s'il manque quelque chose.

## Installation

Nécessite Home Assistant **2026.3.1** ou plus récent et [HACS](https://hacs.xyz).

[![Ouvrir ce dépôt dans HACS sur votre Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=3615nulsi&repository=ha-geocover&category=integration)

Ou à la main : HACS → ⋮ → *Dépôts personnalisés* → `https://github.com/3615nulsi/ha-geocover`,
catégorie *Intégration*. Ensuite :

1. Installez **Geocover (Decathlon)** dans HACS et redémarrez Home Assistant.
2. [![Ajouter l'intégration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=geocover)
   ou *Paramètres → Appareils et services → Ajouter une intégration → Geocover (Decathlon)*.
3. Connectez-vous (voir ci-dessous).

### Connexion

L'application Geocover n'accepte qu'une redirection vers elle-même ; l'assistant passe donc par
un copier-coller :

1. Cliquez sur le lien affiché et connectez-vous à votre compte Decathlon
   (e-mail + code, ou Apple/Google).
2. Vous arrivez sur une page **« Whoops! Looks like something went wrong »** : *c'est normal*.
3. Copiez l'adresse complète de cette page (`https://login.ids.conneq.tech/redirect?code=…`) et
   collez-la dans l'assistant, rapidement : le code expire vite.

Il n'y a aucun autre réglage. Si la session expire, Home Assistant affiche une notification et
vous demande de vous reconnecter de la même façon.

## Entités

Un appareil par vélo, portant le nom du vélo dans l'application.

| Entité | Type | Remarques |
|---|---|---|
| *(nom du vélo)* | Traceur | position GPS, compatible avec les zones ; photo et batterie du vélo sur la carte |
| Batterie | Capteur | % |
| Autonomie | Capteur | km |
| Odomètre | Capteur | km |
| Dernier trajet | Capteur | début du dernier trajet enregistré |
| Distance du dernier trajet | Capteur | km |
| Durée du dernier trajet | Capteur | min |
| En charge | Capteur binaire | |
| En mouvement | Capteur binaire | d'après le dernier point GPS |
| Allumé | Capteur binaire | |
| Trajet en cours | Capteur binaire | |
| Trajets enregistrés | Capteur | nombre de trajets dans l'application |
| Déclaré volé | Capteur binaire | selon la déclaration dans l'application |
| Verrou moteur | Capteur binaire | *activé* signifie déverrouillé |
| Trajet | Événement | déclenché à la fin de chaque trajet, avec son résumé |
| Trajets | Calendrier | chaque trajet enregistré, avec distance et durée |
| Vitesse | Capteur | *désactivé par défaut* ; 0 quand le vélo ne bouge pas |
| Dernière position | Capteur | *désactivé par défaut* |
| Vitesse moyenne du dernier trajet | Capteur | *désactivé par défaut* |
| Dénivelé positif du dernier trajet | Capteur | *désactivé par défaut* |
| Fin, dénivelé négatif, calories, CO₂ économisé du dernier trajet | Capteurs | *désactivés par défaut* |
| Dernière charge complète | Capteur | *désactivé par défaut* |
| Verrou de roue arrière | Capteur binaire | *désactivé par défaut*, absent sur certains vélos |
| Système du vélo | Capteur binaire | *diagnostic* ; *activé* quand le vélo signale un problème |
| Dernière connexion | Capteur | *diagnostic, désactivé par défaut* |
| Batterie du traceur GPS | Capteur | *diagnostic, désactivé par défaut* |

Les entités désactivées par défaut s'activent depuis la page de l'appareil.

Le traceur porte aussi les attributs `geofences` (les géorepères actifs définis dans
l'application Geocover) et `in_geofences` (ceux où se trouve le vélo).

### Événement de fin de trajet

L'entité événement **Trajet** déclenche `ride_finished` une fois par nouveau trajet, quand il est
terminé, avec `distance_km`, `duration_min`, `average_speed_kmh`, `elevation_gain_m`,
`elevation_loss_m`, `calories_kcal`, `co2_saved_g`, `start` et `end`.

### Calendrier des trajets

Le calendrier **Trajets** affiche chaque trajet enregistré (« 7.4 km · 24 min »), y compris ceux
d'avant l'installation de l'intégration. L'historique est lu sur les serveurs Geocover la
première fois qu'il est demandé, puis seuls les nouveaux trajets sont récupérés.

### Statistiques long terme

La distance parcourue et le nombre de trajets sont importés en statistiques long terme
(`geocover:bike_<id>_distance`, `geocover:bike_<id>_rides`), depuis le tout premier trajet.
Utilisez-les dans une carte *Graphique de statistiques*, par exemple la distance par semaine
ou par mois.

### Actions

| Action | Renvoie |
|---|---|
| `geocover.get_rides` | les trajets d'un vélo : les derniers (`limit`), ou ceux commencés entre `start` et `end` |
| `geocover.get_locations` | la trace GPS d'un vélo entre `start` et `end` (7 jours au plus) |

```yaml
action: geocover.get_locations
data:
  device_id: 0123456789abcdef0123456789abcdef
  start: "2026-11-23 06:00:00"
  end: "2026-11-23 09:00:00"
response_variable: trace
```

### Réparations

*Paramètres → Réparations* signale un vélo déclaré volé, une batterie de traceur GPS faible
(sous 20 %) ou un traceur qui ne s'est pas connecté depuis 3 jours.

## Mise à jour des données

La liste des vélos (position, batterie, odomètre) et leur état (charge, autonomie) sont lus à
un **rythme adaptatif** :

- **toutes les minutes** pendant un trajet (ou tant que le dernier point GPS dit que le vélo bouge) ;
- **toutes les 5 minutes** quand le vélo charge, est allumé ou a bougé dans les 3 dernières heures ;
- **toutes les 15 minutes** quand tous les vélos sont immobiles depuis plus de 3 heures.

Un trajet est ainsi suivi de près, et le service est ménagé le reste du temps. En contrepartie,
quand le vélo dort depuis des heures, un déplacement peut mettre jusqu'à 15 minutes à être vu.

La santé du traceur est relue toutes les heures ; le dernier trajet à
la fin d'un trajet, quand le vélo a bougé, ou toutes les heures. Le vélo ne remonte sa position
que lorsqu'il bouge ou se connecte : interroger plus souvent n'apporterait rien et chargerait
inutilement le service. Si une requête secondaire échoue, les dernières valeurs sont conservées.

Les vélos ajoutés au compte ou retirés apparaissent ou disparaissent d'eux-mêmes.

## Blueprints et tableau de bord

| Blueprint | Importer |
|---|---|
| Le vélo bouge alors que personne n'est à la maison | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fbike_moving_while_away.yaml) |
| Vélo chargé : débranchez-le | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fbike_charged.yaml) |
| Rappel de charge la veille d'un jour travaillé | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fcharge_reminder.yaml) |
| Résumé de chaque trajet | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2F3615nulsi%2Fha-geocover%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgeocover%2Fride_summary.yaml) |

Une vue de tableau de bord prête à l'emploi (batterie, autonomie, carte, dernier trajet,
distance par semaine, calendrier des trajets) se trouve dans
[`examples/dashboard.yaml`](examples/dashboard.yaml).

## Exemples d'automatisations

Envoyer le résumé de chaque trajet :

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
        {{ state_attr('event.mon_velo_trajet', 'duration_min') }} min

Prévenir si le vélo bouge alors que personne n'est à la maison :

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.mon_velo_en_mouvement
    to: "on"
conditions:
  - condition: state
    entity_id: zone.home
    state: "0"
actions:
  - action: notify.mobile_app_mon_telephone
    data:
      message: "Le vélo bouge !"
```

Prévenir quand la charge est terminée :

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.mon_velo_en_charge
    from: "on"
    to: "off"
conditions:
  - condition: numeric_state
    entity_id: sensor.mon_velo_batterie
    above: 95
actions:
  - action: notify.mobile_app_mon_telephone
    data:
      message: "Le vélo est chargé, vous pouvez le débrancher."
```

## Limites connues

- La position n'est jamais plus récente que le dernier signal du vélo (quand il bouge ou se
  connecte).
- Aucune commande (verrouillage, alarme) : l'intégration est en lecture seule.
- Un vélo partagé entre deux comptes configurés dans le même Home Assistant n'apparaît qu'une
  fois, sous le compte du propriétaire s'il est configuré.
- L'API Decathlon n'est pas documentée et peut changer sans préavis.

## Dépannage

- **« Adresse invalide ou code expiré »** : le code est à usage unique et expire vite. L'assistant
  génère un nouveau lien : reconnectez-vous avec celui-ci et collez aussitôt la nouvelle adresse.
- **La connexion ne se termine pas sur « Whoops! »** : copiez bien l'adresse de l'onglet ouvert par
  le lien, après la connexion, et non le lien lui-même.
- **Entités indisponibles** : les serveurs Geocover sont injoignables ; l'intégration réessaie
  à la mise à jour suivante. Les détails sont dans le journal.
- **Reconnexion demandée** : la session a été révoquée (par exemple après une déconnexion de tous
  les appareils dans l'application). Suivez la notification pour vous reconnecter.
- Pour ouvrir une issue, joignez les **diagnostics** (page de l'appareil → ⋮ →
  *Télécharger les diagnostics*) : positions, jetons, identifiants et textes inconnus y sont masqués.

## Suppression

1. *Paramètres → Appareils et services → Geocover (Decathlon) → ⋮ → Supprimer*.
2. Si vous le souhaitez, désinstallez-la de HACS et redémarrez Home Assistant.

## Confidentialité

L'intégration ne communique qu'avec les serveurs Geocover (`*.conneq.tech`). Vos jetons ne sont
stockés que dans votre Home Assistant.

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md). Traductions : anglais, français, allemand, espagnol,
italien, néerlandais et portugais ; les corrections par des locuteurs natifs sont bienvenues.

## Crédits

S'appuie sur [`pygeocover`](https://github.com/3615nulsi/pygeocover). Licence : MIT.
