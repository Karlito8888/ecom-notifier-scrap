import os
import sys
import json
from datetime import datetime
from pathlib import Path
import urllib3
import requests
from selectolax.parser import HTMLParser
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

PRICE_FILEPATH = Path(__file__).parent / "price.json"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger.remove()
logger.add(sys.stderr, level="DEBUG")
logger.add("logs/debug.log", level="WARNING", rotation="1 MB")

def write_price_to_file(price: int):
    logger.info(f"Ecriture du nouveau prix : {price}€ dans le fichier")
    if PRICE_FILEPATH.exists():
        with open(PRICE_FILEPATH, "r") as f:
            data = json.load(f)
    else:
        data = []
        
    data.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "price": price
    })
    
    with open(PRICE_FILEPATH, "w") as f:
        json.dump(data, f, indent=4)
    
def get_price_difference(current_price: int) -> int:
    logger.info(f"Calcul de la différence de prix")
    if PRICE_FILEPATH.exists():
        with open(PRICE_FILEPATH, "r") as f:
            data = json.load(f)
        
        previous_price = data[-1]["price"]
    else:
        previous_price = current_price
    
    try:    
        return round((previous_price - current_price) / previous_price * 100)
    except ZeroDivisionError as e:
        logger.error("La var previous price est 0: division impossible")
        raise e
        

def send_alert(message):
    logger.info(f"Envoi de l'alerte par message: {message}") 

    try: 
        response = requests.post("https://api.pushover.net/1/messages.json",
                  data={"token": os.environ.get("PUSHOVER_TOKEN"),
                        "user": os.environ.get("PUSHOVER_USER"),
                        "message": message})
        response.raise_for_status()
        
    except requests.RequestException as e:
        logger.error(f"Erreur lors de l'envoi de l'alerte : {str(e)}")
        raise e

def get_current_price(asin: str):
    proxies = {
        "http": os.environ.get("PROXY"),
        "https": os.environ.get("PROXY")
    }
    
    url = f"https://www.amazon.com/dp/{asin}/"
    
    try:
        response = requests.get(url, proxies=proxies, verify=False)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la récupération de la page {url}: {str(e)}")
        raise e
    
    html_content = response.text
    
    # with open("amazon.html", "w") as f:
    #     f.write(html_content)
        
    tree = HTMLParser(html_content)
    price_node = tree.css_first("span.a-price-whole")
    if price_node:
        return int(price_node.text().replace(".", ""))
    
    error_msg = f"Prix introuvable à {url}"
    logger.error(error_msg)
    raise ValueError(error_msg)

def main(asin: str):
    current_price = get_current_price(asin=asin)
    price_difference = get_price_difference(current_price=current_price)
    write_price_to_file(price=current_price)
    
    if price_difference > 0:
        message = f"Le prix de {asin} a baissé de {price_difference}%"
        send_alert(message=message)

if __name__ == '__main__':
    asin = "B0BWNR58HW"
    main(asin)
    # print(main(url))
    # current_price = main(url)
    # if current_price:
    #     write_price_to_file(price=current_price)
    #     price_difference = get_price_difference(current_price)
    #     print(f"Price difference detected: {price_difference}%")

