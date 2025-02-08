# utils/data_utils.py
def normalize_message(row):
    """Normaliza uma mensagem do SQLite para o formato do Notion"""
    row_dict = dict(row)  # Converte sqlite3.Row para dict
    return {
        "User ID": row_dict.get("user_id"),
        "Role": row_dict.get("role"),
        "Content": row_dict.get("content"),
        # Adicione outras conversões se necessário
    }
