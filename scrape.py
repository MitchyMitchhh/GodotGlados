import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin

def scrape_godot_docs(version="4.4")
    """
    Scrape the Godot documentation and save it to files.
    
    Args:
        version (str): Godot version to scrape docs for
    """
    # Create directory for documentation
    output_dir = f"godot_docs_{version}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Base URL for Godot docs
    base_url = f"https://docs.godotengine.org/en/{version}"
    
    # Get the main class reference page
    print(f"Scraping Godot {version} documentation...")
    response = requests.get(f"{base_url}/classes/index.html")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all class links in the class reference
    class_links = []
    for link in soup.select('.toctree-l1 a'):
        href = link.get('href')
        if href and 'class_' in href:
            class_links.append(urljoin(f"{base_url}/classes/", href))
    
    print(f"Found {len(class_links)} classes to scrape")
    
    # Scrape each class page
    for i, link in enumerate(class_links):
        try:
            class_name = link.split('/')[-1].replace('.html', '')
            print(f"Scraping {i+1}/{len(class_links)}: {class_name}")
            
            # Get class page
            response = requests.get(link)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content section
            content = soup.select_one('.section')
            if content:
                # Save to file
                with open(os.path.join(output_dir, f"{class_name}.txt"), 'w', encoding='utf-8') as f:
                    f.write(content.get_text())
            
            # Be nice to the server
            time.sleep(0.5)
        except Exception as e:
            print(f"Error scraping {link}: {e}")
    
    print(f"Documentation scraped and saved to {output_dir}/")
    return output_dir
