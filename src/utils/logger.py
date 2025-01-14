# utils/logger.py
import logging
import os

def get_logger(name: str) -> logging.Logger:

    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        

        os.makedirs('logs', exist_ok=True)
        

        fh = logging.FileHandler('logs/app.log')
        fh.setLevel(logging.INFO)
        
   
        efh = logging.FileHandler('logs/error.log')
        efh.setLevel(logging.ERROR)
        
   
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s  - %(message)s'
        )
        
        fh.setFormatter(formatter)
        efh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(efh)
        logger.addHandler(ch)
        
    return logger
