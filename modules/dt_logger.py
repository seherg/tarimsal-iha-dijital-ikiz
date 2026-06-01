"""
Merkezi Loglama Modulu.
Terminal ciktisi yerine dosyaya yazilir, seviyeli log tutulur.
"""
import logging
import os
from datetime import datetime

def get_logger(name='DigitalTwin', log_dir='logs'):
    os.makedirs(log_dir, exist_ok=True)
    zaman = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dosya = f"{log_dir}/dt_{zaman}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Dosyaya yaz
    fh = logging.FileHandler(log_dosya, encoding='utf-8')
    fh.setLevel(logging.DEBUG)

    # Terminale yaz (sadece INFO ve ustu)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s',
                            datefmt='%H:%M:%S')
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(f"Logger baslatildi -> {log_dosya}")
    return logger, log_dosya
