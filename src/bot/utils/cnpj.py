#!/usr/bin/env python3
# python -m src.bot.utils.cnpj
"""
Utilitário completo para consulta e formatação de dados de CNPJ.
Usa a API pública https://publica.cnpj.ws/
"""

import argparse
import datetime
import json
import locale
import os
import re
import requests
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Optional

# Configurar locale BR para formatação de números
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        pass  # Foda-se, vai sem formatação brasileira mesmo

# Constantes
API_BASE_URL = "https://publica.cnpj.ws/cnpj"
CACHE_DIR = Path(os.path.expanduser("~/.cache/cnpj_consulta"))


class CNPJError(Exception):
    """Exceção personalizada para erros de CNPJ."""
    pass


def validar_cnpj(cnpj: str) -> str:
    """Valida e limpa o formato do CNPJ."""
    # Remove caracteres não numéricos
    cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
    
    # Verifica se o CNPJ tem 14 dígitos
    if len(cnpj_limpo) != 14:
        raise CNPJError(f"CNPJ inválido: deve ter 14 dígitos, encontrado {len(cnpj_limpo)}")
    
    # Verifica se todos os dígitos são iguais (isso é inválido)
    if len(set(cnpj_limpo)) == 1:
        raise CNPJError("CNPJ inválido: todos os dígitos são iguais")
    
    # Calcula dígitos verificadores
    numeros = [int(digit) for digit in cnpj_limpo]
    
    # Cálculo do primeiro dígito verificador
    soma = sum(a * b for a, b in zip(numeros[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
    resto = soma % 11
    dv1 = 0 if resto < 2 else 11 - resto
    
    if numeros[12] != dv1:
        raise CNPJError(f"CNPJ inválido: primeiro dígito verificador errado. Esperado {dv1}, obtido {numeros[12]}")
    
    # Cálculo do segundo dígito verificador
    soma = sum(a * b for a, b in zip(numeros[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
    resto = soma % 11
    dv2 = 0 if resto < 2 else 11 - resto
    
    if numeros[13] != dv2:
        raise CNPJError(f"CNPJ inválido: segundo dígito verificador errado. Esperado {dv2}, obtido {numeros[13]}")
    
    return cnpj_limpo


def formatar_cnpj(cnpj: str) -> str:
    """Formata o CNPJ no padrão XX.XXX.XXX/XXXX-XX."""
    if len(cnpj) != 14:
        return cnpj
    
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def formatar_data(data_str: Optional[str]) -> str:
    """Formata uma data no padrão brasileiro (DD/MM/AAAA)."""
    if not data_str:
        return "Não informada"
    
    try:
        data = datetime.datetime.fromisoformat(data_str)
        return data.strftime("%d/%m/%Y")
    except ValueError:
        return data_str


def formatar_dinheiro(valor: Any) -> str:
    """Formata um valor monetário no padrão brasileiro."""
    if valor is None:
        return "Não informado"
    
    # CORREÇÃO: Garantir que valor seja um número
    try:
        # Se for string, converter para float
        if isinstance(valor, str):
            # Remover possíveis pontos e vírgulas
            valor_limpo = valor.replace('.', '').replace(',', '.')
            valor = float(valor_limpo)
        else:
            valor = float(valor)  # Garantir que seja float
        
        try:
            return locale.currency(valor, grouping=True, symbol=True)
        except (ValueError, locale.Error):
            # Fallback maneiro se o locale não estiver configurado
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        # Se não conseguir converter para número, retorna como texto
        return f"R$ {valor}" if valor else "Não informado"


def obter_valor_seguro(dicionario: Dict[str, Any], caminho: str, padrao: Any = "Não informado") -> Any:
    """
    Obtém um valor de um dicionário aninhado de forma segura.
    Ex: obter_valor_seguro(dados, "estabelecimento.cidade.nome", "N/A")
    """
    partes = caminho.split('.')
    atual = dicionario
    
    try:
        for parte in partes:
            if isinstance(atual, dict) and parte in atual:
                atual = atual[parte]
            else:
                return padrao
        return atual if atual is not None else padrao
    except Exception:
        return padrao


@lru_cache(maxsize=128)
def busca_CNPJ(cnpj: str, usar_cache: bool = True) -> Dict[str, Any]:
    """
    Busca informações de um CNPJ na API pública.
    
    Args:
        cnpj: CNPJ a ser consultado (com ou sem pontuação).
        usar_cache: Se True, usa cache local para consultas repetidas.
        
    Returns:
        Dicionário com os dados do CNPJ.
        
    Raises:
        CNPJError: Se houver erro na consulta ou CNPJ inválido.
    """
    try:
        cnpj_limpo = validar_cnpj(cnpj)
    except CNPJError as e:
        raise e
    
    # Verifica cache
    if usar_cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = CACHE_DIR / f"{cnpj_limpo}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # Se o cache tá zoado, ignora e segue o baile
                pass
    
    # Faz a requisição à API
    url = f"{API_BASE_URL}/{cnpj_limpo}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            raise CNPJError(f"CNPJ {formatar_cnpj(cnpj_limpo)} não encontrado na base")
        
        response.raise_for_status()  # Levanta exceção para outros erros
        
        dados = response.json()
        
        # Salva no cache
        if usar_cache:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
        
        return dados
    
    except requests.exceptions.RequestException as e:
        raise CNPJError(f"Erro ao consultar CNPJ: {str(e)}")
    except json.JSONDecodeError:
        raise CNPJError("Erro ao processar resposta da API: formato inválido")

def escape_markdown(text):
    """Escapa caracteres especiais para MarkdownV2 do Telegram."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def format_cnpj_info(data: Dict[str, Any], formato: str = 'markdown') -> str:
    """
    Formata os dados de um CNPJ para exibição.
    
    Args:
        data: Dicionário com os dados do CNPJ.
        formato: Formato de saída ('markdown', 'text', 'html', 'json').
        
    Returns:
        String formatada com os dados do CNPJ.
    """
    # Extrai os dados principais
    razao = obter_valor_seguro(data, 'razao_social')
    cnpj_bruto = obter_valor_seguro(data, 'estabelecimento.cnpj')
    cnpj_formatado = formatar_cnpj(cnpj_bruto) if cnpj_bruto != "Não informado" else cnpj_bruto
    natureza = obter_valor_seguro(data, 'natureza_juridica.descricao')
    porte = obter_valor_seguro(data, 'porte.descricao')
    capital = formatar_dinheiro(obter_valor_seguro(data, 'capital_social', None))
    situacao = obter_valor_seguro(data, 'estabelecimento.situacao_cadastral')
    inicio = formatar_data(obter_valor_seguro(data, 'estabelecimento.data_inicio_atividade', None))
    
    # Constrói o endereço completo
    tipo_logradouro = obter_valor_seguro(data, 'estabelecimento.tipo_logradouro', '')
    logradouro = obter_valor_seguro(data, 'estabelecimento.logradouro', '')
    numero = obter_valor_seguro(data, 'estabelecimento.numero', '')
    complemento = obter_valor_seguro(data, 'estabelecimento.complemento', '')
    bairro = obter_valor_seguro(data, 'estabelecimento.bairro', '')
    cidade = obter_valor_seguro(data, 'estabelecimento.cidade.nome', '')
    estado = obter_valor_seguro(data, 'estabelecimento.estado.sigla', '')
    cep_bruto = obter_valor_seguro(data, 'estabelecimento.cep', '')
    
    # Formata o CEP
    cep = f"{cep_bruto[:5]}-{cep_bruto[5:]}" if len(cep_bruto) == 8 else cep_bruto
    
    # Monta o endereço completo
    partes_endereco = []
    if tipo_logradouro and logradouro:
        partes_endereco.append(f"{tipo_logradouro} {logradouro}")
    elif logradouro:
        partes_endereco.append(logradouro)
    
    if numero:
        partes_endereco.append(numero)
    
    if complemento:
        partes_endereco.append(complemento)
    
    if bairro:
        partes_endereco.append(bairro)
    
    cidade_estado = ""
    if cidade and estado:
        cidade_estado = f"{cidade}/{estado}"
    elif cidade:
        cidade_estado = cidade
    elif estado:
        cidade_estado = estado
    
    if cidade_estado:
        partes_endereco.append(cidade_estado)
    
    if cep:
        partes_endereco.append(f"CEP {cep}")
    
    endereco = ", ".join(filter(None, partes_endereco))
    if not endereco:
        endereco = "Não informado"
    
    # Atividades
    atividade_principal = obter_valor_seguro(data, 'estabelecimento.atividade_principal.descricao', "Não informada")
    atividades_secundarias = []
    
    for atividade in obter_valor_seguro(data, 'estabelecimento.atividades_secundarias', []):
        descricao = obter_valor_seguro(atividade, 'descricao')
        if descricao != "Não informado":
            codigo = obter_valor_seguro(atividade, 'codigo', '')
            if codigo:
                atividades_secundarias.append(f"{codigo} - {descricao}")
            else:
                atividades_secundarias.append(descricao)
    
    # Formata lista de sócios (corrigindo o bug principal da função original)
    socios_lista = []
    for socio in obter_valor_seguro(data, 'socios', []):
        nome = obter_valor_seguro(socio, 'nome')
        qualificacao = obter_valor_seguro(socio, 'qualificacao.descricao', '')
        
        if qualificacao:
            socios_lista.append(f"{nome} ({qualificacao})")
        else:
            socios_lista.append(nome)
    
    # Informações do Simples Nacional
    simples = obter_valor_seguro(data, 'simples.simples', None)
    mei = obter_valor_seguro(data, 'simples.mei', None)
    
    simples_info = []
    if simples is not None:
        simples_info.append(f"Simples Nacional: {'Sim' if simples else 'Não'}")
    
    if mei is not None:
        simples_info.append(f"MEI: {'Sim' if mei else 'Não'}")
    
    if simples_info:
        simples_str = ", ".join(simples_info)
    else:
        simples_str = "Não informado"
    
    # Formatação em diferentes formatos
    if formato.lower() == 'json':
        return json.dumps({
            "razao_social": razao,
            "cnpj": cnpj_formatado,
            "natureza_juridica": natureza,
            "porte": porte,
            "capital_social": capital,
            "situacao_cadastral": situacao,
            "data_inicio_atividade": inicio,
            "endereco": endereco,
            "atividade_principal": atividade_principal,
            "atividades_secundarias": atividades_secundarias,
            "socios": socios_lista,
            "simples_nacional": simples_str
        }, ensure_ascii=False, indent=2)
    
    elif formato.lower() == 'html':
        atividades_secundarias_html = ""
        if atividades_secundarias:
            atividades_secundarias_html = "<ul>\n" + "\n".join([f"  <li>{a}</li>" for a in atividades_secundarias]) + "\n</ul>"
        else:
            atividades_secundarias_html = "<p>Não informadas</p>"
        
        socios_html = ""
        if socios_lista:
            socios_html = "<ul>\n" + "\n".join([f"  <li>{s}</li>" for s in socios_lista]) + "\n</ul>"
        else:
            socios_html = "<p>Não informados</p>"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Informações de CNPJ - {razao}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #3498db; margin-top: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .section {{ margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .label {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{razao}</h1>
        
        <div class="section">
            <p><span class="label">CNPJ:</span> {cnpj_formatado}</p>
            <p><span class="label">Natureza Jurídica:</span> {natureza}</p>
            <p><span class="label">Porte:</span> {porte}</p>
            <p><span class="label">Capital Social:</span> {capital}</p>
            <p><span class="label">Situação Cadastral:</span> {situacao}</p>
            <p><span class="label">Início das Atividades:</span> {inicio}</p>
        </div>
        
        <div class="section">
            <h2>Endereço</h2>
            <p>{endereco}</p>
        </div>
        
        <div class="section">
            <h2>Atividade Principal</h2>
            <p>{atividade_principal}</p>
        </div>
        
        <div class="section">
            <h2>Atividades Secundárias</h2>
            {atividades_secundarias_html}
        </div>
        
        <div class="section">
            <h2>Sócios</h2>
            {socios_html}
        </div>
        
        <div class="section">
            <h2>Simples Nacional</h2>
            <p>{simples_str}</p>
        </div>
    </div>
</body>
</html>"""
        return html
    
    elif formato.lower() == 'text':
        # Formatação para texto simples
        atividades_sec_texto = "\n".join([f"- {a}" for a in atividades_secundarias]) if atividades_secundarias else "Não informadas"
        socios_texto = "\n".join([f"- {s}" for s in socios_lista]) if socios_lista else "Não informados"
        
        return f"""
{razao}
CNPJ: {cnpj_formatado}
Natureza Jurídica: {natureza}
Porte: {porte}
Capital Social: {capital}
Situação Cadastral: {situacao}
Início das Atividades: {inicio}

Endereço:
{endereco}

Atividade Principal:
{atividade_principal}

Atividades Secundárias:
{atividades_sec_texto}

Sócios:
{socios_texto}

Simples Nacional:
{simples_str}
""".strip()
    
    else:  # Markdown (padrão)
        # Formatação em markdown
        atividades_sec_md = "\n".join([f"- {a}" for a in atividades_secundarias]) if atividades_secundarias else "Não informadas"
        socios_md = "\n".join([f"- {s}" for s in socios_lista]) if socios_lista else "Não informados"
        
        return f"""
🏢 **{razao}**
CNPJ: `{cnpj_formatado}`
Natureza Jurídica: {natureza}
Porte: {porte}
Capital Social: {capital}
Situação Cadastral: {situacao}
Início das Atividades: {inicio}

📍 **Endereço:**
{endereco}

🛠️ **Atividade Principal:**
{atividade_principal}

📋 **Atividades Secundárias:**
{atividades_sec_md}

👥 **Sócios:**
{socios_md}

📊 **Simples Nacional:**
{simples_str}
""".strip()


def salvar_resultado(dados: str, cnpj: str, formato: str, diretorio: Optional[str] = None) -> str:
    """Salva o resultado da consulta em um arquivo."""
    # Define extensão baseada no formato
    extensoes = {
        'markdown': 'md',
        'text': 'txt',
        'html': 'html',
        'json': 'json'
    }
    
    extensao = extensoes.get(formato.lower(), 'txt')
    
    # Define o diretório
    if diretorio:
        dir_path = Path(diretorio)
    else:
        dir_path = Path.cwd()
    
    os.makedirs(dir_path, exist_ok=True)
    
    # Define o nome do arquivo
    cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cnpj_{cnpj_limpo}_{timestamp}.{extensao}"
    
    filepath = dir_path / filename
    
    # Salva o arquivo
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(dados)
    
    return str(filepath)


def main() -> None:
    """Função principal para execução como script."""
    parser = argparse.ArgumentParser(description="Consulta e formata dados de CNPJ.")
    parser.add_argument("cnpj", help="CNPJ a ser consultado (com ou sem pontuação)")
    parser.add_argument("--formato", "-f", choices=["markdown", "text", "html", "json"], 
                       default="markdown", help="Formato de saída (padrão: markdown)")
    parser.add_argument("--salvar", "-s", action="store_true", 
                       help="Salvar resultado em arquivo")
    parser.add_argument("--diretorio", "-d", 
                       help="Diretório para salvar o arquivo (se --salvar for usado)")
    parser.add_argument("--nocache", action="store_true", 
                       help="Não usar cache (sempre consultar a API)")
    
    args = parser.parse_args()
    
    try:
        dados = busca_CNPJ(args.cnpj, not args.nocache)
        resultado = format_cnpj_info(dados, args.formato)
        
        if args.salvar:
            filepath = salvar_resultado(resultado, args.cnpj, args.formato, args.diretorio)
            print(f"Resultado salvo em: {filepath}")
        
        print(resultado)
        sys.exit(0)
    
    except CNPJError as e:
        print(f"Erro: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {str(e)}", file=sys.stderr)
        sys.exit(2)




if __name__ == "__main__":
    main()