"""Constantes de l'intégration Geocover."""
from datetime import timedelta
import logging

DOMAIN = "geocover"
LOGGER = logging.getLogger(__package__)

CONF_TOKENS = "tokens"
CONF_REDIRECT_URL = "redirect_url"

# Le vélo ne remonte sa position que lorsqu'il bouge ou se connecte : inutile (et mal vu
# par l'éditeur, cf. affaire Haier hOn) d'interroger plus souvent.
UPDATE_INTERVAL = timedelta(minutes=5)
