# src/bot/models/authorization_data.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

"""
Modelo de dados para Autorização de Pagamento.

Este módulo define a estrutura de dados para autorizações de pagamento,
incluindo cálculos automáticos de valores e formatação para diferentes
representações.

Example:
    >>> from datetime import datetime
    >>> auth = AuthorizationData(
    ...     ficha_numero="AP001",
    ...     nf_doc_numero="NF123",
    ...     emissao=datetime.now(),
    ...     vencimento=datetime.now(),
    ...     fornecedor="Fornecedor A"
    ... )
    >>> print(f"Valor líquido: {auth.valor_liquido}")
"""

@dataclass
class AuthorizationData:
    """
    Modelo de dados para Autorização de Pagamento.

    Esta classe representa uma autorização de pagamento com todos os
    campos necessários e cálculos automáticos de valores.

    Attributes:
        ficha_numero (str): Número da ficha de autorização
        nf_doc_numero (str): Número do documento fiscal
        emissao (datetime): Data de emissão
        vencimento (datetime): Data de vencimento
        fornecedor (str): Nome do fornecedor
        valor_bruto_material (float): Valor bruto de materiais
        valor_bruto_servico (float): Valor bruto de serviços
        retencao_seguridade (float): Valor de retenção para seguridade
        retencao_ir_fonte (float): Valor de retenção de IR na fonte
        retencao_contratual (float): Valor de retenção contratual
        retencao_pis_cofins_csll (float): Valor de retenção PIS/COFINS/CSLL
        retencao_iss (float): Valor de retenção de ISS
        retencao_outros (Optional[float]): Outras retenções
        adiantamento (float): Valor de adiantamento
        codigo_obra (str): Código da obra
        codigo_insumo (Optional[str]): Código do insumo

    Example:
        >>> auth = AuthorizationData(
        ...     ficha_numero="AP001",
        ...     nf_doc_numero="NF123",
        ...     emissao=datetime.now(),
        ...     vencimento=datetime.now(),
        ...     fornecedor="Fornecedor A",
        ...     valor_bruto_material=1000.0
        ... )
        >>> print(auth.to_dict())
    """
    
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
        """
        Calcula o valor líquido da autorização.

        Considera o valor bruto total menos todas as retenções
        e adiantamentos aplicáveis.

        Returns:
            float: Valor líquido calculado

        Example:
            >>> auth = AuthorizationData(...)
            >>> print(f"Valor líquido: R$ {auth.valor_liquido:.2f}")
        """
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
        """
        Converte a autorização para formato de dicionário.

        Formata todos os valores numéricos com duas casas decimais
        e datas no formato dd/mm/yyyy.

        Returns:
            dict: Dicionário com todos os campos formatados

        Example:
            >>> auth = AuthorizationData(...)
            >>> data = auth.to_dict()
            >>> print(f"Fornecedor: {data['fornecedor']}")
        """
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