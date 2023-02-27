#!/usr/bin/env python3

import openai
import json

from transformers import GPT2Tokenizer

class ChatGPT:
    def __init__(self, config_file_path):
        with open(config_file_path) as f:
            config = json.load(f)
        openai.api_key = config["openai_api_key"]
        self.temperature = config["temperature"]
        self.max_tokens = config["max_tokens"]
        self.n = config["n"]
        self.model = config["model"]
        self.presence_penalty = config["presence_penalty"]
        # self.preprompt = config["preprompt"]
        self.stop = config["stop_sequence"]
        self.tokenizer = GPT2Tokenizer.from_pretrained('gpt2-xl')
        
    def chat(self, message):
        token_count = len(self.tokenizer.encode(message,add_special_tokens=True))

        response = openai.Completion.create(
            model=self.model,
            prompt=message,
            temperature=self.temperature,
            max_tokens=self.max_tokens-token_count,
            presence_penalty=self.presence_penalty,
            n=self.n,
            stop = self.stop
        )
        generation = response.choices[0].text.strip()
        return generation

if __name__=="__main__":
    gpt = ChatGPT("./config.json")
    print(gpt.chat(""))