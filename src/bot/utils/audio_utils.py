# utils/audio_utils.py
from openai import OpenAI
import logging
from pathlib import Path
import tempfile
import asyncio
from src.config.config import Config

logger = logging.getLogger('AudioUtils')

# Inicializa o cliente OpenAI
client = OpenAI(api_key=Config.OPENAI_API_KEY)

async def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcreve um arquivo de áudio usando a API da OpenAI.

    Args:
        audio_file_path (str): Caminho para o arquivo de áudio.

    Returns:
        str: Texto transcrito.

    Raises:
        Exception: Se ocorrer um erro durante a transcrição ou leitura do arquivo de áudio.
    """
    try:
        logger.info(f"Iniciando transcrição com API do OpenAI: {audio_file_path}")
        
        # Usa run_in_executor para executar a operação de I/O de forma assíncrona
        loop = asyncio.get_event_loop()
        with open(audio_file_path, "rb") as audio_file:
            response = await loop.run_in_executor(
                None,
                lambda: client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            )
            
        logger.debug("Transcrição com API do OpenAI realizada com sucesso.")
        return response

    except Exception as e:
        logger.error(f"Erro ao transcrever áudio com API: {e}", exc_info=True)
        raise