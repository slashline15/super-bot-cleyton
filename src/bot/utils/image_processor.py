# utils/image_processor.py
import cv2
import numpy as np
import logging

logger = logging.getLogger('ImageProcessor')

def preprocess_image(image_path: str) -> np.ndarray:
    """
    Pré-processa a imagem para melhorar a qualidade do OCR.
    
    Args:
        image_path: Caminho da imagem
        
    Returns:
        np.ndarray: Imagem processada
    """
    try:
        # Lê a imagem
        image = cv2.imread(image_path)
        
        # Converte para escala de cinza
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Aplica threshold adaptativo
        threshold = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Remove ruído
        denoised = cv2.fastNlMeansDenoising(threshold)
        
        logger.info(f"Imagem {image_path} pré-processada com sucesso")
        return denoised
        
    except Exception as e:
        logger.error(f"Erro ao processar imagem {image_path}: {str(e)}")
        raise