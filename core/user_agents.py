import random
from .config_loader import ConfigLoader

class UserAgentManager:
    _user_agents = []

    @classmethod
    def get_random_user_agent(cls) -> str:
        if not cls._user_agents:
            config = ConfigLoader.load()
            # Access safely
            scrapers = config.get('scrapers', {})
            default_scraper = scrapers.get('default', {})
            cls._user_agents = default_scraper.get('user_agents', [])
            
            # Fallback if config is empty
            if not cls._user_agents:
                cls._user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                ]
        
        return random.choice(cls._user_agents)
