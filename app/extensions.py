"""Shared Flask extensions and lazily loaded NLP models."""
import logging
import os
import threading
import warnings
from typing import Any, Optional

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_mysqldb import MySQL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("job-interview-platform")

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

mysql = MySQL()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10 per minute"],
)

_sentence_model: Optional[Any] = None
_keyword_model: Optional[Any] = None
_model_lock = threading.RLock()


def get_sentence_model() -> Any:
    """Load and cache SentenceTransformer only when scoring is first used."""
    global _sentence_model

    if _sentence_model is None:
        with _model_lock:
            if _sentence_model is None:
                logger.info("Loading SentenceTransformer model on CPU...")
                from sentence_transformers import SentenceTransformer

                _sentence_model = SentenceTransformer(
                    "sentence-transformers/all-MiniLM-L6-v2",
                    device="cpu",
                )
                logger.info("SentenceTransformer model loaded successfully.")

    return _sentence_model


def get_keyword_model() -> Any:
    """Load and cache KeyBERT only when keyword scoring is first used."""
    global _keyword_model

    if _keyword_model is None:
        with _model_lock:
            if _keyword_model is None:
                logger.info("Loading KeyBERT model...")
                from keybert import KeyBERT

                # Reuse the same embedding model to avoid loading it twice.
                _keyword_model = KeyBERT(model=get_sentence_model())
                logger.info("KeyBERT model loaded successfully.")

    return _keyword_model
