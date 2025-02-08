# src/bot/processors/ap_processor.py
from datetime import datetime, timedelta
import re
import logging
from typing import Optional, Tuple
from bot.models.authorization_data import AuthorizationData
from bot.processors.document_processor import DocumentProcessor, NFSeData

logger = logging.getLogger('APProcessor')

class APProcessor(DocumentProcessor):
    """Processa NFSe e gera dados para Autorização de Pagamento"""
    
    def __init__(self):
        super().__init__()
        self.next_ap_number = 1  # Controle de numeração das APs
    
    def process_nfse(self, nfse_data: NFSeData) -> AuthorizationData:
        """
        Processa os dados da NFSe e gera dados para AP
        
        Args:
            nfse_data: Dados da NFSe
            
        Returns:
            AuthorizationData: Dados para preenchimento da AP
        """
        try:
            # Gera número da ficha
            ficha_numero = self._generate_ap_number()
            
            # Define vencimento (padrão: emissão + 20 dias)
            vencimento = nfse_data.data_emissao + timedelta(days=20)
            
            # Calcula retenções com base no tipo de serviço
            retencoes = self._calculate_retencoes(nfse_data.valor_servico)
            
            # Obtém código do insumo pelo tipo de serviço
            codigo_insumo = self._get_codigo_insumo(nfse_data)
            
            # Cria dados da AP
            return AuthorizationData(
                ficha_numero=ficha_numero,
                nf_doc_numero=nfse_data.numero,
                emissao=nfse_data.data_emissao,
                vencimento=vencimento,
                fornecedor=nfse_data.prestador_nome,
                valor_bruto_servico=nfse_data.valor_servico,
                retencao_seguridade=retencoes['inss'],
                retencao_ir_fonte=retencoes['ir'],
                retencao_pis_cofins_csll=retencoes['pcc'],
                retencao_iss=retencoes['iss'],
                codigo_obra=nfse_data.codigo_obra,
                codigo_insumo=codigo_insumo
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar NFSe para AP: {str(e)}")
            raise
    
    def _generate_ap_number(self) -> str:
        """Gera número sequencial para a AP"""
        ap_num = f"YR-{self.next_ap_number:03d}"
        self.next_ap_number += 1
        return ap_num
    
    def _calculate_retencoes(self, valor_bruto: float) -> dict:
        """
        Calcula retenções com base no valor bruto
        
        Args:
            valor_bruto: Valor bruto do serviço
            
        Returns:
            dict: Dicionário com valores de retenção
        """
        # Valores base para cálculo (podem ser configuráveis)
        inss_rate = 0.11  # 11%
        ir_rate = 0.015   # 1.5%
        pcc_rate = 0.035  # 3.5%
        iss_rate = 0.05   # 5%
        
        return {
            'inss': valor_bruto * inss_rate,
            'ir': valor_bruto * ir_rate,
            'pcc': valor_bruto * pcc_rate,
            'iss': valor_bruto * iss_rate
        }
    
    def _get_codigo_insumo(self, nfse: NFSeData) -> Optional[str]:
        """
        Determina o código do insumo com base na descrição do serviço
        
        Args:
            nfse: Dados da NFSe
            
        Returns:
            str: Código do insumo ou None se não encontrado
        """
        # Implementar lógica para determinar código do insumo
        # Por enquanto, retorna o código da obra
        return nfse.codigo_obra
    
    def _extract_obra_info(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Extrai informações da obra do texto
        
        Args:
            text: Texto da NFSe
            
        Returns:
            Tuple[str, Optional[str]]: Código da obra e código do insumo
        """
        # Padrão para código de obra (exemplo: 31.24.14)
        obra_pattern = r'(\d{2}\.\d{2}\.\d{2})'
        obra_match = re.search(obra_pattern, text)
        
        if obra_match:
            return obra_match.group(1), None
        
        return "", None