import os
import datetime

# Gera um nome de arquivo único com timestamp
timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
NAME_FILE = f"bot-project-{timestamp}.txt"
OUTPUT_FILE = os.path.join("data", "docs", "tree-histories",NAME_FILE)

def get_icon(filename):
    """Define o prefixo para arquivos e pastas"""
    return "[D] " if os.path.isdir(filename) else "[F] "

def print_tree(directory, ignore_dirs=["venv", "__pycache__"], ignore_files=["tree.py"], prefix="", output_lines=None):
    """Lista diretórios e arquivos ignorando pastas e arquivos específicos, formatado profissionalmente."""
    
    if output_lines is None:
        output_lines = []

    # Garante que a saída será escrita corretamente no arquivo
    directory = os.path.abspath(directory)

    # Obtém todos os itens dentro do diretório, ordenados
    items = sorted(os.listdir(directory))

    # Remove as pastas e arquivos indesejados da listagem
    items = [item for item in items if item not in ignore_dirs and item not in ignore_files]

    for index, item in enumerate(items):
        path = os.path.join(directory, item)
        is_last = index == len(items) - 1

        # Define o conector visual para hierarquia
        connector = "└── " if is_last else "├── "
        
        # Adiciona prefixo (D para diretórios, F para arquivos)
        line = f"{prefix}{connector}{get_icon(path)}{item}"
        output_lines.append(line)

        # Se for diretório, verifica a lógica de `venv`
        if os.path.isdir(path):
            new_prefix = prefix + ("    " if is_last else "│   ")

            if item == "venv":
                # Lista apenas os diretórios de primeiro nível dentro de venv
                subdirs = [sub for sub in sorted(os.listdir(path)) if os.path.isdir(os.path.join(path, sub))]
                for sub_index, sub in enumerate(subdirs):
                    sub_path = os.path.join(path, sub)
                    sub_is_last = sub_index == len(subdirs) - 1
                    sub_connector = "└── " if sub_is_last else "├── "
                    output_lines.append(f"{new_prefix}{sub_connector}[D] {sub}")
            else:
                print_tree(path, ignore_dirs, ignore_files, new_prefix, output_lines)

    return output_lines

def get_file_contents(directory, output_lines):
    """Adiciona o conteúdo dos arquivos dentro de `src/` ao relatório."""
    output_lines.append("\n" + "="*80)
    output_lines.append("📄 Conteúdo dos Arquivos em src/")
    output_lines.append("="*80 + "\n")

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)

            # Ignorar arquivos binários e não relacionados a código
            if file.endswith((".py", ".txt", ".md", ".env", ".ini", ".cfg")):
                output_lines.append(f"\n===== {file_path} =====\n")
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        output_lines.append(f.read())
                except Exception as e:
                    output_lines.append(f"Erro ao ler {file}: {str(e)}")

def generate_report_header():
    """Gera o cabeçalho do relatório com nome do projeto e data da atualização."""
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")  # Obtém a data atual
    header = [
        "="*80,
        " " * 25 + "PROJETO SUPER BOT ENG CLEYTON 1.0",
        " Cognitive Logic Engineered for Yield-driven Technology and Operational Networks",
        "="*80,
        " " * 35 + f"ATUALIZAÇÃO DATA {current_date}",
        "="*80,
        " " * 28 + "ESTRUTURA DE PASTAS E ARQUIVOS",
        "\n"
    ]
    return header

def save_tree_to_file(output_file):
    """Executa a função de tree, adiciona conteúdos dos arquivos e salva no arquivo especificado."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)  # Garante que o diretório existe

    # Cria a estrutura do relatório com o cabeçalho
    report_output = generate_report_header()

    # Adiciona a estrutura de diretórios
    report_output.extend(print_tree(".", ignore_dirs=["__pycache__"], ignore_files=["tree.py"]))

    # Adiciona o conteúdo dos arquivos da pasta `src/`
    get_file_contents("src", report_output)

    # Salva no arquivo
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_output))

    print(f"📂 Estrutura e conteúdos dos arquivos de `src/` salvos em: {output_file}")

# Executa e salva o resultado
save_tree_to_file(OUTPUT_FILE)
