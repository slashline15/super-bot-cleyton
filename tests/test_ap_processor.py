# tests/test_ap_processor.py
import sys
import os
import logging
from datetime import datetime
from decimal import Decimal

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adiciona o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.bot.processors.document_processor import NFSeData
from src.bot.processors.ap_processor import APProcessor

def test_ap_generation():
    """Testa geração de AP a partir de NFSe"""
    try:
        # Cria processador
        processor = APProcessor()
        
        # Cria NFSe de teste baseada na nota real
        nfse_test = NFSeData(
            numero="870",
            data_emissao=datetime(2024, 10, 8, 14, 35, 13),
            codigo_verificacao="4606.DDD1.B977",
            prestador_nome="B ROSA LTDA",
            prestador_cnpj="04.395.055/0001-07",
            tomador_nome="CONSTRUTORA HOSS LTDA",
            tomador_cnpj="43.836.352/0006-07",
            valor_servico=3500.00,
            valor_liquido=3351.25,
            codigo_obra="31.24.14",
            retencoes={
                'iss': 87.50,
                'inss': 61.25
            }
        )
        
        # Processa NFSe
        logger.info("Processando NFSe para gerar AP...")
        ap_data = processor.process_nfse(nfse_test)
        
        # Verifica dados gerados
        logger.info("Verificando dados gerados:")
        logger.info(f"Número da AP: {ap_data.ficha_numero}")
        logger.info(f"NF/Doc: {ap_data.nf_doc_numero}")
        logger.info(f"Emissão: {ap_data.emissao.strftime('%d/%m/%Y')}")
        logger.info(f"Vencimento: {ap_data.vencimento.strftime('%d/%m/%Y')}")
        logger.info(f"Fornecedor: {ap_data.fornecedor}")
        logger.info(f"Valor Bruto Serviço: R$ {ap_data.valor_bruto_servico:.2f}")
        logger.info(f"Retenções:")
        logger.info(f"  - ISS: R$ {ap_data.retencao_iss:.2f}")
        logger.info(f"  - INSS: R$ {ap_data.retencao_seguridade:.2f}")
        logger.info(f"  - PIS/COFINS/CSLL: R$ {ap_data.retencao_pis_cofins_csll:.2f}")
        logger.info(f"Valor Líquido: R$ {ap_data.valor_liquido:.2f}")
        logger.info(f"Código da Obra: {ap_data.codigo_obra}")
        
        # Validações
        assert ap_data.nf_doc_numero == "870"
        assert ap_data.fornecedor == "B ROSA LTDA"
        assert ap_data.valor_bruto_servico == 3500.00
        assert ap_data.codigo_obra == "31.24.14"
        
        return "Teste de geração de AP concluído com sucesso!"
        
    except Exception as e:
        logger.error(f"Erro durante os testes: {str(e)}")
        raise

if __name__ == "__main__":
    import asyncio
    result = test_ap_generation()
    print(result)