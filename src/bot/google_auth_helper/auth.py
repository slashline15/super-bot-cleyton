# src/bot/google_auth_helper/auth.py
import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.auth.exceptions import RefreshError, DefaultCredentialsError
from cryptography.fernet import Fernet
import base64

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

@dataclass
class CachedToken:
    """Classe para armazenar tokens em cache com tempo de expiração."""
    credentials: Any
    expiry: datetime

class SecureTokenStorage:
    """Armazenamento seguro de tokens usando criptografia."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Inicializa o storage com uma chave de criptografia.
        
        Args:
            encryption_key: Chave para criptografia. Se não fornecida,
                          será gerada e salva no ambiente.
        """
        if encryption_key:
            self.key = base64.urlsafe_b64encode(encryption_key.encode())
        else:
            self.key = os.getenv('TOKEN_ENCRYPTION_KEY')
            if not self.key:
                self.key = Fernet.generate_key()
                os.environ['TOKEN_ENCRYPTION_KEY'] = self.key.decode()
        
        self.cipher_suite = Fernet(self.key)

    def save_token(self, token_path: str, credentials: Credentials) -> None:
        """
        Salva as credenciais de forma segura.
        
        Args:
            token_path: Caminho para salvar o token
            credentials: Credenciais do Google
        """
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # Converte para JSON e criptografa
        token_json = json.dumps(token_data)
        encrypted_data = self.cipher_suite.encrypt(token_json.encode())
        
        # Salva o token criptografado
        with open(token_path, 'wb') as token_file:
            token_file.write(encrypted_data)

    def load_token(self, token_path: str) -> Optional[Credentials]:
        """
        Carrega credenciais de forma segura.
        
        Args:
            token_path: Caminho do arquivo do token
            
        Returns:
            Credentials ou None se o arquivo não existir
        """
        try:
            with open(token_path, 'rb') as token_file:
                encrypted_data = token_file.read()
                
            # Descriptografa e carrega o JSON
            token_json = self.cipher_suite.decrypt(encrypted_data).decode()
            token_data = json.loads(token_json)
            
            return Credentials(
                token=token_data['token'],
                refresh_token=token_data['refresh_token'],
                token_uri=token_data['token_uri'],
                client_id=token_data['client_id'],
                client_secret=token_data['client_secret'],
                scopes=token_data['scopes']
            )
        except FileNotFoundError:
            return None
        except Exception as e:
            logging.error(f"Erro ao carregar token: {str(e)}")
            return None

