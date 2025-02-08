# test_ocr.py
import pytesseract
from PIL import Image

# Define o caminho do executável do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

try:
    # Verifica a versão instalada
    version = pytesseract.get_tesseract_version()
    print("Versão do Tesseract:", version)
    print("Tesseract configurado com sucesso!")
    
except Exception as e:
    print("Erro ao configurar Tesseract:")
    print(str(e))
    print("\nVerifique se o caminho está correto:")
    print("- Atual:", pytesseract.pytesseract.tesseract_cmd)
    print("\nDicas de solução:")
    print("1. Verifique se o Tesseract está instalado em 'C:\\Program Files\\Tesseract-OCR'")
    print("2. Se estiver em outro local, atualize o caminho no script")
    print("3. Certifique-se que você tem permissão para acessar o diretório")