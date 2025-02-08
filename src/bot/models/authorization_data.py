# src/bot/models/authorization_data.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class AuthorizationData:
    """Modelo de dados para Autorização de Pagamento"""
    
    # Dados de controle
    ficha_numero: str
    nf_doc_numero: str
    emissao: datetime
    vencimento: datetime
    
    # Dados do fornecedor
    fornecedor: str
    
    # Valores
    valor_bruto_material: float = 0.0
    valor_bruto_servico: float = 0.0
    
    # Retenções
    retencao_seguridade: float = 0.0
    retencao_ir_fonte: float = 0.0
    retencao_contratual: float = 0.0
    retencao_pis_cofins_csll: float = 0.0
    retencao_iss: float = 0.0
    retencao_outros: Optional[float] = None
    adiantamento: float = 0.0
    
    # Códigos
    codigo_obra: str
    codigo_insumo: Optional[str] = None

    @property
    def valor_liquido(self) -> float:
        """Calcula o valor líquido"""
        valor_bruto = self.valor_bruto_material + self.valor_bruto_servico
        retencoes = (
            self.retencao_seguridade +
            self.retencao_ir_fonte +
            self.retencao_contratual +
            self.retencao_pis_cofins_csll +
            self.retencao_iss +
            (self.retencao_outros or 0.0) +
            self.adiantamento
        )
        return valor_bruto - retencoes

    def to_dict(self) -> dict:
        """Converte os dados para dicionário"""
        return {
            "ficha_numero": self.ficha_numero,
            "nf_doc_numero": self.nf_doc_numero,
            "emissao": self.emissao.strftime("%d/%m/%Y"),
            "vencimento": self.vencimento.strftime("%d/%m/%Y"),
            "fornecedor": self.fornecedor,
            "valor_bruto_material": f"{self.valor_bruto_material:.2f}",
            "valor_bruto_servico": f"{self.valor_bruto_servico:.2f}",
            "retencao_seguridade": f"{self.retencao_seguridade:.2f}",
            "retencao_ir_fonte": f"{self.retencao_ir_fonte:.2f}",
            "retencao_contratual": f"{self.retencao_contratual:.2f}",
            "retencao_pis_cofins_csll": f"{self.retencao_pis_cofins_csll:.2f}",
            "retencao_iss": f"{self.retencao_iss:.2f}",
            "retencao_outros": f"{self.retencao_outros:.2f}" if self.retencao_outros else "",
            "adiantamento": f"{self.adiantamento:.2f}",
            "valor_liquido": f"{self.valor_liquido:.2f}",
            "codigo_obra": self.codigo_obra,
            "codigo_insumo": self.codigo_insumo or ""
        }