class GoogleAuthHelper:
    """Helper para autenticação com APIs do Google."""
    
    def __init__(
        self,
        config_dir: str = "~/.google-auth-helper",
        cache_ttl: int = 300,
        encryption_key: Optional[str] = None
    ):
        """
        Inicializa o helper.
        
        Args:
            config_dir: Diretório base para configurações
            cache_ttl: Tempo de vida do cache em segundos
            encryption_key: Chave para criptografia dos tokens
        """
        self.config_dir = os.path.expanduser(config_dir)
        self.cache_ttl = cache_ttl
        self._cached_tokens: Dict[str, CachedToken] = {}
        self.token_storage = SecureTokenStorage(encryption_key)
        
        try:
            Path(self.config_dir).mkdir(parents=True, exist_ok=True)
            logging.info(f"Diretório de configuração inicializado: {self.config_dir}")
        except PermissionError as e:
            logging.error(f"Erro de permissão ao criar diretório: {str(e)}")
            raise

    def _get_token_path(self, project_name: str) -> str:
        """
        Retorna o caminho do arquivo de token para um projeto específico.
        
        Args:
            project_name: Nome do projeto.
            
        Returns:
            Caminho completo para o arquivo de token.
        """
        project_dir = os.path.join(self.config_dir, project_name)
        Path(project_dir).mkdir(parents=True, exist_ok=True)
        return os.path.join(project_dir, "token.json")

    def _get_cached_credentials(self, project_name: str) -> Optional[Any]:
        """
        Recupera credenciais do cache se ainda forem válidas.
        
        Args:
            project_name: Nome do projeto.
            
        Returns:
            Credenciais em cache ou None se não existirem ou estiverem expiradas.
        """
        if project_name in self._cached_tokens:
            cached = self._cached_tokens[project_name]
            if datetime.now() < cached.expiry:
                logging.debug(f"Usando credenciais em cache para {project_name}")
                return cached.credentials
            else:
                logging.debug(f"Cache expirado para {project_name}")
                del self._cached_tokens[project_name]
        return None

    def _cache_credentials(self, project_name: str, credentials: Any) -> None:
        """
        Armazena credenciais no cache.
        
        Args:
            project_name: Nome do projeto.
            credentials: Credenciais a serem armazenadas.
        """
        expiry = datetime.now() + timedelta(seconds=self.cache_ttl)
        self._cached_tokens[project_name] = CachedToken(credentials, expiry)
        logging.debug(f"Credenciais armazenadas em cache para {project_name}")

    def setup_oauth_credentials(
        self,
        scopes: List[str],
        project_name: str,
        client_secrets_file: Optional[str] = None,
        headless: bool = False
    ) -> Credentials:
        """
        Configura credenciais OAuth2.
        
        Args:
            scopes: Escopos necessários
            project_name: Nome do projeto
            client_secrets_file: Arquivo de credenciais
            headless: Modo sem navegador
            
        Returns:
            Credenciais válidas
            
        Raises:
            FileNotFoundError: Se arquivos necessários não forem encontrados
            RefreshError: Se a renovação do token falhar
            DefaultCredentialsError: Se a autenticação falhar
        """
        try:
            # Verifica cache
            cached_creds = self._get_cached_credentials(project_name)
            if cached_creds:
                return cached_creds

            creds = None
            token_path = self._get_token_path(project_name)
            
            # Tenta carregar token existente
            if os.path.exists(token_path):
                creds = self.token_storage.load_token(token_path)

            # Renova ou obtém novas credenciais
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logging.info("Renovando token expirado...")
                    creds.refresh(Request())
                else:
                    creds = self._get_new_credentials(
                        client_secrets_file,
                        scopes,
                        headless
                    )
                
                # Salva credenciais
                self.token_storage.save_token(token_path, creds)

            # Armazena em cache
            self._cache_credentials(project_name, creds)
            return creds
            
        except RefreshError as e:
            logging.error(f"Erro ao renovar token: {str(e)}")
            raise
        except DefaultCredentialsError as e:
            logging.error(f"Erro de autenticação: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Erro inesperado: {str(e)}")
            raise

    def _get_new_credentials(
        self,
        client_secrets_file: Optional[str],
        scopes: List[str],
        headless: bool
    ) -> Credentials:
        """
        Obtém novas credenciais OAuth2.
        
        Args:
            client_secrets_file: Arquivo de credenciais
            scopes: Escopos necessários
            headless: Modo sem navegador
            
        Returns:
            Novas credenciais
            
        Raises:
            FileNotFoundError: Se arquivo de credenciais não for encontrado
        """
        if not client_secrets_file:
            client_secrets_file = os.getenv("GOOGLE_CLIENT_SECRETS")
            if not client_secrets_file or not os.path.exists(client_secrets_file):
                raise FileNotFoundError(
                    "Arquivo client_secrets.json não encontrado. "
                    "Forneça o caminho do arquivo ou defina a variável "
                    "GOOGLE_CLIENT_SECRETS."
                )

        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file,
            scopes
        )
        
        if headless:
            return flow.run_console()
        return flow.run_local_server(port=0)

    def setup_service_account(
        self,
        project_name: str,
        service_account_file: Optional[str] = None
    ) -> service_account.Credentials:
        """
        Configura credenciais de conta de serviço.
        
        Args:
            project_name: Nome do projeto
            service_account_file: Arquivo de credenciais
            
        Returns:
            Credenciais da conta de serviço
            
        Raises:
            FileNotFoundError: Se arquivo não for encontrado
        """
        try:
            cached_creds = self._get_cached_credentials(project_name)
            if cached_creds:
                return cached_creds

            if not service_account_file:
                service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if not service_account_file or not os.path.exists(service_account_file):
                    raise FileNotFoundError(
                        "Arquivo de credenciais da conta de serviço não encontrado."
                    )

            creds = service_account.Credentials.from_service_account_file(
                service_account_file
            )
            
            self._cache_credentials(project_name, creds)
            return creds
            
        except Exception as e:
            logging.error(f"Erro ao configurar conta de serviço: {str(e)}")
            raise

    def list_projects(self) -> Set[str]:
        """
        Lista todos os projetos que têm tokens salvos.
        
        Returns:
            Conjunto com os nomes dos projetos autenticados.
        """
        projects = set()
        try:
            for item in os.listdir(self.config_dir):
                project_path = os.path.join(self.config_dir, item)
                if os.path.isdir(project_path):
                    token_path = os.path.join(project_path, "token.json")
                    if os.path.exists(token_path):
                        projects.add(item)
            
            logging.info(f"Encontrados {len(projects)} projetos autenticados")
            return projects
        except Exception as e:
            logging.error(f"Erro ao listar projetos: {str(e)}")
            return set()

    def save_project_config(self, project_name: str, config_data: Dict[str, Any]) -> None:
        """
        Salva configuração específica do projeto.
        
        Args:
            project_name: Nome do projeto.
            config_data: Dicionário com dados de configuração.
        """
        project_dir = os.path.join(self.config_dir, project_name)
        Path(project_dir).mkdir(parents=True, exist_ok=True)
        
        config_path = os.path.join(project_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        logging.info(f"Configuração salva para o projeto {project_name}")

    def load_project_config(self, project_name: str) -> Optional[Dict[str, Any]]:
        """
        Carrega configuração específica do projeto.
        
        Args:
            project_name: Nome do projeto.
        
        Returns:
            Dicionário com a configuração do projeto ou None se não existir.
        """
        config_path = os.path.join(self.config_dir, project_name, "config.json")
        if os.path.exists(config_path):
            logging.info(f"Carregando configuração do projeto {project_name}")
            with open(config_path, "r") as f:
                return json.load(f)
        
        logging.warning(f"Nenhuma configuração encontrada para o projeto {project_name}")
        return None

# # Exemplo de uso
# if __name__ == "__main__":
#     try:
#         # Inicializa o helper
#         auth_helper = GoogleAuthHelper()
        
#         # Define o nome do projeto
#         project_name = "meu-projeto-teste"
        
#         # Lista projetos existentes
#         existing_projects = auth_helper.list_projects()
#         logging.info(f"Projetos existentes: {existing_projects}")
        
#         # Configura autenticação OAuth (modo headless para ambientes sem navegador)
#         scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
#         creds = auth_helper.setup_oauth_credentials(
#             scopes=scopes,
#             project_name=project_name,
#             headless=True  # Usar True em ambientes sem navegador
#         )
        
#         # Configura conta de serviço
#         service_creds = auth_helper.setup_service_account(
#             project_name=project_name
#         )
        
#         # Exemplo de configuração e uso do cache
#         # Segunda chamada usa cache automaticamente
#         creds_cached = auth_helper.setup_oauth_credentials(
#             scopes=scopes,
#             project_name=project_name
#         )
            
#     except Exception as e:
#         logging.error(f"Erro durante a execução: {str(e)}")
        

# from googleapiclient.discovery import build
# from google.auth.transport.requests import Request

# # Importa a classe que criamos
# from google_auth_helper import GoogleAuthHelper

# # Escopos necessários (exemplo: Google Drive)
# SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# # Inicializa o gerenciador de credenciais
# auth_helper = GoogleAuthHelper()

# # Obtém as credenciais OAuth2 (pede autorização do usuário na primeira vez)
# creds = auth_helper.setup_oauth_credentials(scopes=SCOPES, project_name="turing-lyceum-435603-k1", client_secrets_file="credentials\client_secret_944617682742-09hd1g7ve533hf7303epc8lnatqudr1f.apps.googleusercontent.com.json")

# # Conecta à API do Google Drive
# service = build("sheet", "v3", credentials=creds)

# # Lista arquivos do Google Drive
# results = service.files().list(pageSize=10, fields="files(id, name)").execute()
# files = results.get("files", [])

# print("Arquivos encontrados:")
# for file in files:
#     print(f"{file['name']} ({file['id']})")