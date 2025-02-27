"""
Modelos de dados para o sistema financeiro.

Este módulo define os modelos SQLAlchemy para representar as entidades
do sistema financeiro, incluindo documentos, transações e configurações.

Attributes:
    Base: Classe base declarativa do SQLAlchemy
    engine: Engine de conexão com o banco de dados

Example:
    >>> from src.bot.database.models import Invoice, PurchaseOrder
    >>> invoice = Invoice(number="NF123", value=1000.00)
"""

class Invoice(Base):
    """
    Modelo para representar notas fiscais no sistema.

    Attributes:
        id (int): Identificador único da NF
        number (str): Número da nota fiscal
        issue_date (datetime): Data de emissão
        value (Decimal): Valor total da NF
        supplier_id (int): ID do fornecedor
        status (str): Status atual da NF

    Example:
        >>> nf = Invoice(number="NF123", value=1500.00)
        >>> db.session.add(nf)
    """

    __tablename__ = 'invoices'

class PurchaseOrder(Base):
    """
    Modelo para representar pedidos de compra.

    Attributes:
        id (int): Identificador único do PC
        code (str): Código do pedido (ex: YR-027)
        creation_date (datetime): Data de criação
        total_value (Decimal): Valor total do pedido
        status (str): Status atual do pedido
        parent_id (int): ID do pedido pai (para pedidos filhotes)

    Example:
        >>> pc = PurchaseOrder(code="YR-027", total_value=5000.00)
        >>> db.session.add(pc)
    """

    __tablename__ = 'purchase_orders' 