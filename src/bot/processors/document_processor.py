# src/bot/processors/document_processor.py
from abc import ABC, abstractmethod
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
# import pytesseract
# from PIL import Image
import re

logger = logging.getLogger('DocumentProcessor')

@dataclass
class NFSeData:
    """
    Estrutura de dados para NFSe.

    Esta classe representa os dados de uma Nota Fiscal de Serviço Eletrônico.
    """
    numero: str
    data_emissao: datetime
    codigo_verificacao: str
    prestador_nome: str
    prestador_cnpj: str

    tomador_nome: str
    tomador_cnpj: str
    valor_servico: float
    valor_liquido: float
    codigo_obra: str
    retencoes: Dict[str, float]

@dataclass
class APData:
    """
    Estrutura de dados para Autorização de Pagamento.

    Esta classe representa os dados de uma Autorização de Pagamento.
    """
    numero: str
    data_emissao: datetime
    data_vencimento: datetime
    fornecedor: str
    valor_bruto: float

    valor_liquido: float
    codigo_obra: str
    retencoes: Dict[str, float]

class DocumentProcessor(ABC):   
    """
    Classe base para processamento de documentos.

    Esta classe define a estrutura básica para processar documentos
    usando OCR (Optical Character Recognition).
    """
    

    def __init__(self):
        self.config = {
            'tesseract_cmd': r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        }
        pytesseract.pytesseract.tesseract_cmd = self.config['tesseract_cmd']
    
    def extract_text(self, image_path: str) -> str:
        """
        Extrai texto de uma imagem usando OCR.

        Esta função usa a biblioteca pytesseract para extrair texto
        de uma imagem e retornar uma string com o texto extraído.
        """
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='por')
            return text

        except Exception as e:
            logger.error(f"Erro ao extrair texto da imagem: {str(e)}")
            raise

    def clean_text(self, text: str) -> str:
        """
        Limpa o texto extraído removendo caracteres indesejados.

        Esta função remove caracteres especiais mantendo pontuação relevante
        e remove espaços múltiplos para manter o texto limpo e legível.
        """
        # Remove caracteres especiais mantendo pontuação relevante
        text = re.sub(r'[^\w\s.,:-@]', '', text)
        # Remove espaços múltiplos
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    
    def extract_date(self, text: str, pattern: str) -> Optional[datetime]:
        """
        Extrai data do texto usando regex.

        Esta função usa expressões regulares para encontrar e extrair
        uma data no formato dd/mm/yyyy a partir de um texto.
        """
        try:
            match = re.search(pattern, text)

            if match:
                date_str = match.group(1)
                return datetime.strptime(date_str, '%d/%m/%Y')
            return None
        except Exception as e:
            logger.error(f"Erro ao extrair data: {str(e)}")
            return None
    
    def extract_value(self, text: str, pattern: str) -> Optional[float]:
        """
        Extrai valor monetário do texto usando regex.

        Esta função usa expressões regulares para encontrar e extrair
        um valor monetário no formato R$ 1.234,56 a partir de um texto.
        """
        try:
            match = re.search(pattern, text)

            if match:
                value_str = match.group(1).replace('.', '').replace(',', '.')
                return float(value_str)
            return None
        except Exception as e:
            logger.error(f"Erro ao extrair valor: {str(e)}")
            return None
    
    @abstractmethod
    def process(self, image_path: str) -> Any:
        """
        Processa o documento e retorna os dados estruturados.

        Esta função é abstrata e deve ser implementada pelas subclasses
        para processar documentos específicos.
        """
        pass


class NFSeProcessor(DocumentProcessor):
    """
    Processador específico para NFSe de Manaus.

    Esta classe herda de DocumentProcessor e implementa a lógica
    para processar dados de NFSe de Manaus.
    """
    

    def __init__(self):
        super().__init__()
        self.patterns = {
            'numero': r'Número da Nota\s*(\d+)',
            'data_emissao': r'Data/Hora de emissão\s*(\d{2}/\d{2}/\d{4})',
            'codigo_verificacao': r'Código de verificação\s*([A-Za-z0-9.-]+)',
            'valor_servico': r'Valor do Serviço\s*R\$\s*([\d.,]+)',
            'codigo_obra': r'Centro de Custo:\s*(\d{2}\.\d{2}\.\d{2})'
        }
    
    def process(self, image_path: str) -> NFSeData:
        """
        Processa uma NFSe e retorna os dados estruturados.

        Esta função implementa a lógica para processar uma NFSe
        e retornar os dados estruturados conforme a classe NFSeData.
        """
        try:
            # Extrai texto da imagem

            text = self.extract_text(image_path)
            text = self.clean_text(text)
            logger.debug(f"Texto extraído: {text[:200]}...")
            
            # Extrai dados usando regex
            numero = re.search(self.patterns['numero'], text)
            data_emissao = self.extract_date(text, self.patterns['data_emissao'])
            valor_servico = self.extract_value(text, self.patterns['valor_servico'])
            codigo_obra = re.search(self.patterns['codigo_obra'], text)
            
            # Cria e retorna objeto com os dados
            return NFSeData(
                numero=numero.group(1) if numero else '',
                data_emissao=data_emissao or datetime.now(),
                codigo_verificacao='',  # Implementar
                prestador_nome='',      # Implementar
                prestador_cnpj='',      # Implementar
                tomador_nome='',        # Implementar
                tomador_cnpj='',        # Implementar
                valor_servico=valor_servico or 0.0,
                valor_liquido=0.0,      # Implementar
                codigo_obra=codigo_obra.group(1) if codigo_obra else '',
                retencoes={}            # Implementar
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar NFSe: {str(e)}")
            raise