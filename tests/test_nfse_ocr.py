# test_nfse_ocr.py
import pytesseract
from PIL import Image
import re
from datetime import datetime

# Define o caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def clean_text(text: str) -> str:
    """Limpa o texto removendo caracteres problemáticos"""
    text = text.replace('„', ',')  # Corrige vírgulas especiais
    text = text.replace('"', "'")  # Corrige apóstrofos
    text = re.sub(r'\s+', ' ', text)  # Remove espaços múltiplos
    return text

def extract_nfse_info(image_path: str) -> dict:
    """Extrai informações relevantes da NFSe"""
    # Abre a imagem
    image = Image.open(image_path)
    
    # Extrai texto com OCR
    print("Iniciando extração de texto...")
    text = pytesseract.image_to_string(image, lang='por')
    text = clean_text(text)
    
    # Padrões de regex melhorados
    patterns = {
        'numero': r'[Nn][úu]mero\s*(?:da\s*)?[Nn]ota\s*:?\s*(\d+)',
        'data_emissao': r'(?:Data/Hora\s*(?:de|da)\s*emiss[ãa]o|emiss[ãa]o)\s*:?\s*(\d{2}/\d{2}/\d{4})',
        'codigo_verificacao': r'[Cc][óo]digo\s*(?:de)?\s*verifica[çc][ãa]o\s*:?\s*([A-Za-z0-9.-]+)',
        'valor_servico': r'Valor\s*(?:do)?\s*Servi[çc]o\s*(?:\(R\$\)|\(?R\$\)?)\s*([\d.,]+)',
        'codigo_obra': r'(?:CENTRO\s*DE\s*CUSTO|[Cc]entro\s*[Cc]usto)\s*:?\s*(\d{2}\.\d{2}\.\d{2})',
        'prestador_nome': r'B\s*ROSA\s*LTDA',
        'prestador_cnpj': r'(?:CPF/CNPJ|CNPJ)\s*:?\s*(\d{2}\.?\d{3}\.?\d{3}/\d{4}-\d{2})',
        'tomador_nome': r'CONSTRUTORA\s*HOSS\s*LTDA',
        'tomador_cnpj': r'43\.836\.352/\d{4}-\d{2}',
        'valor_total': r'VALOR\s*TOTAL\s*DA\s*NOTA\s*=\s*R\$\s*([\d.,]+)',
        'retencoes_iss': r'ISS[QN]?\(R\$\)\s*([\d.,]+)',
        'retencoes_inss': r'(?:INSS|Retenção\s*Previdenciária)\s*\(R\$\)\s*([\d.,]+)',
        'valor_liquido': r'[Vv]alor\s*[Ll][íi]quido\s*(?:da\s*[Nn]ota)?\s*\(R\$\)\s*([\d.,]+)'
    }
    
    # Dicionário para armazenar os resultados
    results = {}
    
    # Extrai cada informação usando os padrões
    print("\nExtraindo informações...")
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip() if match.groups() else match.group(0).strip()
            results[key] = value
            print(f"✓ {key}: {value}")
        else:
            results[key] = None
            print(f"✗ {key}: Não encontrado")
    
    # Converte valores monetários
    monetary_fields = ['valor_servico', 'valor_total', 'retencoes_iss', 'retencoes_inss', 'valor_liquido']
    for field in monetary_fields:
        if results.get(field):
            try:
                valor = results[field].replace('.', '').replace(',', '.')
                results[field] = float(valor)
                print(f"✓ Conversão de {field}: {results[field]}")
            except ValueError:
                print(f"✗ Erro ao converter {field}: {results[field]}")
    
    print("\nTexto completo extraído para debug:")
    print("-" * 50)
    print(text)
    print("-" * 50)
    
    return results

if __name__ == "__main__":
    # Substitua pelo caminho da sua imagem
    image_path = r"C:\Users\danie\OneDrive\Área de Trabalho\bot2\data\docs\Image December 04, 2024 - 2 44AM (1).jpeg"  # Ajuste o caminho conforme necessário
    

    try:
        info = extract_nfse_info(image_path)
        print("\nInformações extraídas com sucesso!")
        
    except Exception as e:
        print(f"Erro durante o processamento: {str(e)}")
        
    #image_path = r"C:\Users\danie\OneDrive\Área de Trabalho\bot2\data\docs\Image December 04, 2024 - 2 44AM (1).jpeg"
    # info = extract_nfse_info(image_path)
    # print("\nInformações extraídas com sucesso!")
    
    print(info)