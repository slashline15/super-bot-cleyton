# python -m tests.provider
#----------CÓDIGO ESCRITO PELO DANIEL-------------#
#------- POSSIVELMENTE, NÃO VAI RODAR ------------#

import dotenv
import os

dotenv.load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER")

print(f"AI é {LLM_PROVIDER}")
