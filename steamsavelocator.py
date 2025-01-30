import os
import re
import sys
import json
import winreg
import unicodedata
import requests
import subprocess
from pathlib import Path
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def set_console_title(title):
    """Set the console window title using the `title` command"""
    if os.name == 'nt':  # Check if running on Windows
        subprocess.run(f"title {title}", shell=True)

# Configuration
STEAM_CLOUD_DIRS = ['remote', 'storage']
COMMON_SAVE_DIRS = ['saves', 'save', 'savegames', 'savedata', 'game', 'games']
REGISTRY_KEYS = [
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
]

def get_steam_game_info(app_id):
    """Get detailed game info from Steam API with fallback and better error handling"""
    try:
        response = requests.get(
            f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us&l=english",
            headers={
                'Accept-Language': 'en-US',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout=10
        )
        data = response.json().get(str(app_id), {})
        if data.get('success'):
            name = data['data'].get('name', f"AppID {app_id}")
            developers = data['data'].get('developers', [])
            # Remove any "(TM)", "®", etc. from the game name
            name = re.sub(r'\s*[™®©]\s*', '', name)
            return name, developers
        return f"AppID {app_id}", []
    except Exception as e:
        print(f"\n{Fore.YELLOW}⚠️ Warning: Couldn't fetch game info from Steam: {str(e)}{Fore.RESET}")
        return f"AppID {app_id}", []

def normalize_text(text):
    """Advanced normalization for multilingual support"""
    text = unicodedata.normalize('NFKD', str(text))
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    return text.strip().lower()

def find_steam_cloud_saves(app_id):
    """Find all possible Steam Cloud locations"""
    cloud_paths = []
    try:
        steam_path = winreg.QueryValueEx(
            winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
            "SteamPath"
        )[0]
        userdata = Path(steam_path) / 'userdata'
        
        if userdata.exists():
            for user_id in userdata.iterdir():
                for cloud_dir in STEAM_CLOUD_DIRS:
                    cloud_path = user_id / str(app_id) / cloud_dir
                    if cloud_path.exists():
                        cloud_paths.append(str(cloud_path))
    except Exception:
        pass
    return cloud_paths

def search_registry_for_paths(search_term):
    """Deep registry search for save locations"""
    found_paths = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, '', 0, winreg.KEY_READ) as root:
            subkey_count = winreg.QueryInfoKey(root)[0]
            for i in range(subkey_count):
                subkey_name = winreg.EnumKey(root, i)
                try:
                    with winreg.OpenKey(root, subkey_name) as subkey:
                        value_count = winreg.QueryInfoKey(subkey)[1]
                        for j in range(value_count):
                            name, value, _ = winreg.EnumValue(subkey, j)
                            if search_term.lower() in str(value).lower():
                                found_paths.append(value)
                except Exception:
                    continue
    except Exception:
        pass
    return found_paths

def check_path_for_sequel(path, game_name):
    """Check if a path contains a sequel number that doesn't match the game name"""
    path_lower = str(path).lower()
    game_lower = game_name.lower()
    
    # Extract numbers from the game name (if any)
    game_numbers = re.findall(r'\d+', game_lower)
    
    # Look for numbers in the path that come after the game name
    path_parts = path_lower.split(game_lower.split()[0], 1)
    if len(path_parts) > 1:
        after_game = path_parts[1]
        path_numbers = re.findall(r'\d+', after_game)
        
        # If the game has no numbers but the path does, it's a sequel
        if not game_numbers and path_numbers:
            return True
            
        # If both have numbers, they should match
        if game_numbers and path_numbers:
            return game_numbers[0] != path_numbers[0]
    
    return False

def is_valid_save_location(path, game_name):
    """Check if a path is likely to be a valid save location"""
    # Skip system directories and temp files
    if any(skip in str(path).lower() for skip in ['windows', 'program files', 'temp', '$recycle.bin']):
        return False
        
    # Skip if path is too deep
    if len(path.parts) > 10:
        return False

    path_str = str(path)
    
    # Skip crashlog directories
    if 'crashlog' in path_str.lower():
        return False
        
    # Check for sequel numbers in the path
    if check_path_for_sequel(path, game_name):
        return False
    
    # Basic name matching
    game_parts = game_name.lower().split()
    path_parts = path_str.lower().split()
    
    # The first word of the game name must be present
    if game_parts[0] not in ' '.join(path_parts):
        return False
    
    # For exact match checking
    game_name_lower = game_name.lower()
    path_lower = path_str.lower()
    
    # Check for save file types
    has_save_files = False
    try:
        save_extensions = {'.sav', '.save', '.dat', '.bin', '.json', '.profile'}
        has_save_files = any(f.suffix.lower() in save_extensions for f in path.glob('*.*'))
    except Exception:
        pass

    # Check for numbered save directory pattern (e.g., .1911)
    parent_is_numbered = bool(re.match(r'\.\d+$', path.parent.name))
    
    # Return true if it's either a numbered save directory or matches the game name exactly
    return (parent_is_numbered and game_name_lower in path_lower) or (game_name_lower in path_lower and has_save_files)

