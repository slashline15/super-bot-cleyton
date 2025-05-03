# python -m src.bot.utils.cnpj
import pprint
import requests
import os

cnpj = "43836352000780"

url = f"https://publica.cnpj.ws/cnpj/{cnpj}"

requisicao = requests.get(url)

pprint(requisicao.json())