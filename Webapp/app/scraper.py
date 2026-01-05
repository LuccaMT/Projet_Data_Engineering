import os
import subprocess

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
MONGO_DB = os.getenv('MONGO_DB', 'flashscore')


def scrape_upcoming_matches(target_date: str) -> tuple[bool, str]:
    try:
        cmd = [
            "docker", "exec", "flashscore-scrapy",
            "python", "/app/crawler/fetch_upcoming.py",
            "--date", target_date
        ]
        
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
        success = proc.returncode == 0
        
        if success:
            return True, f"Scraping OK pour {target_date}"
        else:
            return False, f"Erreur scraping: {proc.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return False, "Timeout scraping (>60s)"
    except Exception as e:
        return False, f"Erreur: {str(e)[:200]}"


def scrape_finished_matches(target_date: str = None, month: str = None) -> tuple[bool, str]:
    try:
        cmd = ["docker", "exec", "flashscore-scrapy", "python", "/app/crawler/fetch_finished.py"]
        
        if month:
            cmd.extend(["--month", month])
        elif target_date:
            cmd.extend(["--date", target_date])
        else:
            return False, "Aucune date ou mois spécifié"
        
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
        success = proc.returncode == 0
        
        if success:
            period = month or target_date
            return True, f"Scraping OK pour {period}"
        else:
            return False, f"Erreur scraping: {proc.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return False, "Timeout scraping (>120s)"
    except Exception as e:
        return False, f"Erreur: {str(e)[:200]}"