def find_system_saves(app_id, game_name, developers):
    """Comprehensive save location search with improved accuracy"""
    save_locations = []
    
    # Standard system locations
    system_paths = [
        Path(os.environ['USERPROFILE']) / 'Documents',
        Path(os.environ['USERPROFILE']) / 'Saved Games',
        Path(os.environ['USERPROFILE']) / 'AppData' / 'Local',
        Path(os.environ['USERPROFILE']) / 'AppData' / 'LocalLow',
        Path(os.environ['USERPROFILE']) / 'AppData' / 'Roaming',
        Path(os.environ['USERPROFILE']) / 'My Games'
    ]

    # Game-specific registry locations
    registry_paths = search_registry_for_paths(game_name)
    system_paths.extend([Path(p) for p in registry_paths if Path(p).exists()])

    # Deep directory scan with improved filtering
    for base_path in system_paths:
        if not base_path.exists():
            continue
            
        try:
            max_depth = 4
            for path in base_path.rglob('*'):
                if path.is_dir() and len(path.parts) - len(base_path.parts) <= max_depth:
                    if is_valid_save_location(path, game_name):
                        # If we find a valid save location, check if its parent is also a valid save location
                        parent = path.parent
                        parent_is_valid = is_valid_save_location(parent, game_name)
                        
                        # Only add the path if its parent isn't already a valid save location
                        if not parent_is_valid:
                            save_locations.append(str(path))
        except Exception:
            continue

    # PCGamingWiki integration
    try:
        wiki_response = requests.get(f"https://www.pcgamingwiki.com/api/appid/{app_id}", timeout=10)
        if wiki_response.status_code == 200:
            wiki_data = wiki_response.json()
            if 'save_game' in wiki_data:
                wiki_path = Path(os.path.expandvars(wiki_data['save_game']))
                if wiki_path.exists():
                    save_locations.append(f"PCGamingWiki: {wiki_path}")
    except Exception:
        pass

    return sorted(set(save_locations))

def main():
    # Set the console title
    set_console_title("Steam Save Locator")

    # ============================================
    ascii_art = r"""
███████╗████████╗███████╗ █████╗ ███╗   ███╗███████╗ █████╗ ██╗   ██╗███████╗██╗      ██████╗  ██████╗ █████╗ ████████╗ ██████╗ ██████╗ 
██╔════╝╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██╔════╝██╔══██╗██║   ██║██╔════╝██║     ██╔═══██╗██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗
███████╗   ██║   █████╗  ███████║██╔████╔██║███████╗███████║██║   ██║█████╗  ██║     ██║   ██║██║     ███████║   ██║   ██║   ██║██████╔╝
╚════██║   ██║   ██╔══╝  ██╔══██║██║╚██╔╝██║╚════██║██╔══██║╚██╗ ██╔╝██╔══╝  ██║     ██║   ██║██║     ██╔══██║   ██║   ██║   ██║██╔══██╗
███████║   ██║   ███████╗██║  ██║██║ ╚═╝ ██║███████║██║  ██║ ╚████╔╝ ███████╗███████╗╚██████╔╝╚██████╗██║  ██║   ██║   ╚██████╔╝██║  ██║
╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═
    """
    print(f"{Fore.CYAN}{ascii_art}{Fore.RESET}")
    # ============================================

    print(f"{Fore.CYAN}steam save locator")
    print(f"{Fore.YELLOW}for the lazy or the ones that cant be bothered{Fore.RESET}")
    
    try:
        app_id = int(input(f"\n{Fore.WHITE}Enter Steam Game ID: {Fore.CYAN}"))
    except ValueError:
        print(f"\n{Fore.RED}❌ Invalid ID! Must be a number (e.g. 292030)")
        input(f"{Fore.YELLOW}Press Enter to exit...")
        return

    game_name, developers = get_steam_game_info(app_id)
    print(f"\n{Fore.WHITE}Searching for:{Fore.GREEN} {game_name}")
    if developers:
        print(f"{Fore.WHITE}Developer(s):{Fore.CYAN} {', '.join(developers)}")
    else:
        print(f"{Fore.WHITE}Developer(s):{Fore.YELLOW} Could not retrieve developer info")
    
    print(f"\n{Fore.YELLOW}🔍 Scanning system...{Fore.RESET}")
    found_paths = []
    
    # Multi-source search
    found_paths += find_steam_cloud_saves(app_id)
    found_paths += find_system_saves(app_id, game_name, developers)
    
    # Display results
    if found_paths:
        print(f"\n{Fore.GREEN}✅ Found {len(found_paths)} save locations:{Fore.RESET}")
        for idx, path in enumerate(sorted(set(found_paths)), 1):
            print(f"{Fore.WHITE}{idx:2}. {Fore.CYAN}{path}")
    else:
        print(f"\n{Fore.RED}❌ No save locations found{Fore.RESET}")
        print(f"{Fore.YELLOW}Try checking these manually:{Fore.RESET}")
        print(f"- Game installation folder")
        print(f"- Documents/My Games subfolders")
        print(f"- AppData/LocalLow (common for Unity games)")
    
    # Offer to open paths
    if found_paths:
        try:
            choice = input(f"\n{Fore.WHITE}Open a location? (1-{len(found_paths)} or N): {Fore.CYAN}")
            if choice.isdigit() and 1 <= int(choice) <= len(found_paths):
                os.startfile(found_paths[int(choice)-1])
        except Exception:
            pass
    
    input(f"\n{Fore.YELLOW}Press Enter to exit...{Fore.RESET}")

if __name__ == "__main__":
    main()