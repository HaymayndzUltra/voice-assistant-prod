#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import logging
import threading
import zmq
import torch
from transformers import MarianMTModel, MarianTokenizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class HelsinkiTranslationAdapter:
    """
    Translation adapter using the Helsinki-NLP Opus-MT model specifically for Tagalog-English translation.
    This is a specialized model for Tagalog to English translation only.
    """
    
    def __init__(self, model_name="Helsinki-NLP/opus-mt-tl-en", port=5581, device=None):
        """
        Initialize the Helsinki Translation Adapter.
        
        Args:
            model_name (str): Name of the Helsinki-NLP model to use
            port (int): Port to bind the ZMQ server
            device (str): Device to use for model inference ('cpu' or 'cuda')
        """
        self.logger = logging.getLogger("HelsinkiTranslationAdapter")
        self.model_name = model_name
        self.port = port
        
        # Determine device based on availability
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.logger.info(f"Starting Helsinki Translation Adapter")
        self.logger.info(f"Using Helsinki model: {self.model_name}")
        self.logger.info(f"Using device: {self.device}")
        
        # Set up ZMQ socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        self.logger.info(f"Helsinki Translation Adapter bound to port {self.port}")
        
        # Load model
        self.model = None
        self.tokenizer = None
        self.load_model()
        
    def load_model(self):
        """
        Load the Helsinki-NLP translation model and tokenizer.
        """
        self.logger.info(f"Loading Helsinki model: {self.model_name}")
        
        # Record start time for performance tracking
        start_time = time.time()
        
        try:
            self.logger.info("Loading tokenizer...")
            self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
            
            self.logger.info("Loading model...")
            self.model = MarianMTModel.from_pretrained(self.model_name)
            self.model = self.model.to(self.device)
            
            # Track and log model loading performance
            load_time = time.time() - start_time
            self.logger.info(f"Model loaded on {self.device.upper()}")
            self.logger.info(f"Model loaded in {load_time:.2f} seconds")
            
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            raise
    
    def translate(self, text, src_lang=None, tgt_lang=None):
        """
        Translate text from Tagalog to English.
        
        Note: Helsinki-NLP/opus-mt-tl-en is a dedicated Tagalog-to-English translator,
        so src_lang and tgt_lang parameters are actually ignored.
        
        Args:
            text (str): Text to translate
            src_lang (str): Source language (ignored, always "tl")
            tgt_lang (str): Target language (ignored, always "en")
            
        Returns:
            str: Translated text
        """
        # Helsinki models are language-pair specific, so we don't need to specify languages
        try:
            # Track translation time
            start_time = time.time()
            
            # Tokenize and translate
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            translated = self.model.generate(**inputs)
            translated_text = self.tokenizer.batch_decode(translated, skip_special_tokens=True)[0]
            
            # Log translation performance
            translation_time = time.time() - start_time
            self.logger.debug(f"Translation completed in {translation_time:.2f} seconds")
            
            return translated_text
            
        except Exception as e:
            self.logger.error(f"Error during translation: {str(e)}")
            raise
    
    def process_request(self, request_data):
        """
        Process an incoming translation request.
        
        Args:
            request_data (dict): Request data containing text and language info
            
        Returns:
            dict: Response containing translated text
        """
        # Log request
        text = request_data.get("text", "")
        src_lang = request_data.get("src_lang", "tl")
        tgt_lang = request_data.get("tgt_lang", "en")
        
        self.logger.info(f"Processing translation request: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        try:
            # Translate the text
            translated_text = self.translate(text, src_lang, tgt_lang)
            
            # Prepare and log response
            response = {
                "translated_text": translated_text,
                "src_lang": src_lang,
                "tgt_lang": tgt_lang,
                "model": self.model_name,
                "status": "success"
            }
            
            self.logger.info(f"Translation successful: {translated_text[:50]}{'...' if len(translated_text) > 50 else ''}")
            return response
            
        except Exception as e:
            # Log error and return error response
            error_msg = str(e)
            self.logger.error(f"Translation error: {error_msg}")
            
            return {
                "error": error_msg,
                "src_lang": src_lang,
                "tgt_lang": tgt_lang,
                "model": self.model_name,
                "status": "error"
            }
    
    def run(self):
        """
        Run the translation server and process requests.
        """
        self.logger.info("Helsinki Translation Adapter running...")
        
        while True:
            try:
                # Receive request
                request = self.socket.recv_json()
                
                # Process request
                response = self.process_request(request)
                
                # Send response
                self.socket.send_json(response)
                
            except Exception as e:
                self.logger.error(f"Error processing request: {str(e)}")
                
                # Send error response
                try:
                    self.socket.send_json({
                        "error": str(e),
                        "status": "error"
                    })
                except:
                    # If we can't send a response, just log the error and continue
                    pass

if __name__ == "__main__":
    # Create and run the adapter
    adapter = HelsinkiTranslationAdapter(
        model_name="Helsinki-NLP/opus-mt-tl-en",
        port=5581,
        device=None  # Auto-detect
    )
    adapter.run()
