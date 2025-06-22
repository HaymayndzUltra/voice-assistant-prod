"""
NLLB Translator Agent - migrated from nllb_adapter.py
Connects to No Language Left Behind (NLLB) model for translation
Implementation: facebook/nllb-200-distilled-600M
"""
import zmq
import json
import time
import logging
import sys
import os
import argparse
from datetime import datetime

# Import Hugging Face Transformers
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("nllb_translator.log")
    ]
)
logger = logging.getLogger("NLLBTranslatorAgent")

DEFAULT_PORT = 5581
LANG_MAPPING = {
    "en": "eng_Latn",
    "tl": "fil_Latn",
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "zh": "zho_Hans",
}

class NLLBTranslatorAgent:
    def __init__(self, port=DEFAULT_PORT, model_name="facebook/nllb-200-distilled-600M"):
        self.port = port
        self.model_name = model_name
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info(f"NLLB Translator Agent listening on port {self.port}")
        logger.info(f"Loading model: {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        logger.info("Model loaded successfully")

    def translate(self, text, src_lang, tgt_lang):
        src_code = LANG_MAPPING.get(src_lang, src_lang)
        tgt_code = LANG_MAPPING.get(tgt_lang, tgt_lang)
        inputs = self.tokenizer(text, return_tensors="pt")
        translated_tokens = self.model.generate(
            **inputs,
            forced_bos_token_id=self.tokenizer.lang_code_to_id[tgt_code]
        )
        translated_text = self.tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
        return translated_text

    def run(self):
        logger.info("NLLB Translator Agent started successfully.")
        while True:
            try:
                message = self.socket.recv_json()
                action = message.get("action")
                if action == "translate":
                    text = message.get("text", "")
                    src_lang = message.get("src_lang", "tl")
                    tgt_lang = message.get("tgt_lang", "en")
                    logger.info(f"Received translation request: {text} ({src_lang}->{tgt_lang})")
                    translated = self.translate(text, src_lang, tgt_lang)
                    response = {
                        "status": "success",
                        "translated_text": translated
                    }
                else:
                    response = {"status": "error", "message": "Unknown action"}
                self.socket.send_json(response)
            except Exception as e:
                logger.error(f"Error: {e}")
                self.socket.send_json({"status": "error", "message": str(e)})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NLLB Translator Agent")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind to (default: {DEFAULT_PORT})")
    parser.add_argument("--model", type=str, default="facebook/nllb-200-distilled-600M", help="NLLB model to use")
    args = parser.parse_args()
    agent = NLLBTranslatorAgent(port=args.port, model_name=args.model)
    agent.run()
