"""
Utilitaires de traitement de texte pour le dashboard Flashscore.

Ce module contient les fonctions de normalisation et de parsing de texte
utilisées dans l'interface web.
"""

# Standard library
import unicodedata
from typing import Tuple


def normalize_unicode_label(text: str) -> str:
    """
    Normalise une chaîne de caractères en supprimant les accents et caractères spéciaux.
    
    Args:
        text (str): Texte à normaliser.
    
    Returns:
        str: Texte normalisé en ASCII sans accents.
        
    Example:
        >>> normalize_unicode_label("Première Division")
        'Premiere Division'
        >>> normalize_unicode_label("São Paulo")
        'Sao Paulo'
    """
    if not text:
        return ""
    
    # Décompose les caractères Unicode (sépare les accents)
    nfkd_form = unicodedata.normalize('NFKD', text)
    
    # Filtre les caractères non-ASCII
    return ''.join([char for char in nfkd_form if not unicodedata.combining(char)])


def parse_league_country(league_full_name: str) -> Tuple[str, str]:
    """
    Parse un nom de ligue au format "PAYS: Nom de la ligue" pour extraire pays et ligue.
    
    Args:
        league_full_name (str): Nom complet de la ligue (format: "PAYS: Ligue").
    
    Returns:
        Tuple[str, str]: Tuple (pays, nom_ligue).
                        Si le format n'est pas reconnu, retourne ("", league_full_name).
    
    Example:
        >>> parse_league_country("FRANCE: Ligue 1")
        ('FRANCE', 'Ligue 1')
        >>> parse_league_country("SPAIN: LaLiga")
        ('SPAIN', 'LaLiga')
        >>> parse_league_country("Champions League")
        ('', 'Champions League')
    """
    if not league_full_name:
        return "", ""

    if ":" not in league_full_name:
        return "", league_full_name

    country, league_name = league_full_name.split(":", 1)
    country = country.strip()
    league_name = league_name.strip()
    
    return country, league_name
